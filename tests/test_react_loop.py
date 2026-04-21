import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT.parent))

from quant_react_interview.agent.tools import _get_pipeline
from quant_react_interview.agent.react_loop import _LoopCoordinator
from quant_react_interview.engine.core.builder import PipelineBuilder
from quant_react_interview.engine.nodes.data.market_bars import MarketBarsStep


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
                arguments='{"kind": "trigger.manual",',
            ),
        )

        tool_message = await coordinator._run_one_tool(tool_call)
        payload = json.loads(tool_message["content"])

        self.assertFalse(payload["success"])
        self.assertEqual(payload["stage"], "tooling")
        self.assertEqual(payload["raw_arguments"], '{"kind": "trigger.manual",')
        self.assertIn("valid JSON", payload["error"])

    async def test_get_pipeline_is_blocked_until_steps_execute_successfully(self) -> None:
        builder = PipelineBuilder()
        builder.add_step("trigger.manual", {"universe": ["sh.600000"]}, "trigger")

        result = await _get_pipeline(builder, {})

        self.assertFalse(result["success"])
        self.assertEqual(result["action"], "get_pipeline")
        self.assertIn("blocked", result["error"])
        self.assertEqual(len(result["failures"]), 1)
        self.assertIn("trigger", result["failures"][0])

    async def test_market_bars_reports_symbol_level_query_failures(self) -> None:
        step = MarketBarsStep()
        login_result = SimpleNamespace(error_code="0", error_msg="")
        logout_result = SimpleNamespace(error_code="0", error_msg="")
        query_result = SimpleNamespace(error_code="1", error_msg="bad symbol", next=lambda: False)

        with patch("quant_react_interview.engine.nodes.data.market_bars.bs.login", return_value=login_result), \
             patch("quant_react_interview.engine.nodes.data.market_bars.bs.logout", return_value=logout_result), \
             patch("quant_react_interview.engine.nodes.data.market_bars.bs.query_history_k_data_plus", return_value=query_result):
            with self.assertRaises(RuntimeError) as exc:
                await step.execute({"symbols": ["bad.symbol"], "lookback_days": 2}, None)

        self.assertIn("bad.symbol", str(exc.exception))
        self.assertIn("bad symbol", str(exc.exception))

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
                    "name": "update_step",
                    "error_stage": "execution",
                    "step_id": "bars",
                    "error": "missing symbols",
                }
            ],
            state_summary=[{"step_id": "bars", "execution_status": "Failed/Pending"}],
        )
        payload = json.loads(message["content"].split("\n\n", 1)[1])

        self.assertEqual(message["role"], "user")
        self.assertEqual(payload["failures"][0]["tool"], "update_step")
        self.assertEqual(payload["failures"][0]["stage"], "execution")
        self.assertEqual(payload["failures"][0]["step_id"], "bars")
        self.assertEqual(payload["draft_summary"][0]["step_id"], "bars")


if __name__ == "__main__":
    unittest.main()
