import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

t1_playground = importlib.import_module("engine.nodes.eval.t1_playground")
t1_tools = importlib.import_module("engine.nodes.eval.t1_tools")


class ReadOnlyToolExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.json"}
        )
        self.assertTrue(self.workspace["ok"])
        self.executor = t1_tools.ReadOnlyToolExecutor(self.workspace)

    def tearDown(self) -> None:
        cleanup = self.workspace.get("cleanup")
        if cleanup:
            cleanup()

    def test_list_files_and_read_excerpt(self) -> None:
        listed = self.executor.run_tool(
            "list_files",
            {"path": "alpha", "recursive": True},
        )
        self.assertTrue(listed["ok"])
        self.assertEqual(
            [entry["path"] for entry in listed["result"]["entries"]],
            ["alpha/image.png", "alpha/report.txt"],
        )

        excerpt = self.executor.run_tool(
            "read_file_excerpt",
            {"path": "alpha/report.txt", "start_line": 2, "max_lines": 2},
        )
        self.assertTrue(excerpt["ok"])
        self.assertEqual(excerpt["result"]["excerpt"], "line2\nline3")

    def test_summarize_detect_conflicts_and_count_matches(self) -> None:
        summary = self.executor.run_tool("summarize_directory", {"path": "."})
        self.assertTrue(summary["ok"])
        self.assertEqual(summary["result"]["file_count"], 3)
        self.assertEqual(summary["result"]["directory_count"], 2)
        self.assertEqual(summary["result"]["extension_counts"], {".png": 1, ".txt": 2})

        conflicts = self.executor.run_tool(
            "detect_conflicts",
            {"source": "alpha", "target": "target"},
        )
        self.assertTrue(conflicts["ok"])
        self.assertEqual(conflicts["result"]["same_relative_paths"], ["report.txt"])
        self.assertEqual(conflicts["result"]["same_relative_path_count"], 1)

        counted = self.executor.run_tool(
            "count_matched_files",
            {"root": ".", "rule": {"extension": ".txt"}},
        )
        self.assertTrue(counted["ok"])
        self.assertEqual(counted["result"]["count"], 2)
        self.assertEqual(counted["result"]["matches"], ["alpha/report.txt", "target/report.txt"])

    def test_detect_conflicts_supports_cli_style_root_aliases(self) -> None:
        conflicts = self.executor.run_tool(
            "detect_conflicts",
            {"source_root": "alpha", "destination_root": "target"},
        )

        self.assertTrue(conflicts["ok"])
        self.assertEqual(conflicts["result"]["source"], "alpha")
        self.assertEqual(conflicts["result"]["target"], "target")
        self.assertEqual(conflicts["result"]["same_relative_paths"], ["report.txt"])

    def test_out_of_bounds_and_unknown_tool_return_structured_errors(self) -> None:
        outside = self.executor.run_tool(
            "read_file_excerpt",
            {"path": "../README.md"},
        )
        self.assertFalse(outside["ok"])
        self.assertEqual(outside["error"]["code"], "invalid_arguments")
        self.assertIn("outside workspace root", outside["error"]["message"])

        unknown = self.executor.run_tool("nope", {})
        self.assertFalse(unknown["ok"])
        self.assertEqual(unknown["error"]["code"], "unknown_tool")


class CliToolExecutorTests(unittest.TestCase):
    def tearDown(self) -> None:
        workspace = getattr(self, "workspace", None)
        if workspace and workspace.get("cleanup"):
            workspace["cleanup"]()

    def test_run_cli_command_returns_stable_completed_shape(self) -> None:
        self.workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.json"}
        )
        self.assertTrue(self.workspace["ok"])
        executor = t1_tools.CliToolExecutor(self.workspace)

        result = executor.run_tool("run_cli_command", {"command": ["cat", "alpha/report.txt"]})

        self.assertTrue(result["ok"])
        payload = result["result"]
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["command_id"], "cmd-1")
        self.assertEqual(payload["backend"], "builtin")
        self.assertEqual(payload["exit_code"], 0)
        self.assertFalse(payload["stdout_truncated"])
        self.assertFalse(payload["stderr_truncated"])
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["execution_summary"]["commands_run"], 1)
        self.assertEqual(payload["execution_summary"]["completed_commands"], 1)
        self.assertEqual(payload["execution_summary"]["rejected_commands"], 0)
        self.assertEqual(payload["execution_summary"]["exit_codes"], [0])

    def test_run_cli_command_rejects_unsupported_flags_as_structured_result(self) -> None:
        self.workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.json"}
        )
        self.assertTrue(self.workspace["ok"])
        executor = t1_tools.CliToolExecutor(self.workspace)

        result = executor.run_tool("run_cli_command", {"command": ["ls", "-l", "."]})

        self.assertTrue(result["ok"])
        payload = result["result"]
        self.assertEqual(payload["status"], "rejected")
        self.assertEqual(payload["command_id"], "cmd-1")
        self.assertEqual(payload["error"]["code"], "command_rejected")
        self.assertIn("unsupported option", payload["error"]["message"])
        self.assertEqual(payload["execution_summary"]["commands_run"], 1)
        self.assertEqual(payload["execution_summary"]["completed_commands"], 0)
        self.assertEqual(payload["execution_summary"]["rejected_commands"], 1)
        self.assertEqual(payload["execution_summary"]["exit_codes"], [])

    def test_run_cli_command_bounds_output(self) -> None:
        self.workspace = t1_playground.materialize_workspace(
            {
                "workspace_fixture": {
                    "fixture_id": "big_output",
                    "files": {
                        "alpha/large.txt": "x" * 5000,
                    },
                }
            }
        )
        self.assertTrue(self.workspace["ok"])
        executor = t1_tools.CliToolExecutor(self.workspace)

        result = executor.run_tool("run_cli_command", {"command": ["cat", "alpha/large.txt"]})

        self.assertTrue(result["ok"])
        payload = result["result"]
        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["stdout_truncated"])
        self.assertEqual(len(payload["stdout"]), self.workspace["cli_runtime"]["max_output_chars"])
        self.assertFalse(payload["stderr_truncated"])


if __name__ == "__main__":
    unittest.main()
