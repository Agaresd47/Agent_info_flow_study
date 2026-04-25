import importlib
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))
PACKAGE = ROOT.name

react_loop = importlib.import_module(f"{PACKAGE}.agent.react_loop")
tools = importlib.import_module(f"{PACKAGE}.agent.tools")
builder_module = importlib.import_module(f"{PACKAGE}.engine.core.builder")

_LoopCoordinator = react_loop._LoopCoordinator
_get_pipeline = tools._get_pipeline
PipelineBuilder = builder_module.PipelineBuilder


class ReactLoopEdgeCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_tool_arguments_are_reported_without_crashing(self) -> None:
        coordinator = _LoopCoordinator(
            client=SimpleNamespace(),
            model="test-model",
            prompt="test prompt",
            iteration_limit=1,
        )
        tool_call = SimpleNamespace(
            id="call_1",
            function=SimpleNamespace(
                name="add_step",
                arguments='{"kind": "eval.task",',
            ),
        )

        tool_message = await coordinator._run_one_tool(tool_call)
        payload = json.loads(tool_message["content"])

        self.assertFalse(payload["success"])
        self.assertEqual(payload["stage"], "tooling")
        self.assertEqual(payload["raw_arguments"], '{"kind": "eval.task",')
        self.assertIn("valid JSON", payload["error"])

    async def test_get_pipeline_is_blocked_until_steps_execute_successfully(self) -> None:
        builder = PipelineBuilder()
        builder.add_step("eval.task", {"request": "Clean up files."}, "task")

        result = await _get_pipeline(builder, {})

        self.assertFalse(result["success"])
        self.assertEqual(result["action"], "get_pipeline")
        self.assertIn("blocked", result["error"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertIn("task", result["failures"][0])

    async def test_loop_returns_idle_limit_when_model_never_uses_tools(self) -> None:
        coordinator = _LoopCoordinator(
            client=SimpleNamespace(),
            model="test-model",
            prompt="test prompt",
            iteration_limit=4,
        )

        async def no_tool_reply() -> SimpleNamespace:
            return SimpleNamespace(content="thinking", tool_calls=[])

        coordinator._next_model_message = no_tool_reply  # type: ignore[method-assign]
        outcome = await coordinator.run()

        self.assertEqual(outcome["status"], "incomplete")
        self.assertEqual(outcome["termination_reason"], "idle_limit")
        self.assertGreaterEqual(len(outcome["messages"]), 4)

    async def test_failure_feedback_is_structured_for_model_recovery(self) -> None:
        coordinator = _LoopCoordinator(
            client=SimpleNamespace(),
            model="test-model",
            prompt="test prompt",
            iteration_limit=1,
        )

        message = coordinator._failure_message(
            failures=[
                {
                    "name": "worker.review",
                    "error_stage": "execution",
                    "step_id": "review",
                    "error": "spec must resolve to an object",
                }
            ],
            state_summary=[{"step_id": "review", "execution_status": "Failed/Pending"}],
        )
        payload = json.loads(message["content"].split("\n\n", 1)[1])

        self.assertEqual(message["role"], "user")
        self.assertEqual(payload["failures"][0]["tool"], "worker.review")
        self.assertEqual(payload["failures"][0]["stage"], "execution")
        self.assertEqual(payload["failures"][0]["step_id"], "review")
        self.assertEqual(payload["draft_summary"][0]["step_id"], "review")


if __name__ == "__main__":
    unittest.main()
