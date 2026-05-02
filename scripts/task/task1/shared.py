from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from scripts.fixture.common import load_yaml, parse_runner_arg, resolve_repo_path


ROOT = Path(__file__).resolve().parents[3]


def load_task1_config(config_path: Path, required_sections: Iterable[str] = ()) -> Dict[str, Any]:
    config = load_yaml(config_path)
    missing = [key for key in required_sections if key not in config]
    if missing:
        raise ValueError(f"config missing required sections {missing}: {config_path}")
    return config


def resolve_task_paths(explicit_paths: List[str], fallback_paths: List[str], repo_root: Path) -> List[Path]:
    raw_paths = explicit_paths or fallback_paths
    return [resolve_repo_path(path, repo_root) for path in raw_paths]


def runners_from_config(config: Dict[str, Any], cli_runners: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    if cli_runners:
        return cli_runners
    return [(str(item["label"]), str(item["model_id"])) for item in config.get("runners", [])]


def resolve_default_bash(candidates: List[str]) -> str:
    if os.name != "nt":
        return "bash"
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    return "bash"


def print_run_summary(record: Dict[str, Any]) -> None:
    print(
        "  oracle={0} obs={1} rejected={2} dry_run_approved={3}".format(
            record["summary"]["oracle_passed"],
            record["summary"]["tool_observation_count"],
            record["summary"]["rejected_tool_observation_count"],
            record.get("dry_run_approved"),
        ),
        flush=True,
    )
