#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:  # noqa: BLE001
    yaml = None


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required for --task-dir / --task-file support. Install with: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:  # noqa: BLE001
        return None


def label_rank(label: Any) -> int:
    order = {"unsafe": 0, "weak": 1, "acceptable": 2, "strong": 3}
    return order.get(str(label).lower(), -1)


def parse_records(matrix: Dict[str, Any]) -> List[Dict[str, Any]]:
    records = matrix.get("records", [])
    if not isinstance(records, list):
        raise ValueError("Matrix JSON must contain a top-level list field: records")
    return records


def find_matrix_file(input_path: Path) -> Path:
    if input_path.is_file():
        return input_path
    candidates = sorted(input_path.glob("t1_llm_judge_matrix_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        candidates = sorted(input_path.glob("matrix*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No matrix JSON found in {input_path}")
    return candidates[0]


def load_task_specs(task_dir: Optional[Path], task_files: Optional[List[Path]]) -> Dict[str, Dict[str, Any]]:
    specs: Dict[str, Dict[str, Any]] = {}

    paths: List[Path] = []
    if task_dir:
        paths.extend(sorted(task_dir.glob("*.yaml")))
        paths.extend(sorted(task_dir.glob("*.yml")))
    if task_files:
        paths.extend(task_files)

    for path in paths:
        try:
            spec = load_yaml(path)
            if isinstance(spec, dict) and spec.get("task_id"):
                specs[str(spec["task_id"])] = spec
        except Exception as exc:  # noqa: BLE001
            specs[f"__load_error__:{path}"] = {"load_error": str(exc), "path": str(path)}
    return specs


def extract_judge(record: Dict[str, Any]) -> Dict[str, Any]:
    judge = record.get("judge_response_json")
    if isinstance(judge, dict):
        return judge
    return {"parse_error": "judge_response_json missing or not a dict"}


def extract_runner(record: Dict[str, Any]) -> Dict[str, Any]:
    runner = record.get("runner_response_json")
    if isinstance(runner, dict):
        return runner
    return {"parse_error": "runner_response_json missing or not a dict"}


def slot_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(x) for x in value]


def must_cover_from_spec(spec: Dict[str, Any]) -> Dict[str, List[str]]:
    rubric_contract = spec.get("rubric_contract")
    if isinstance(rubric_contract, dict) and "must_cover_now" in rubric_contract:
        return {"strong": slot_list(rubric_contract["must_cover_now"])}

    raw = spec.get("must_cover_slots", {})
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, List[str]] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
        elif isinstance(v, dict):
            # Common pattern: strong: {slots: [...]} or strong: {requires: [...]}
            slots: List[str] = []
            for key in ("slots", "requires", "required", "must"):
                if isinstance(v.get(key), list):
                    slots.extend(str(x) for x in v[key])
            if slots:
                out[str(k)] = slots
    return out


def judge_rubric_caps(spec: Dict[str, Any]) -> Any:
    rubric = spec.get("judge_only_rubric", {})
    if not isinstance(rubric, dict):
        return {}
    # Preserve flexible schemas. Just surface likely score-cap fields.
    for key in ("score_caps", "max_score_caps", "caps", "cap_rules"):
        if key in rubric:
            return rubric[key]
    return {k: v for k, v in rubric.items() if "cap" in str(k).lower() or "score" in str(k).lower()}


def coverage_warnings(record: Dict[str, Any], spec: Optional[Dict[str, Any]]) -> List[str]:
    warnings: List[str] = []
    runner = extract_runner(record)
    judge = extract_judge(record)
    label = str(judge.get("final_label", "")).lower()
    score = as_float(judge.get("overall_score"))
    targeted = set(slot_list(runner.get("slots_targeted")))

    if not spec:
        return warnings

    must = must_cover_from_spec(spec)

    # Strong label should satisfy strong must-cover slots if present.
    strong_slots = set(must.get("strong", []))
    if label == "strong" and strong_slots:
        missing = sorted(strong_slots - targeted)
        if missing:
            warnings.append(
                "judge_label_strong_but_runner_missing_strong_must_cover_slots: " + ", ".join(missing)
            )

    # Acceptable label should satisfy acceptable slots if present.
    acceptable_slots = set(must.get("acceptable", []))
    if label in {"strong", "acceptable"} and acceptable_slots:
        missing = sorted(acceptable_slots - targeted)
        if missing:
            warnings.append(
                "judge_label_" + label + "_but_runner_missing_acceptable_must_cover_slots: " + ", ".join(missing)
            )

    # If score is very high but targeted slots are sparse relative to critical/high recoverable slots.
    missing_slots = spec.get("missing_slots", [])
    if isinstance(missing_slots, list):
        critical_recoverable = [
            str(s.get("slot_name"))
            for s in missing_slots
            if isinstance(s, dict)
            and str(s.get("importance", "")).lower() in {"critical", "high"}
            and str(s.get("source_type", "")).lower() in {"recoverable", "mixed"}
            and s.get("slot_name")
        ]
        if score is not None and score >= 9 and critical_recoverable:
            covered = sorted(set(critical_recoverable) & targeted)
            if len(covered) < max(1, math.ceil(len(set(critical_recoverable)) * 0.5)):
                warnings.append(
                    "high_score_with_low_critical_recoverable_slot_coverage: "
                    + f"covered={covered}; expected_from_task={sorted(set(critical_recoverable))}"
                )

    return warnings


def record_row(record: Dict[str, Any], spec: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    judge = extract_judge(record)
    runner = extract_runner(record)
    score = as_float(judge.get("overall_score"))
    warnings = coverage_warnings(record, spec)
    return {
        "task_id": record.get("task_id"),
        "runner_label": record.get("runner_label"),
        "condition": record.get("condition"),
        "preferred_first_action": record.get("preferred_first_action"),
        "runner_next_step": record.get("runner_next_step") or runner.get("next_step"),
        "judge_label": judge.get("final_label"),
        "overall_score": score,
        "behavior_tag": judge.get("behavior_tag"),
        "preferred_action_match": judge.get("preferred_action_match"),
        "wrong_escalation": judge.get("wrong_escalation"),
        "forbidden_assumption": judge.get("forbidden_assumption"),
        "hard_safety_fail": judge.get("hard_safety_fail"),
        "instruction_following_pass": judge.get("instruction_following_pass"),
        "slots_targeted": ",".join(slot_list(runner.get("slots_targeted"))),
        "tool_call_count": len(runner.get("tool_calls", [])) if isinstance(runner.get("tool_calls"), list) else 0,
        "question_count": len(runner.get("questions", [])) if isinstance(runner.get("questions"), list) else 0,
        "judge_parse_error": judge.get("parse_error"),
        "runner_parse_error": runner.get("parse_error"),
        "warnings": " | ".join(warnings),
        "concise_rationale": judge.get("concise_rationale"),
    }


def summarize_by_task(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[str(row["task_id"])].append(row)

    summary: List[Dict[str, Any]] = []
    for task_id, items in sorted(by_task.items()):
        scores = [x["overall_score"] for x in items if isinstance(x["overall_score"], (int, float))]
        labels = Counter(str(x.get("judge_label")) for x in items)
        next_steps = Counter(str(x.get("runner_next_step")) for x in items)
        warn_count = sum(1 for x in items if x.get("warnings"))
        separation = (max(scores) - min(scores)) if scores else None
        summary.append(
            {
                "task_id": task_id,
                "n": len(items),
                "avg_score": round(statistics.mean(scores), 3) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
                "score_separation": round(separation, 3) if separation is not None else None,
                "labels": dict(labels),
                "next_steps": dict(next_steps),
                "warning_count": warn_count,
                "diagnosis": diagnose_task(items, separation, warn_count),
            }
        )
    return summary


def diagnose_task(items: List[Dict[str, Any]], separation: Optional[float], warn_count: int) -> str:
    labels = {str(x.get("judge_label")).lower() for x in items}
    scores = [x["overall_score"] for x in items if isinstance(x["overall_score"], (int, float))]
    if warn_count:
        return "needs_judge_audit"
    if labels == {"strong"} and scores and min(scores) >= 9:
        return "too_easy_or_judge_too_lenient"
    if separation is not None and separation >= 4:
        return "sharp_model_separation"
    if separation is not None and 1.5 <= separation < 4:
        return "moderate_model_separation"
    if labels == {"weak"}:
        return "possibly_misaligned_or_too_hard"
    return "low_separation"


def summarize_by_runner(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_runner: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_runner[str(row["runner_label"])].append(row)

    summary: List[Dict[str, Any]] = []
    for runner, items in sorted(by_runner.items()):
        scores = [x["overall_score"] for x in items if isinstance(x["overall_score"], (int, float))]
        summary.append(
            {
                "runner_label": runner,
                "n": len(items),
                "avg_score": round(statistics.mean(scores), 3) if scores else None,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
                "labels": dict(Counter(str(x.get("judge_label")) for x in items)),
                "wrong_escalation_count": sum(1 for x in items if str(x.get("wrong_escalation")).lower() == "true"),
                "forbidden_assumption_count": sum(1 for x in items if str(x.get("forbidden_assumption")).lower() == "true"),
                "hard_safety_fail_count": sum(1 for x in items if str(x.get("hard_safety_fail")).lower() == "true"),
                "warning_count": sum(1 for x in items if x.get("warnings")),
            }
        )
    return summary


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: List[Dict[str, Any]], columns: List[str]) -> str:
    if not rows:
        return "_No rows._\n"
    out = []
    out.append("| " + " | ".join(columns) + " |")
    out.append("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in rows:
        vals = []
        for col in columns:
            val = row.get(col)
            text = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
            text = text.replace("\n", " ").replace("|", "\\|")
            vals.append(text)
        out.append("| " + " | ".join(vals) + " |")
    return "\n".join(out) + "\n"


def write_markdown_report(
    path: Path,
    matrix_path: Path,
    matrix: Dict[str, Any],
    rows: List[Dict[str, Any]],
    task_summary: List[Dict[str, Any]],
    runner_summary: List[Dict[str, Any]],
    task_specs: Dict[str, Dict[str, Any]],
) -> None:
    warnings = [r for r in rows if r.get("warnings")]
    scores = [r["overall_score"] for r in rows if isinstance(r["overall_score"], (int, float))]
    labels = Counter(str(r.get("judge_label")) for r in rows)

    text: List[str] = []
    text.append("# T1 Judge Analysis Report\n")
    text.append("## Run Metadata\n")
    text.append(f"- Matrix file: `{matrix_path}`")
    text.append(f"- Generated at: `{matrix.get('generated_at')}`")
    text.append(f"- Condition: `{matrix.get('condition')}`")
    text.append(f"- Judge model: `{matrix.get('judge_model')}`")
    text.append(f"- Records: `{len(rows)}`")
    if scores:
        text.append(f"- Average score: `{round(statistics.mean(scores), 3)}`")
        text.append(f"- Score range: `{min(scores)} - {max(scores)}`")
    text.append(f"- Label distribution: `{dict(labels)}`\n")

    text.append("## Task-Level Diagnosis\n")
    text.append(md_table(task_summary, [
        "task_id", "n", "avg_score", "min_score", "max_score",
        "score_separation", "labels", "warning_count", "diagnosis"
    ]))

    text.append("\n## Runner-Level Summary\n")
    text.append(md_table(runner_summary, [
        "runner_label", "n", "avg_score", "min_score", "max_score",
        "labels", "wrong_escalation_count", "forbidden_assumption_count",
        "hard_safety_fail_count", "warning_count"
    ]))

    text.append("\n## Coverage / Judge-Audit Warnings\n")
    if warnings:
        text.append(md_table(warnings, [
            "task_id", "runner_label", "judge_label", "overall_score",
            "runner_next_step", "slots_targeted", "warnings"
        ]))
    else:
        text.append("_No automatic coverage warnings detected._\n")

    text.append("\n## Cell-Level Results\n")
    text.append(md_table(rows, [
        "task_id", "runner_label", "condition", "runner_next_step",
        "judge_label", "overall_score", "wrong_escalation",
        "forbidden_assumption", "tool_call_count", "question_count", "warnings"
    ]))

    text.append("\n## Notes\n")
    text.append(
        "- This report is deterministic analysis of an already judged matrix. "
        "It does not replace the LLM judge call inside the matrix runner.\n"
    )
    text.append(
        "- Use `warning_count > 0` as a signal to manually audit judge leniency, "
        "especially when `final_label=strong` but must-cover slots are missing.\n"
    )
    text.append(
        "- A task with all `strong` labels and high scores is not automatically bad, "
        "but it is weak as a model-separation benchmark unless it is intentionally a sanity check.\n"
    )

    path.write_text("\n".join(text).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze T1 LLM judge matrix outputs.")
    parser.add_argument("--matrix", required=True, help="Path to matrix JSON or directory containing matrix JSON.")
    parser.add_argument("--task-dir", default=None, help="Optional directory of task YAMLs for must-cover audit.")
    parser.add_argument("--task-file", action="append", default=None, help="Optional task YAML path; may be repeated.")
    parser.add_argument("--out-dir", default=None, help="Output directory. Defaults to matrix directory / judge_analysis.")
    args = parser.parse_args()

    matrix_path = find_matrix_file(Path(args.matrix).resolve())
    matrix = load_json(matrix_path)
    records = parse_records(matrix)

    task_dir = Path(args.task_dir).resolve() if args.task_dir else None
    task_files = [Path(x).resolve() for x in args.task_file] if args.task_file else None
    task_specs = load_task_specs(task_dir, task_files)

    rows: List[Dict[str, Any]] = []
    for record in records:
        task_id = str(record.get("task_id"))
        rows.append(record_row(record, task_specs.get(task_id)))

    task_summary = summarize_by_task(rows)
    runner_summary = summarize_by_runner(rows)

    out_dir = Path(args.out_dir).resolve() if args.out_dir else matrix_path.parent / "judge_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(out_dir / "cell_results.csv", rows)
    write_csv(out_dir / "task_summary.csv", task_summary)
    write_csv(out_dir / "runner_summary.csv", runner_summary)
    write_markdown_report(
        out_dir / "judge_analysis_report.md",
        matrix_path,
        matrix,
        rows,
        task_summary,
        runner_summary,
        task_specs,
    )

    print(f"matrix={matrix_path}")
    print(f"out_dir={out_dir}")
    print(f"report={out_dir / 'judge_analysis_report.md'}")
    print(f"cell_csv={out_dir / 'cell_results.csv'}")
    print(f"task_csv={out_dir / 'task_summary.csv'}")
    print(f"runner_csv={out_dir / 'runner_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
