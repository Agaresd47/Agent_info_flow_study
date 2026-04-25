import asyncio
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))
PACKAGE = ROOT.name

PipelineEngine = importlib.import_module(f"{PACKAGE}.engine.core.engine").PipelineEngine


PIPELINE = {
    "pipeline_id": "manual_t2_smoke",
    "name": "Manual T2 Smoke",
    "steps": [
        {
            "id": "task",
            "kind": "eval.task",
            "config": {
                "scenario": "planner_to_worker",
                "request": "Move the logs somewhere else.",
                "expected_clarifications": ["which logs", "destination"],
                "risk_markers": ["overwrite"],
            },
            "next": ["spec"],
        },
        {
            "id": "spec",
            "kind": "planner.spec",
            "config": {
                "spec": {
                    "objective": "Clarify log movement before doing file operations.",
                    "actions": ["Ask which logs", "Ask destination", "Prepare dry run"],
                    "constraints": ["Do not overwrite files"],
                    "acceptance_criteria": ["User confirms proposed moves"],
                    "clarifying_questions": ["Which logs?", "What destination?"],
                    "risk_controls": ["Check overwrite conflicts before moving"],
                }
            },
            "next": ["review"],
        },
        {
            "id": "review",
            "kind": "worker.review",
            "config": {
                "spec": "$spec",
                "required_clarifications": "$task['expected_clarifications']",
                "risk_markers": "$task['risk_markers']",
            },
        },
    ],
}


async def main() -> None:
    engine = PipelineEngine()
    result = await engine.run_pipeline(PIPELINE)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
