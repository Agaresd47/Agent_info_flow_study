from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable

from scripts.fixture.common import load_yaml


ROOT = Path(__file__).resolve().parents[3]


def load_task2_config(config_path: Path, required_sections: Iterable[str] = ()) -> Dict[str, Any]:
    config = load_yaml(config_path)
    missing = [key for key in required_sections if key not in config]
    if missing:
        raise ValueError(f"config missing required sections {missing}: {config_path}")
    return config


def normalize_pair(pair: Dict[str, Any]) -> Dict[str, Any]:
    planner = dict(pair.get("planner") or {})
    worker = dict(pair.get("worker") or {})
    if not pair.get("label"):
        planner_label = planner.get("label") or "planner"
        worker_label = worker.get("label") or "worker"
        pair["label"] = f"{planner_label}_x_{worker_label}"
    pair["planner"] = planner
    pair["worker"] = worker
    return pair
