from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Tuple

from .common import load_yaml, resolve_repo_path


TASK_LOCAL_KEYS = {
    "judge_spec",
    "judge_spec_path",
    "judge_yaml",
    "judge_yaml_path",
}


def judge_spec_path_for(task_path: Path, task: Dict[str, Any], repo_root: Path) -> Path | None:
    for key in ("judge_spec_path", "judge_spec", "judge_yaml_path", "judge_yaml"):
        value = task.get(key)
        if value:
            return resolve_repo_path(str(value), repo_root)
    return None


def merge_task_and_judge(task: Dict[str, Any], judge: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(task)
    for key, value in judge.items():
        if key in TASK_LOCAL_KEYS:
            continue
        if key in merged and merged[key] != value:
            raise ValueError(f"task/judge key conflict on {key!r}")
        merged[key] = value
    return merged


def load_task_bundle(task_path: Path, repo_root: Path) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    task = load_yaml(task_path)
    judge_path = judge_spec_path_for(task_path, task, repo_root)
    judge = load_yaml(judge_path) if judge_path else None
    merged = merge_task_and_judge(task, judge) if judge else dict(task)
    merged["_task_path"] = str(task_path)
    if judge_path:
        merged["_judge_path"] = str(judge_path)
    return merged, judge
