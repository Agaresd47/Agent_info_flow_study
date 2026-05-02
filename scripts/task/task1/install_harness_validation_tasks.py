from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fixture.common import load_yaml, resolve_repo_path
from scripts.fixture.task_loader import load_task_bundle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/task1/harness_validation_assets.yaml")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    config_path = resolve_repo_path(args.config, repo_root)
    payload = load_yaml(config_path)
    assets = payload.get("assets", [])
    if not isinstance(assets, list) or not assets:
        raise SystemExit(f"No assets configured in {config_path}")

    for item in assets:
        if not isinstance(item, dict):
            raise SystemExit(f"Invalid asset entry in {config_path}: {item!r}")
        task_path = resolve_repo_path(str(item["task_path"]), repo_root)
        fixture_path = resolve_repo_path(str(item["fixture_path"]), repo_root)
        if not task_path.exists():
            raise SystemExit(f"Missing task YAML: {task_path}")
        if not fixture_path.exists():
            raise SystemExit(f"Missing fixture YAML: {fixture_path}")
        task, _judge = load_task_bundle(task_path, repo_root)
        expected_fixture = str(item["fixture_path"]).replace("\\", "/")
        actual_fixture = str(task.get("workspace_fixture", "")).replace("\\", "/")
        if actual_fixture != expected_fixture:
            raise SystemExit(f"Task fixture mismatch: {task_path} -> {actual_fixture} != {expected_fixture}")
        judge_ref = task.get("judge_spec") or task.get("judge_spec_path")
        if str(judge_ref).replace("\\", "/") != str(item["judge_path"]).replace("\\", "/"):
            raise SystemExit(f"Task judge mismatch: {task_path} -> {judge_ref} != {item['judge_path']}")
        print(f"OK {task_path}")


if __name__ == "__main__":
    main()
