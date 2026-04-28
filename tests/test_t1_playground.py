import importlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

t1_playground = importlib.import_module("engine.nodes.eval.t1_playground")


class MaterializeWorkspaceTests(unittest.TestCase):
    def test_materialize_workspace_from_json_descriptor(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.json"}
        )
        self.assertTrue(workspace["ok"])
        root = Path(workspace["root"])
        self.assertEqual(workspace["fixture_id"], "json_fixture")
        self.assertTrue((root / "alpha" / "report.txt").is_file())
        self.assertEqual((root / "target" / "report.txt").read_text(encoding="utf-8"), "existing\n")
        workspace["cleanup"]()
        self.assertFalse(root.exists())

    def test_materialize_workspace_from_yaml_descriptor(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.yaml"}
        )
        self.assertTrue(workspace["ok"])
        root = Path(workspace["root"])
        self.assertEqual(workspace["fixture_id"], "yaml_fixture")
        self.assertEqual((root / "docs" / "readme.md").read_text(encoding="utf-8"), "hello yaml")
        workspace["cleanup"]()

    def test_materialize_workspace_from_static_tree(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_static_tree/source"}
        )
        self.assertTrue(workspace["ok"])
        root = Path(workspace["root"])
        self.assertEqual((root / "a.txt").read_text(encoding="utf-8"), "alpha\n")
        self.assertEqual((root / "nested" / "b.log").read_text(encoding="utf-8"), "beta\n")
        workspace["cleanup"]()

    def test_materialize_rejects_escaping_paths_in_descriptor(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {
                "workspace_fixture": {
                    "fixture_id": "bad_fixture",
                    "files": {
                        "../escape.txt": "nope",
                    },
                }
            }
        )
        self.assertFalse(workspace["ok"])
        self.assertEqual(workspace["error"]["code"], "materialize_failed")

    def test_materialize_normalizes_windows_style_paths_in_list_entries(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {
                "workspace_fixture": {
                    "fixture_id": "windows_fixture",
                    "files": [
                        {"path": r"C:\data\report.txt", "content": "hello"},
                    ],
                    "entries": [
                        {"path": r"logs\latest.txt", "content": "done"},
                    ],
                }
            }
        )
        self.assertTrue(workspace["ok"])
        root = Path(workspace["root"])
        self.assertEqual((root / "C" / "data" / "report.txt").read_text(encoding="utf-8"), "hello")
        self.assertEqual((root / "logs" / "latest.txt").read_text(encoding="utf-8"), "done")
        workspace["cleanup"]()

    def test_materialize_exposes_bounded_cli_runtime_contract(self) -> None:
        workspace = t1_playground.materialize_workspace(
            {"workspace_fixture": "fixtures/t1_descriptor.json"}
        )
        self.assertTrue(workspace["ok"])
        runtime = workspace["cli_runtime"]
        self.assertTrue(runtime["builtin_only"])
        self.assertEqual(runtime["max_output_chars"], 4000)
        self.assertEqual(runtime["shell_mode"], "argv_only")
        self.assertEqual(runtime["allowed_options"]["mkdir"], ["-p", "--parents"])
        workspace["cleanup"]()


if __name__ == "__main__":
    unittest.main()
