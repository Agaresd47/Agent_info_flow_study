import os
from typing import Any, Dict

from ..base import BaseStep


class ResearchChatStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        prompt = str(config.get('prompt', '')).strip()
        if not prompt:
            raise ValueError('research_chat requires a non-empty prompt')

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY is not set for research_chat')

        model = str(
            config.get('model')
            or os.getenv('RESEARCH_CHAT_MODEL')
            or os.getenv('OPENAI_MODEL')
            or 'gpt-4o-mini'
        )
        instructions = str(
            config.get('instructions')
            or 'You are a concise quant research assistant. Explain numeric outputs clearly and avoid fabricating facts.'
        )

        try:
            from openai import AsyncOpenAI
        except Exception as exc:
            raise ValueError('openai dependency is unavailable for research_chat: {0}'.format(exc))

        client = AsyncOpenAI(api_key=api_key, base_url=os.getenv('OPENAI_BASE_URL'))

        try:
            response = await client.responses.create(
                model=model,
                instructions=instructions,
                input=prompt,
            )
        except Exception as exc:
            raise ValueError('research_chat API call failed: {0}'.format(exc))

        content = getattr(response, 'output_text', '') or ''
        if not content:
            raise ValueError('research_chat returned an empty response')

        usage = getattr(response, 'usage', None)
        usage_payload = None
        if usage is not None:
            usage_payload = {
                'input_tokens': getattr(usage, 'input_tokens', None),
                'output_tokens': getattr(usage, 'output_tokens', None),
                'total_tokens': getattr(usage, 'total_tokens', None),
            }

        return {
            'content': content,
            'model': model,
            'response_id': getattr(response, 'id', None),
            'usage': usage_payload,
        }
