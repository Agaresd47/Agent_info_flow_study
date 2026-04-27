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


if __name__ == "__main__":
    unittest.main()
