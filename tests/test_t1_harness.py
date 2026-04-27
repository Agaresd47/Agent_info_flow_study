import importlib
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

t1_harness = importlib.import_module("engine.nodes.eval.t1_harness")
t1_runtime = importlib.import_module("engine.nodes.eval.t1_runtime")


class T1HarnessTests(unittest.TestCase):
    def test_smoke_task_runs_loop_and_generates_trace_and_summary(self) -> None:
        task_path = ROOT / "data" / "t1_tasks" / "test_ground" / "t1_smoke_cleanup_archive.yaml"
        task = t1_runtime.build_t1_task_payload(yaml.safe_load(task_path.read_text(encoding="utf-8")))

        record = t1_harness.run_t1_agent_eval(
            task,
            {
                "condition": {"spec_level": "A0_interactive"},
                "model_id": "mock_primary",
                "requested_model_id": "mock_primary",
                "model_tier": "mock",
            },
        )

        self.assertTrue(record["agent_trace"])
        self.assertTrue(record["summary_markdown"])
        self.assertEqual(record["preferred_first_action"], "ask_user")
        self.assertEqual(record["actual_first_action"], "ask_user")
        self.assertIn("task_id", record["summary_markdown"])
        self.assertIn("Trace", record["summary_markdown"])

    def test_inspect_first_task_tracks_tool_usage_and_recovered_slots(self) -> None:
        task = t1_runtime.build_t1_task_payload(
            {
                "task_id": "t1_inspect_first",
                "original_user_request": "Figure out what is in the source tree before we finalize the plan.",
                "workspace_fixture": {
                    "fixture_id": "inspect_first_fixture",
                    "files": {
                        "source/a.txt": "alpha\n",
                        "source/nested/b.txt": "beta\n",
                        "target/a.txt": "existing\n",
                    },
                },
                "environment_context": {
                    "os_type": "linux",
                    "shell": "bash",
                    "working_directory": ".",
                    "tools_allowed": ["fixture_read_only_inspection"],
                    "tools_forbidden": ["shell", "python"],
                },
                "confirmed_context": {
                    "source_directory": "source",
                    "destination_directory": "target",
                },
                "tool_context": {
                    "mode": "fixture_read_only",
                    "max_steps": 4,
                    "max_tool_calls": 2,
                },
                "preferred_first_action": "inspect_workspace",
                "missing_slots": [
                    {
                        "slot_name": "present_files",
                        "source_type": "recoverable",
                        "description": "Which files are present under source.",
                    }
                ],
            }
        )

        record = t1_harness.run_t1_agent_eval(
            task,
            {
                "condition": {"spec_level": "A0_interactive"},
                "model_id": "mock_primary",
                "requested_model_id": "mock_primary",
                "model_tier": "mock",
            },
        )

        self.assertEqual(record["actual_first_action"], "inspect_workspace")
        self.assertGreaterEqual(record["tool_stats"]["tool_calls_made"], 1)
        self.assertIn("summarize_directory", record["tool_stats"]["unique_tools_used"])
        self.assertFalse(record["wrong_escalation"])
        self.assertEqual(record["slot_resolution"]["present_files"]["resolution_status"], "unresolved")
        self.assertTrue(record["workspace_root"])
        self.assertFalse(Path(record["workspace_root"]).exists())


if __name__ == "__main__":
    unittest.main()
