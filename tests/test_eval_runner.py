import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

eval_runner = importlib.import_module("scripts.eval_runner")


class EvalRunnerTests(unittest.TestCase):
    def test_apply_pricing_adds_cost_breakdown(self) -> None:
        usage = {
            "prompt_tokens": 1500,
            "completion_tokens": 500,
            "reasoning_tokens": 250,
            "cached_tokens": 0,
            "total_tokens": 2250,
            "estimated_cost_usd": 0.0,
            "latency_s": 0.2,
            "n_turns": 1,
        }
        pricing = {
            "prompt_per_1k_usd": 0.001,
            "completion_per_1k_usd": 0.002,
            "reasoning_per_1k_usd": 0.004,
        }

        priced = eval_runner.apply_pricing(usage, pricing)

        self.assertEqual(priced["prompt_cost_usd"], 0.0015)
        self.assertEqual(priced["completion_cost_usd"], 0.001)
        self.assertEqual(priced["reasoning_cost_usd"], 0.001)
        self.assertEqual(priced["estimated_cost_usd"], 0.0035)

    def test_provider_fallback_warning_and_actual_model_are_persisted(self) -> None:
        task = {
            "task_id": "t1_fallback",
            "original_user_request": "Archive the old log files from the app directory.",
            "environment_context": {
                "os_type": "linux",
                "shell": "bash",
                "working_directory": "/srv/app",
                "tools_allowed": ["bash"],
                "tools_forbidden": ["python"],
            },
            "missing_slots": [
                {"slot_name": "age_threshold", "description": "which files count as old"},
            ],
            "user_reply_if_asked": {
                "age_threshold": "Files older than 14 days.",
            },
        }
        config = eval_runner.ProviderConfig(
            model_id="openai_gpt5_nano",
            provider="openai",
            api_model_name="broken-model-name",
            role_tags=["weak", "worker"],
            supports_json_mode=True,
            env={"api_key_var": "OPENAI_API_KEY"},
            pricing={
                "prompt_per_1k_usd": 0.001,
                "completion_per_1k_usd": 0.002,
                "reasoning_per_1k_usd": 0.003,
            },
            fallback_api_model_names=["gpt-5-nano"],
        )

        def fake_openai(provider_config, api_model_name, prompt, started, warnings):
            if api_model_name == "broken-model-name":
                raise RuntimeError("404 model_not_found")
            usage = eval_runner.apply_pricing(
                {
                    "prompt_tokens": 1000,
                    "completion_tokens": 500,
                    "reasoning_tokens": 250,
                    "cached_tokens": 0,
                    "total_tokens": 1750,
                    "estimated_cost_usd": 0.0,
                    "latency_s": 0.3,
                    "n_turns": 1,
                },
                provider_config.pricing,
            )
            return eval_runner.ProviderResult(
                text="I need clarification about which files count as old before I can safely execute anything.",
                actual_model_name=api_model_name,
                provider=provider_config.provider,
                usage=usage,
                warnings=list(warnings),
                metadata={"status": "completed"},
            )

        with patch.object(eval_runner, "call_openai", side_effect=fake_openai):
            record = eval_runner.build_t1_run(task, config, "A0_strict", seed=0, provider_mode="real")

        self.assertEqual(record["model_id"], "gpt-5-nano")
        self.assertEqual(record["requested_model_id"], "openai_gpt5_nano")
        self.assertEqual(len(record["provider_warnings"]), 1)
        self.assertIn("broken-model-name", record["provider_warnings"][0])
        self.assertGreater(record["usage"]["estimated_cost_usd"], 0.0)


if __name__ == "__main__":
    unittest.main()
