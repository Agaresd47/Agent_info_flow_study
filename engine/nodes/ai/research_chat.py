import os
from typing import Any, Dict

from openai import AsyncOpenAI

from ..base import BaseStep


class ResearchChatStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Call LLM for research insights
        prompt = config.get("prompt")
        if not prompt:
            raise ValueError("The 'prompt' field is required for research_chat and cannot be empty.")

        model = config.get("model") or os.getenv("RESEARCH_MODEL") or "gpt-4o-mini"

        client = AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
        )

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a quant research assistant. Provide concise, data-driven insights.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            content = response.choices[0].message.content
            return {
                "content": content,
                "model": model,
                "status": "success",
            }
        except Exception as e:
            raise RuntimeError(f"LLM call failed: {str(e)}")
