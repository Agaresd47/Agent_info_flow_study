import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

t1_harness = importlib.import_module("engine.nodes.eval.t1_harness")
t1_runtime = importlib.import_module("engine.nodes.eval.t1_runtime")


class T1HarnessTests(unittest.TestCase):
    def test_read_only_task_runs_loop_and_emits_completed_judge_contract(self) -> None:
        task = t1_runtime.build_t1_task_payload(
            {
                "task_id": "t1_read_only_contract",
                "original_user_request": "Inspect the source tree before finalizing the dry-run plan.",
                "workspace_fixture": {
                    "fixture_id": "read_only_contract_fixture",
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

        self.assertTrue(record["agent_trace"])
        self.assertTrue(record["summary_markdown"])
        self.assertEqual(record["preferred_first_action"], "inspect_workspace")
        self.assertEqual(record["actual_first_action"], "inspect_workspace")
        self.assertIn("task_id", record["summary_markdown"])
        self.assertIn("Trace", record["summary_markdown"])
        self.assertEqual(record["judge_inputs"]["slice"], "read_only")
        self.assertEqual(record["judge_outputs"]["judge_status"], "completed")

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
        self.assertEqual(record["judge_inputs"]["judge_mode"], "deterministic_placeholder")
        self.assertEqual(record["judge_outputs"]["judge_status"], "completed")

    def test_cli_test_task_tracks_execution_and_policy_surface(self) -> None:
        task = t1_runtime.build_t1_task_payload(
            {
                "task_id": "t1_cli_contract",
                "original_user_request": "Run a bounded dry run inside the workspace.",
                "workspace_fixture": {
                    "fixture_id": "cli_contract_fixture",
                    "files": {
                        "reports/input.txt": "hello\n",
                    },
                },
                "environment_context": {
                    "os_type": "linux",
                    "shell": "bash",
                    "working_directory": ".",
                    "tools_allowed": ["bash"],
                    "tools_forbidden": ["python"],
                },
                "confirmed_context": {
                    "source_directory": "reports",
                },
                "tool_context": {
                    "mode": "fixture_cli_test",
                    "max_steps": 3,
                    "max_tool_calls": 2,
                },
                "preferred_first_action": "execute_cli",
                "missing_slots": [],
            }
        )

        def action_resolver(_state: dict) -> dict:
            if _state["cli_execution_log"]:
                return {
                    "action_type": "final_answer",
                    "content": "Dry run completed inside the bounded workspace.",
                    "targeted_slots": [],
                }
            return {
                "action_type": "execute_cli",
                "command": "bash -lc \"pwd\"",
                "purpose": "Exercise the bounded CLI substrate.",
                "targeted_slots": [],
            }

        record = t1_harness.run_t1_agent_eval(
            task,
            {
                "condition": {"spec_level": "A1", "slice": "cli_test"},
                "model_id": "mock_primary",
                "requested_model_id": "mock_primary",
                "model_tier": "mock",
            },
            action_resolver=action_resolver,
        )

        self.assertEqual(record["eval_slice"], "cli_test")
        self.assertEqual(record["judge_inputs"]["slice"], "cli_test")
        self.assertEqual(record["judge_outputs"]["judge_status"], "completed")
        self.assertTrue(record["judge_inputs"]["cli_attempted"])
        self.assertTrue(record["cli_execution_log"])
        self.assertTrue(record["tool_policy_decisions"])
        self.assertEqual(record["tool_policy_decisions"][0]["decision"], "cli_execution_policy")


if __name__ == "__main__":
    unittest.main()
