from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fixture.common import write_json
from scripts.task.task1.shared import load_task1_config


CONDITIONS = ["A0_strict", "A0_interactive", "A1", "A2"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Chat_test with progressive full-score short-circuiting.")
    parser.add_argument("--config-dir", type=Path, default=ROOT / "configs" / "task1")
    parser.add_argument("--summary-path", type=Path, default=ROOT / "run_result" / "Chat_test" / "progressive_summary.json")
    parser.add_argument("--full-score", type=float, default=10.0)
    return parser.parse_args()


def condition_config_path(config_dir: Path, condition: str) -> Path:
    return config_dir / f"chat_test_matrix_{condition}.yaml"


def extract_matrix_path(stdout: str) -> Path:
    for line in stdout.splitlines():
        if line.startswith("matrix="):
            return Path(line.split("=", 1)[1].strip())
    raise RuntimeError(f"Could not find matrix path in runner stdout:\n{stdout}")


def build_temp_config(base_cfg: Dict[str, Any], task_subset: List[str], runner: Dict[str, Any], temp_path: Path) -> None:
    payload = {
        "tasks": task_subset,
        "runners": [runner],
        "judge_model": base_cfg["judge_model"],
        "condition": base_cfg["condition"],
        "runner_visibility": base_cfg.get("runner_visibility", "benchmark"),
        "fail_on_leak": base_cfg.get("fail_on_leak", True),
        "max_runner_tokens": base_cfg.get("max_runner_tokens", 1200),
        "max_judge_tokens": base_cfg.get("max_judge_tokens", 1800),
        "out_dir": base_cfg["out_dir"],
    }
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    config_dir = args.config_dir.resolve()
    summary_path = args.summary_path.resolve()
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    base_cfgs: Dict[str, Dict[str, Any]] = {}
    for condition in CONDITIONS:
        cfg_path = condition_config_path(config_dir, condition)
        base_cfgs[condition] = load_task1_config(cfg_path)

    canonical_tasks = [str(item) for item in base_cfgs["A0_strict"]["tasks"]]
    runners = list(base_cfgs["A0_strict"]["runners"])
    pending: Dict[str, List[str]] = {str(runner["label"]): canonical_tasks.copy() for runner in runners}
    executed_cells: List[Dict[str, Any]] = []
    short_circuited_cells: List[Dict[str, Any]] = []

    temp_dir = ROOT / "temp" / "chat_test_progressive"

    for cond_idx, condition in enumerate(CONDITIONS):
        base_cfg = base_cfgs[condition]
        for runner in runners:
            label = str(runner["label"])
            task_subset = [task for task in canonical_tasks if task in pending[label]]
            if not task_subset:
                continue

            temp_cfg = temp_dir / f"{condition}__{label}.json"
            build_temp_config(base_cfg, task_subset, runner, temp_cfg)

            cmd = [sys.executable, str(ROOT / "scripts" / "task" / "task1" / "t1_matrix_runner.py"), "--config", str(temp_cfg)]
            completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
            matrix_path = extract_matrix_path(completed.stdout)
            matrix_abs = (ROOT / matrix_path).resolve() if not matrix_path.is_absolute() else matrix_path.resolve()
            matrix = json.loads(matrix_abs.read_text(encoding="utf-8"))

            for record in matrix.get("records", []):
                score_raw = (record.get("judge_response_json") or {}).get("overall_score", 0)
                try:
                    score = float(score_raw)
                except (TypeError, ValueError):
                    score = 0.0
                raw_task_path = str(record["task_yaml"])
                try:
                    task_rel = str(Path(raw_task_path).resolve().relative_to(ROOT).as_posix())
                except Exception:
                    task_rel = raw_task_path.replace("\\", "/")
                executed_cells.append(
                    {
                        "condition": condition,
                        "runner_label": label,
                        "task_id": record.get("task_id"),
                        "task_yaml": task_rel,
                        "score": score,
                        "label": (record.get("judge_response_json") or {}).get("final_label"),
                        "matrix_path": str(matrix_abs.relative_to(ROOT)),
                    }
                )
                if score >= args.full_score:
                    pending[label] = [task for task in pending[label] if task != task_rel]
                    for easier in CONDITIONS[cond_idx + 1 :]:
                        short_circuited_cells.append(
                            {
                                "condition": easier,
                                "runner_label": label,
                                "task_id": record.get("task_id"),
                                "task_yaml": task_rel,
                                "inherited_from_condition": condition,
                                "inherited_score": score,
                                "inherited_label": (record.get("judge_response_json") or {}).get("final_label"),
                            }
                        )

    summary = {
        "conditions_in_order": CONDITIONS,
        "full_score_threshold": args.full_score,
        "executed_cells": executed_cells,
        "short_circuited_cells": short_circuited_cells,
        "remaining_unresolved_tasks_by_runner": pending,
    }
    write_json(summary_path, summary)
    print(f"summary={summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
