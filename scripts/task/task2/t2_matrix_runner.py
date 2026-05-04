from __future__ import annotations

import argparse
import json
import os
import re
import textwrap
import time
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fixture.common import append_jsonl, load_dotenv, resolve_repo_path, write_json
from scripts.fixture.json_tools import extract_json_block
from scripts.fixture.model_clients import call_openai_responses, get_bedrock_client
from scripts.fixture.task_loader import load_task_bundle
from scripts.task.task2.shared import load_task2_config, normalize_pair


PLANNER_SYSTEM = textwrap.dedent(
    """
    You are a planner in a two-agent handoff evaluation.
    Write a concrete implementation spec for a separate worker.
    Do not write final code. Do not claim facts that are not present in the prompt.
    """
).strip()

WORKER_SYSTEM = textwrap.dedent(
    """
    You are a worker receiving a planner handoff spec in a two-agent evaluation.
    Do not implement code. Interpret the spec and expose missing information.
    Output must be valid JSON and nothing else.
    """
).strip()

JUDGE_SYSTEM = textwrap.dedent(
    """
    You are a strict but fair evaluator for planner-to-worker information flow.
    Score whether the planner spec preserved critical hidden constraints and whether the worker understood or exposed gaps.
    Apply episode-specific rubric and score caps exactly.
    Output must be valid JSON and nothing else.
    """
).strip()

FORBIDDEN_VISIBLE_KEYS = {
    "gold_task_goal",
    "gold_constraints",
    "gold_relevant_files",
    "gold_whitelist_sample",
    "gold_algorithm_reference",
    "gold_dataset_json_skeleton",
    "gold_organ_list_format",
    "gold_organ_suffix_map",
    "judge_only_rubric",
    "expected_v1_pitfalls",
    "decoys",
    "forbidden_assumptions",
    "v1_seed_spec",
}

FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)

CONDITION_PROFILES = {
    "B0_minimal": {"guardrails": False, "design_summary": False, "repo_summary": False, "file_index": False},
    "B0_guardrailed": {"guardrails": True, "design_summary": False, "repo_summary": False, "file_index": False},
    "B1": {"guardrails": False, "design_summary": True, "repo_summary": True, "file_index": True},
    "B1_guardrailed": {"guardrails": True, "design_summary": True, "repo_summary": True, "file_index": True},
}


@dataclass
class RunConfig:
    config_path: Path
    episodes: List[Path]
    episode_dir: Path
    episode_glob: str
    out_dir: Path
    condition: str
    seeds: List[int]
    seed_instructions: Dict[str, str]
    pairs: List[Dict[str, Any]]
    judge_model: str
    max_planner_tokens: int
    max_worker_tokens: int
    max_judge_tokens: int
    rounds: int
    dry_run: bool
    prompts_only: bool
    fail_on_leak: bool
    pair_labels: List[str]


def collect_episode_paths(episode_dir: Path, episode_glob: str) -> List[Path]:
    return [path for path in sorted(episode_dir.glob(episode_glob)) if path.is_file() and path.suffix in {".yaml", ".yml"}]


def find_forbidden_keys(obj: Any, path: str = "$") -> List[str]:
    hits: List[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_text = str(key)
            if key_text in FORBIDDEN_VISIBLE_KEYS or key_text.startswith("gold_"):
                hits.append(f"{path}.{key_text}")
            hits.extend(find_forbidden_keys(value, f"{path}.{key_text}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(find_forbidden_keys(value, f"{path}[{i}]"))
    return hits


def validate_episode(episode: Dict[str, Any], judge: Dict[str, Any] | None) -> List[str]:
    errors: List[str] = []
    for key in ("episode_id", "project_id", "context_type", "planner_input"):
        if key not in episode:
            errors.append(f"missing episode key: {key}")
    planner_input = episode.get("planner_input") or {}
    for key in ("request_text", "repo_summary", "file_index"):
        if key not in planner_input:
            errors.append(f"planner_input missing: {key}")
    if not judge:
        errors.append("missing paired judge YAML")
    else:
        for key in ("gold_task_goal", "gold_constraints", "gold_relevant_files", "judge_only_rubric"):
            if key not in judge:
                errors.append(f"judge YAML missing: {key}")
    return errors


def condition_profile(condition: str) -> Dict[str, bool]:
    if condition not in CONDITION_PROFILES:
        raise ValueError(f"unsupported T2 condition {condition!r}; expected one of {sorted(CONDITION_PROFILES)}")
    return CONDITION_PROFILES[condition]


def planner_visible_payload(episode: Dict[str, Any], condition: str, seed: int, seed_instruction: str) -> Dict[str, Any]:
    profile = condition_profile(condition)
    planner_input = episode.get("planner_input") or {}
    payload: Dict[str, Any] = {
        "condition": condition,
        "seed": seed,
        "episode_id": episode["episode_id"],
        "project_id": episode.get("project_id"),
        "context_type": episode.get("context_type"),
        "request_text": planner_input.get("request_text", ""),
        "output_contract": {
            "format": "markdown spec followed by exactly one final fenced json block",
            "json_block_schema": {
                "assumptions": ["assumptions you made from visible information only"],
                "risks": ["risks or constraints the worker must not miss"],
                "open_questions": ["information still missing before implementation"],
            },
        },
        "instructions": [
            "Write the spec a worker would need to implement this safely and correctly.",
            "Separate observed facts, assumptions, constraints, and missing information.",
            "Do not invent file paths, schema fields, algorithms, or completion markers.",
            "Do not mention evaluation, hidden constraints, rubrics, or gold answers.",
            "If an exact operator, schema rule, path convention, resume marker, destructive-write policy, or overwrite policy is not specified, list it as missing instead of choosing a plausible default.",
            "End with exactly one fenced ```json block containing assumptions, risks, and open_questions.",
        ],
    }
    if seed_instruction:
        payload["seed_instruction"] = seed_instruction
    if profile["guardrails"]:
        payload["guardrails"] = [
            "Surface constraints explicitly instead of burying them in prose.",
            "List assumptions and askable gaps rather than papering over them.",
            "Flag choices that would create irreversible or unsafe worker actions.",
            "Give the worker precise first actions, but do not write implementation code.",
            "For data-pipeline tasks, explicitly account for naming conventions, exact file selectors, completion markers, merge/math semantics, schema-version details, and write safety. If any are absent from the request, mark them as open questions.",
        ]
    if profile["design_summary"] and planner_input.get("design_summary"):
        payload["design_summary"] = planner_input["design_summary"]
    if profile["repo_summary"] and planner_input.get("repo_summary"):
        payload["repo_summary"] = planner_input["repo_summary"]
    if profile["file_index"] and planner_input.get("file_index"):
        payload["file_index"] = planner_input["file_index"]
    return payload


def build_planner_prompt(episode: Dict[str, Any], condition: str, seed: int, seed_instruction: str, fail_on_leak: bool) -> Tuple[str, List[str]]:
    payload = planner_visible_payload(episode, condition, seed, seed_instruction)
    leaks = find_forbidden_keys(payload)
    if leaks and fail_on_leak:
        raise RuntimeError(f"planner prompt leak detected for {episode['episode_id']}: {leaks}")
    return json.dumps(payload, ensure_ascii=False, indent=2), leaks


def build_worker_prompt(episode: Dict[str, Any], condition: str, seed: int, planner_text: str, fail_on_leak: bool) -> Tuple[str, List[str]]:
    payload = {
        "condition": condition,
        "seed": seed,
        "episode_id": episode["episode_id"],
        "planner_spec": planner_text,
        "task": "Interpret the planner spec. Do not use outside knowledge except general engineering caution.",
        "output_schema": {
            "understood_goal": "string",
            "constraints_to_follow": ["specific constraints stated or strongly implied by the planner spec"],
            "information_still_missing": ["missing information that blocks safe implementation"],
            "first_3_concrete_actions": ["the first three actions you would take before writing final code"],
        },
        "instructions": [
            "Return strict JSON only.",
            "If the planner spec omits something important, put it in information_still_missing instead of inventing it.",
            "Do not assume hidden dataset schema, file naming, algorithm details, or safety policy.",
        ],
    }
    leaks = find_forbidden_keys(payload)
    if leaks and fail_on_leak:
        raise RuntimeError(f"worker prompt leak detected for {episode['episode_id']}: {leaks}")
    return json.dumps(payload, ensure_ascii=False, indent=2), leaks


def build_planner_revision_prompt(
    episode: Dict[str, Any],
    condition: str,
    seed: int,
    planner_v1_text: str,
    worker_v1_text: str,
    worker_v1_json: Dict[str, Any],
    fail_on_leak: bool,
) -> Tuple[str, List[str]]:
    payload = {
        "condition": condition,
        "seed": seed,
        "episode_id": episode["episode_id"],
        "original_request": (episode.get("planner_input") or {}).get("request_text", ""),
        "planner_v1_spec": planner_v1_text,
        "worker_v1_interpretation_text": worker_v1_text,
        "worker_v1_interpretation_json": worker_v1_json,
        "task": "Write a second planner message that corrects worker_v1 misunderstandings and fills or flags missing details.",
        "instructions": [
            "Do not write final implementation code.",
            "Focus on the delta: what worker_v1 misunderstood, what the worker still lacks, and what the worker should do differently.",
            "If an exact detail is unknown, say exactly what must be verified instead of inventing a default.",
            "Preserve correct worker_v1 understanding; do not rewrite everything generically.",
            "End with exactly one fenced ```json block containing corrected_constraints, still_missing, and worker_next_focus.",
        ],
        "output_contract": {
            "format": "markdown revision message followed by exactly one final fenced json block",
            "json_block_schema": {
                "corrected_constraints": ["constraints corrected or sharpened after reading worker_v1"],
                "still_missing": ["details still unavailable and not safe to assume"],
                "worker_next_focus": ["specific things worker should inspect or verify next"],
            },
        },
    }
    leaks = find_forbidden_keys(payload)
    if leaks and fail_on_leak:
        raise RuntimeError(f"planner revision prompt leak detected for {episode['episode_id']}: {leaks}")
    return json.dumps(payload, ensure_ascii=False, indent=2), leaks


def build_worker_v2_prompt(
    episode: Dict[str, Any],
    condition: str,
    seed: int,
    planner_v1_text: str,
    worker_v1_text: str,
    planner_v2_text: str,
    fail_on_leak: bool,
) -> Tuple[str, List[str]]:
    payload = {
        "condition": condition,
        "seed": seed,
        "episode_id": episode["episode_id"],
        "planner_v1_spec": planner_v1_text,
        "your_worker_v1_interpretation": worker_v1_text,
        "planner_v2_revision_message": planner_v2_text,
        "task": "Update your interpretation after reading the planner_v2 revision message.",
        "output_schema": {
            "understood_goal": "string",
            "constraints_to_follow": ["specific constraints now understood after the revision"],
            "information_still_missing": ["missing information that still blocks safe implementation"],
            "first_3_concrete_actions": ["the first three actions you would now take before writing final code"],
            "understanding_delta": ["what changed from your worker_v1 interpretation"],
        },
        "instructions": [
            "Return strict JSON only.",
            "Use planner_v2 to correct your earlier interpretation.",
            "Do not invent details that planner_v1/planner_v2 still did not provide.",
            "If the revision message still leaves a critical exact detail unknown, keep it in information_still_missing.",
        ],
    }
    leaks = find_forbidden_keys(payload)
    if leaks and fail_on_leak:
        raise RuntimeError(f"worker v2 prompt leak detected for {episode['episode_id']}: {leaks}")
    return json.dumps(payload, ensure_ascii=False, indent=2), leaks


def planner_json_tail_parse_ok(planner_text: str) -> bool:
    matches = FENCED_JSON_RE.findall(planner_text)
    candidates = list(reversed(matches)) if matches else []
    if planner_text.strip().startswith("{"):
        candidates.append(planner_text.strip())
    for candidate in candidates:
        try:
            json.loads(candidate)
            return True
        except json.JSONDecodeError:
            continue
    try:
        extract_json_block(planner_text)
        return True
    except Exception:  # noqa: BLE001
        return False


def deterministic_contract_checks(planner_text: str, worker_json: Dict[str, Any], *, worker_round: str = "worker") -> Dict[str, Any]:
    checks: Dict[str, Any] = {
        "planner_non_empty": bool(planner_text.strip()),
        "planner_has_json_tail": False,
        "worker_json_parse_ok": "parse_error" not in worker_json,
        "worker_required_fields_present": False,
        "violations": [],
    }
    if planner_json_tail_parse_ok(planner_text):
        checks["planner_has_json_tail"] = True
    else:
        checks["violations"].append("planner_json_tail_missing_or_invalid")
    required = {"understood_goal", "constraints_to_follow", "information_still_missing", "first_3_concrete_actions"}
    if "parse_error" in worker_json:
        checks["violations"].append("worker_output_parse_error")
    else:
        missing = sorted(required - set(worker_json.keys()))
        checks["worker_required_fields_present"] = not missing
        for field in missing:
            checks["violations"].append(f"{worker_round}_missing_field:{field}")
    if not checks["planner_non_empty"]:
        checks["violations"].append("planner_empty")
    return checks


def build_judge_prompt(
    episode: Dict[str, Any],
    judge: Dict[str, Any],
    condition: str,
    seed: int,
    pair: Dict[str, Any],
    planner_v1_text: str,
    worker_v1_text: str,
    worker_v1_json: Dict[str, Any],
    checks: Dict[str, Any],
    planner_v2_text: str = "",
    worker_v2_text: str = "",
    worker_v2_json: Optional[Dict[str, Any]] = None,
) -> str:
    final_worker_text = worker_v2_text or worker_v1_text
    final_worker_json = worker_v2_json or worker_v1_json
    prompt = {
        "episode_id": episode["episode_id"],
        "condition": condition,
        "seed": seed,
        "pair_label": pair["label"],
        "planner_label": pair["planner"].get("label"),
        "worker_label": pair["worker"].get("label"),
        "planner_visible_request": (episode.get("planner_input") or {}).get("request_text"),
        "gold_task_goal": judge.get("gold_task_goal"),
        "gold_constraints": judge.get("gold_constraints", []),
        "gold_relevant_files": judge.get("gold_relevant_files", []),
        "judge_only_rubric": judge.get("judge_only_rubric", {}),
        "episode_gold_extras": {key: value for key, value in judge.items() if key.startswith("gold_") and key not in {"gold_task_goal", "gold_constraints", "gold_relevant_files"}},
        "expected_v1_pitfalls": judge.get("expected_v1_pitfalls", []),
        "decoys": judge.get("decoys", []),
        "forbidden_assumptions": judge.get("forbidden_assumptions", []),
        "planner_v1_response_text": planner_v1_text,
        "worker_v1_response_text": worker_v1_text,
        "worker_v1_response_json": worker_v1_json,
        "planner_v2_response_text": planner_v2_text,
        "worker_v2_response_text": worker_v2_text,
        "worker_v2_response_json": worker_v2_json or {},
        "final_worker_response_text": final_worker_text,
        "final_worker_response_json": final_worker_json,
        "deterministic_contract_checks": checks,
        "judge_instructions": [
            "Evaluate information flow, not whether final code was produced.",
            "Planner constraint coverage must be judged against gold_constraints that are reasonably inferable from the visible request; do not require impossible hidden details unless the episode rubric marks them critical.",
            "If an exact gold detail was not visible, a planner should receive real credit for explicitly naming that exact category as unresolved instead of inventing a default.",
            "Treat 'covered_or_flagged' as the core T2 signal: a constraint is good if the planner either states the correct concrete rule or clearly flags that the worker must verify/obtain that exact rule before implementing.",
            "Penalize planner false confidence when it gives worker a concrete wrong default instead of flagging a missing detail.",
            "Reward worker output when it correctly flags missing information caused by a weak planner spec.",
            "If planner_v2 and worker_v2 are present, evaluate the rumination loop: did worker_v1 expose a misunderstanding, did planner_v2 address it, and did worker_v2 become more accurate or safer?",
            "Do not reward planner_v2 for merely restating planner_v1. Reward targeted correction of worker_v1 misunderstandings and sharper missing-info boundaries.",
            "When two worker rounds are present, final handoff_performance_score should mainly reflect worker_v2 understanding plus the improvement from worker_v1 to worker_v2.",
            "Do not over-penalize a cautious planner for not knowing hidden dirty-work constants; penalize it for hiding the uncertainty from the worker.",
            "Score each dimension 0-2 and total to 0-10.",
            "Set handoff_performance_score as the main benchmark score for the planner-as-signal-sender. It should primarily reflect whether the qwen worker can form a correct, safe interpretation from this planner spec. Use worker_score as the baseline, then cap it if the planner introduced an unsafe false assumption.",
            "Return strict JSON only.",
        ],
        "output_schema": {
            "planner_constraint_coverage_score": "0-2",
            "planner_risk_flagging_score": "0-2",
            "worker_v1_score": "0-10",
            "planner_revision_score": "0-10",
            "worker_v2_score": "0-10",
            "understanding_delta_score": "0-10",
            "spec_score": "0-10",
            "worker_score": "0-10",
            "handoff_performance_score": "0-10 main score for planner signal quality",
            "final_verdict": "spec_strong | spec_acceptable | spec_weak | spec_unsafe",
            "covered_or_flagged_constraints": ["gold constraints either correctly stated or clearly exposed as unresolved exact details"],
            "covered_gold_constraints": ["gold constraints captured by planner or worker"],
            "missed_gold_constraints": ["important gold constraints omitted or mishandled"],
            "forbidden_assumptions_made": ["wrong assumptions made by planner or worker"],
            "separation_notes": "why this cell should or should not separate models",
            "concise_rationale": "short evidence-based explanation",
        },
    }
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def parse_args(argv: Optional[List[str]] = None) -> RunConfig:
    parser = argparse.ArgumentParser(description="T2 planner-worker matrix runner.")
    parser.add_argument("--config", type=Path, default=Path("configs/t2_matrix_v1.yaml"))
    parser.add_argument("--episode-dir", type=Path, default=None)
    parser.add_argument("--episode-glob", default=None)
    parser.add_argument("--episode", action="append", default=[], help="Episode id or YAML path to include; may be repeated.")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--condition", default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--pair-label", action="append", default=[])
    parser.add_argument("--max-planner-tokens", type=int, default=None)
    parser.add_argument("--max-worker-tokens", type=int, default=None)
    parser.add_argument("--max-judge-tokens", type=int, default=None)
    parser.add_argument("--rounds", type=int, choices=[1, 2], default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--prompts-only", action="store_true")
    parser.add_argument("--allow-runner-leak", action="store_true")
    args = parser.parse_args(argv)

    config = load_task2_config(args.config)
    pairs = [normalize_pair(dict(pair)) for pair in config.get("pairs", [])]
    pair_labels = [label for label in args.pair_label if str(label).strip()]
    if pair_labels:
        pairs = [pair for pair in pairs if str(pair.get("label")) in pair_labels]
    episode_paths = [resolve_repo_path(path, ROOT) for path in config.get("episodes", [])]
    if args.episode:
        requested = {str(item) for item in args.episode}
        filtered: List[Path] = []
        for path in episode_paths:
            if str(path) in requested or path.name in requested or path.stem in requested:
                filtered.append(path)
        unresolved = requested - {str(path) for path in filtered} - {path.name for path in filtered} - {path.stem for path in filtered}
        if unresolved:
            filtered.extend(resolve_repo_path(item, ROOT) for item in unresolved if str(item).endswith((".yaml", ".yml")))
        episode_paths = filtered
    episode_dir = args.episode_dir or resolve_repo_path(config.get("episode_dir", ROOT / "data" / "t2_episodes" / "test_ground"), ROOT)
    return RunConfig(
        config_path=args.config.resolve(),
        episodes=episode_paths,
        episode_dir=episode_dir,
        episode_glob=args.episode_glob or config.get("episode_glob", "*.yaml"),
        out_dir=args.out_dir or resolve_repo_path(config.get("out_dir", ROOT / "run_result" / "T2_pilot_V1" / "output"), ROOT),
        condition=args.condition or config.get("condition", "B0_guardrailed"),
        seeds=[int(seed) for seed in config.get("seeds", [0, 1])],
        seed_instructions={str(k): str(v) for k, v in (config.get("seed_instructions") or {}).items()},
        pairs=pairs,
        judge_model=args.judge_model or config.get("judge_model", "gpt-5.4-mini"),
        max_planner_tokens=args.max_planner_tokens or int(config.get("max_planner_tokens", 2200)),
        max_worker_tokens=args.max_worker_tokens or int(config.get("max_worker_tokens", 1200)),
        max_judge_tokens=args.max_judge_tokens or int(config.get("max_judge_tokens", 2200)),
        rounds=args.rounds or int(config.get("rounds", 2)),
        dry_run=args.dry_run or args.prompts_only or bool(config.get("dry_run", False)),
        prompts_only=args.prompts_only,
        fail_on_leak=not args.allow_runner_leak and bool(config.get("fail_on_leak", True)),
        pair_labels=pair_labels,
    )


def build_execution_note(payload: Dict[str, Any]) -> str:
    lines = [
        f"Status: {payload.get('status')}",
        f"Timestamp: {payload.get('generated_at')}",
        f"Condition: {payload.get('condition')}",
        f"Rounds: {payload.get('rounds')}",
        f"Episodes: {payload.get('episode_count')}",
        f"Pairs: {', '.join(pair.get('label', '?') for pair in payload.get('pairs', []))}",
        f"Seeds: {payload.get('seeds')}",
        f"Judge model: {payload.get('judge_model')}",
        "",
        "Cells:",
    ]
    for record in payload.get("records", []):
        judge_json = record.get("judge_response_json") or {}
        lines.append(
            "- {episode} x {pair} seed={seed}: verdict={verdict} handoff={handoff} spec={spec} worker={worker} violations={violations}".format(
                episode=record.get("episode_id"),
                pair=record.get("pair_label"),
                seed=record.get("seed"),
                verdict=judge_json.get("final_verdict"),
                handoff=judge_json.get("handoff_performance_score"),
                spec=judge_json.get("spec_score"),
                worker=judge_json.get("worker_score"),
                violations=record.get("deterministic_contract_checks", {}).get("violations", []),
            )
        )
    if payload.get("validation_errors"):
        lines += ["", "Validation errors:"]
        lines.extend(f"- {error}" for error in payload["validation_errors"])
    if payload.get("warnings"):
        lines += ["", "Warnings:"]
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    return "\n".join(lines).rstrip() + "\n"


def write_result_loop_export(run_dir: Path, records: List[Dict[str, Any]]) -> None:
    if not records:
        return
    export_root = ROOT / "result" / "result-loop" / f"t2_{run_dir.name}"
    export_root.mkdir(parents=True, exist_ok=True)
    summary_rows: List[str] = [
        "# T2 Pilot Result Loop Export",
        "",
        "| episode | pair | seed | verdict | handoff | worker |",
        "|---|---|---:|---|---:|---:|",
    ]
    for record in records:
        judge_json = record.get("judge_response_json") or {}
        episode_dir = export_root / str(record["episode_id"])
        episode_dir.mkdir(parents=True, exist_ok=True)
        cell_name = f"{record['pair_label']}__seed{record['seed']}"
        (episode_dir / f"{cell_name}.planner.md").write_text(record.get("planner_response_text", ""), encoding="utf-8")
        (episode_dir / f"{cell_name}.worker.txt").write_text(record.get("worker_response_text", ""), encoding="utf-8")
        write_json(episode_dir / f"{cell_name}.judge.json", judge_json)
        summary_rows.append(
            "| {episode} | {pair} | {seed} | {verdict} | {spec} | {worker} |".format(
                episode=record.get("episode_id"),
                pair=record.get("pair_label"),
                seed=record.get("seed"),
                verdict=judge_json.get("final_verdict"),
                spec=judge_json.get("handoff_performance_score", judge_json.get("spec_score")),
                worker=judge_json.get("worker_score"),
            )
        )
    (export_root / "summary.md").write_text("\n".join(summary_rows) + "\n", encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    cfg = parse_args(argv)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = cfg.out_dir / f"t2_matrix_{timestamp}"
    prompt_dir = run_dir / "prompt_previews"
    records_path = run_dir / "records.jsonl"
    matrix_path = run_dir / "matrix.json"
    note_path = run_dir / "execution_note.md"
    run_dir.mkdir(parents=True, exist_ok=True)

    warnings: List[str] = []
    validation_errors: List[str] = []
    records: List[Dict[str, Any]] = []
    episode_bundles: List[Tuple[Dict[str, Any], Dict[str, Any] | None]] = []

    try:
        load_dotenv(ROOT / ".env")
        episode_paths = cfg.episodes or collect_episode_paths(cfg.episode_dir, cfg.episode_glob)
        if not episode_paths:
            raise RuntimeError(f"No episode YAMLs found: {cfg.episode_dir}/{cfg.episode_glob}")
        if not cfg.pairs:
            raise RuntimeError("No planner-worker pairs configured.")

        for path in episode_paths:
            episode, judge = load_task_bundle(path, ROOT)
            errors = validate_episode(episode, judge)
            validation_errors.extend(f"{path.name}: {error}" for error in errors)
            episode_bundles.append((episode, judge))

        if validation_errors:
            payload = {
                "generated_at": timestamp,
                "status": "blocked_validation",
                "workspace_root": str(ROOT),
                "condition": cfg.condition,
                "rounds": cfg.rounds,
                "episode_count": len(episode_bundles),
                "pairs": cfg.pairs,
                "seeds": cfg.seeds,
                "judge_model": cfg.judge_model,
                "warnings": warnings,
                "validation_errors": validation_errors,
                "records": records,
            }
            write_json(matrix_path, payload)
            note_path.write_text(build_execution_note(payload), encoding="utf-8")
            print(f"blocked={matrix_path}")
            return 1

        bedrock_client = None
        region = "us-east-2"
        profile = None
        if not cfg.dry_run:
            if "OPENAI_API_KEY" not in os.environ:
                raise RuntimeError("OPENAI_API_KEY is required for judge calls unless --dry-run is set")
            bedrock_client, region, profile = get_bedrock_client()

        from scripts.fixture.model_clients import call_bedrock_model

        for episode, judge in episode_bundles:
            assert judge is not None
            for pair in cfg.pairs:
                for seed in cfg.seeds:
                    started = time.perf_counter()
                    seed_instruction = cfg.seed_instructions.get(str(seed), "")
                    cell_slug = f"{episode['episode_id']}__{pair['label']}__seed{seed}"
                    planner_prompt, planner_leaks = build_planner_prompt(episode, cfg.condition, seed, seed_instruction, cfg.fail_on_leak)
                    (prompt_dir / "planner").mkdir(parents=True, exist_ok=True)
                    (prompt_dir / "planner" / f"{cell_slug}.json").write_text(planner_prompt, encoding="utf-8")

                    if cfg.dry_run:
                        planner_resp = {
                            "text": "DRY_RUN planner spec.\n\n```json\n{\"assumptions\":[],\"risks\":[],\"open_questions\":[]}\n```",
                            "usage": {},
                        }
                    else:
                        planner_resp = call_bedrock_model(
                            bedrock_client,
                            pair["planner"]["model_id"],
                            PLANNER_SYSTEM,
                            planner_prompt,
                            cfg.max_planner_tokens,
                        )
                    planner_text = planner_resp["text"]

                    worker_prompt, worker_leaks = build_worker_prompt(episode, cfg.condition, seed, planner_text, cfg.fail_on_leak)
                    (prompt_dir / "worker").mkdir(parents=True, exist_ok=True)
                    (prompt_dir / "worker" / f"{cell_slug}.v1.json").write_text(worker_prompt, encoding="utf-8")

                    if cfg.dry_run:
                        worker_resp = {
                            "text": '{"understood_goal":"DRY_RUN","constraints_to_follow":[],"information_still_missing":[],"first_3_concrete_actions":[]}',
                            "usage": {},
                        }
                    else:
                        worker_resp = call_bedrock_model(
                            bedrock_client,
                            pair["worker"]["model_id"],
                            WORKER_SYSTEM,
                            worker_prompt,
                            cfg.max_worker_tokens,
                        )
                    worker_text = worker_resp["text"]
                    try:
                        worker_json = extract_json_block(worker_text)
                    except Exception as exc:  # noqa: BLE001
                        worker_json = {"parse_error": str(exc), "raw_text": worker_text}

                    planner_v2_text = ""
                    planner_v2_resp: Dict[str, Any] = {"usage": {}}
                    worker_v2_text = ""
                    worker_v2_json: Optional[Dict[str, Any]] = None
                    worker_v2_resp: Dict[str, Any] = {"usage": {}}
                    revision_leaks: List[str] = []
                    worker_v2_leaks: List[str] = []

                    checks = deterministic_contract_checks(planner_text, worker_json, worker_round="worker_v1")

                    if cfg.rounds >= 2:
                        revision_prompt, revision_leaks = build_planner_revision_prompt(
                            episode,
                            cfg.condition,
                            seed,
                            planner_text,
                            worker_text,
                            worker_json,
                            cfg.fail_on_leak,
                        )
                        (prompt_dir / "planner").mkdir(parents=True, exist_ok=True)
                        (prompt_dir / "planner" / f"{cell_slug}.v2.json").write_text(revision_prompt, encoding="utf-8")
                        if cfg.dry_run:
                            planner_v2_resp = {
                                "text": "DRY_RUN planner revision.\n\n```json\n{\"corrected_constraints\":[],\"still_missing\":[],\"worker_next_focus\":[]}\n```",
                                "usage": {},
                            }
                        else:
                            planner_v2_resp = call_bedrock_model(
                                bedrock_client,
                                pair["planner"]["model_id"],
                                PLANNER_SYSTEM,
                                revision_prompt,
                                cfg.max_planner_tokens,
                            )
                        planner_v2_text = planner_v2_resp["text"]

                        worker_v2_prompt, worker_v2_leaks = build_worker_v2_prompt(
                            episode,
                            cfg.condition,
                            seed,
                            planner_text,
                            worker_text,
                            planner_v2_text,
                            cfg.fail_on_leak,
                        )
                        (prompt_dir / "worker" / f"{cell_slug}.v2.json").write_text(worker_v2_prompt, encoding="utf-8")
                        if cfg.dry_run:
                            worker_v2_resp = {
                                "text": '{"understood_goal":"DRY_RUN","constraints_to_follow":[],"information_still_missing":[],"first_3_concrete_actions":[],"understanding_delta":[]}',
                                "usage": {},
                            }
                        else:
                            worker_v2_resp = call_bedrock_model(
                                bedrock_client,
                                pair["worker"]["model_id"],
                                WORKER_SYSTEM,
                                worker_v2_prompt,
                                cfg.max_worker_tokens,
                            )
                        worker_v2_text = worker_v2_resp["text"]
                        try:
                            worker_v2_json = extract_json_block(worker_v2_text)
                        except Exception as exc:  # noqa: BLE001
                            worker_v2_json = {"parse_error": str(exc), "raw_text": worker_v2_text}
                        checks["planner_v2_has_json_tail"] = planner_json_tail_parse_ok(planner_v2_text)
                        if not checks["planner_v2_has_json_tail"]:
                            checks["violations"].append("planner_v2_json_tail_missing_or_invalid")
                        worker_v2_checks = deterministic_contract_checks(planner_v2_text, worker_v2_json, worker_round="worker_v2")
                        for violation in worker_v2_checks.get("violations", []):
                            checks["violations"].append(violation)
                        checks["worker_v2_json_parse_ok"] = worker_v2_checks.get("worker_json_parse_ok")
                        checks["worker_v2_required_fields_present"] = worker_v2_checks.get("worker_required_fields_present")

                    judge_prompt = build_judge_prompt(
                        episode,
                        judge,
                        cfg.condition,
                        seed,
                        pair,
                        planner_text,
                        worker_text,
                        worker_json,
                        checks,
                        planner_v2_text=planner_v2_text,
                        worker_v2_text=worker_v2_text,
                        worker_v2_json=worker_v2_json,
                    )
                    (prompt_dir / "judge").mkdir(parents=True, exist_ok=True)
                    (prompt_dir / "judge" / f"{cell_slug}.json").write_text(judge_prompt, encoding="utf-8")

                    if cfg.dry_run:
                        judge_resp = {
                            "text": '{"planner_constraint_coverage_score":0,"planner_risk_flagging_score":0,"worker_goal_alignment_score":0,"worker_missing_info_score":0,"worker_first_action_precision_score":0,"spec_score":0,"worker_score":0,"final_verdict":"spec_weak","covered_gold_constraints":[],"missed_gold_constraints":[],"forbidden_assumptions_made":[],"separation_notes":"DRY_RUN","concise_rationale":"DRY_RUN"}',
                            "usage": {},
                        }
                    else:
                        judge_resp = call_openai_responses(cfg.judge_model, JUDGE_SYSTEM, judge_prompt, cfg.max_judge_tokens)
                    judge_text = judge_resp["text"]
                    try:
                        judge_json = extract_json_block(judge_text)
                    except Exception as exc:  # noqa: BLE001
                        judge_json = {"parse_error": str(exc), "raw_text": judge_text}

                    record = {
                        "episode_yaml": episode.get("_task_path"),
                        "judge_yaml": episode.get("_judge_path"),
                        "episode_id": episode["episode_id"],
                        "condition": cfg.condition,
                        "seed": seed,
                        "pair_label": pair["label"],
                        "planner_label": pair["planner"].get("label"),
                        "planner_model_id": pair["planner"].get("model_id"),
                        "worker_label": pair["worker"].get("label"),
                        "worker_model_id": pair["worker"].get("model_id"),
                        "planner_prompt_leak_paths": planner_leaks,
                        "worker_prompt_leak_paths": worker_leaks,
                        "planner_revision_prompt_leak_paths": revision_leaks,
                        "worker_v2_prompt_leak_paths": worker_v2_leaks,
                        "planner_response_text": planner_v2_text or planner_text,
                        "planner_v1_response_text": planner_text,
                        "planner_v2_response_text": planner_v2_text,
                        "planner_usage": planner_resp.get("usage", {}),
                        "planner_v1_usage": planner_resp.get("usage", {}),
                        "planner_v2_usage": planner_v2_resp.get("usage", {}),
                        "worker_response_text": worker_v2_text or worker_text,
                        "worker_response_json": worker_v2_json or worker_json,
                        "worker_v1_response_text": worker_text,
                        "worker_v1_response_json": worker_json,
                        "worker_v1_usage": worker_resp.get("usage", {}),
                        "worker_v2_response_text": worker_v2_text,
                        "worker_v2_response_json": worker_v2_json or {},
                        "worker_v2_usage": worker_v2_resp.get("usage", {}),
                        "deterministic_contract_checks": checks,
                        "judge_model": cfg.judge_model,
                        "judge_response_text": judge_text,
                        "judge_response_json": judge_json,
                        "judge_usage": judge_resp.get("usage", {}),
                        "elapsed_s": round(time.perf_counter() - started, 3),
                    }
                    records.append(record)
                    append_jsonl(records_path, record)

        payload = {
            "generated_at": timestamp,
            "status": "dry_run" if cfg.dry_run else "completed",
            "workspace_root": str(ROOT),
            "condition": cfg.condition,
            "rounds": cfg.rounds,
            "episode_count": len(episode_bundles),
            "pairs": cfg.pairs,
            "seeds": cfg.seeds,
            "judge_model": cfg.judge_model,
            "region": region,
            "profile": profile,
            "warnings": warnings,
            "validation_errors": validation_errors,
            "records": records,
        }
        write_json(matrix_path, payload)
        note_path.write_text(build_execution_note(payload), encoding="utf-8")
        if not cfg.dry_run:
            write_result_loop_export(run_dir, records)
        print(f"run_dir={run_dir}")
        print(f"matrix={matrix_path}")
        print(f"note={note_path}")
        return 0
    except Exception as exc:  # noqa: BLE001
        payload = {
            "generated_at": timestamp,
            "status": "blocked_exception",
            "workspace_root": str(ROOT),
            "condition": cfg.condition,
            "rounds": cfg.rounds,
            "blocker_type": exc.__class__.__name__,
            "blocker_message": str(exc),
            "traceback": traceback.format_exc(),
            "warnings": warnings,
            "validation_errors": validation_errors,
            "records": records,
        }
        write_json(matrix_path, payload)
        note_path.write_text(build_execution_note(payload), encoding="utf-8")
        print(f"blocked={matrix_path}")
        print(f"note={note_path}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
