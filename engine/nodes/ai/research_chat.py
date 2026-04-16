from typing import Any, Dict

from ..base import BaseStep


class ResearchChatStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Interview task:
        # Replace this mock with a real LLM-backed implementation.
        #
        # Expected behavior:
        # - accept config["prompt"]
        # - optionally accept a configurable model
        # - call a real chat completion API
        # - return a structured output such as:
        #   {
        #       "content": "...generated explanation...",
        #       "model": "..."
        #   }
        #
        # Handle API failures clearly and keep the output shape consistent.
        prompt = str(config.get("prompt", ""))
        return {"content": f"Research note: {prompt}", "model": "mock-research-chat"}
