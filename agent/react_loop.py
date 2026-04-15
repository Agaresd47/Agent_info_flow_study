import json
import os
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

from ..engine.core.builder import PipelineBuilder
from .tools import bind_builder, execute_tool, get_tool_specs

SYSTEM_PROMPT = """You operate a draft builder for quant research plans.

Available actions:
- add_step
- update_step
- connect_steps
- get_catalog
- get_details
- get_pipeline

Operating rules:
- Build the plan through tool calls, not plain-text answers.
- Prefer short stable ids like trigger, bars, momentum, rank, chat, report.
- `add_step` and `update_step` evaluate a step immediately and return either output or an error.
- Use catalog inspection before guessing a config shape.
- If a tool reports an error, repair the affected step instead of abandoning the draft.
- Use connect_steps so the draft has a clear ordered path, even when references already imply data flow.
- Only call `get_pipeline` after the draft contains a coherent ordered path.

For a simple momentum-ranking request, a sensible draft usually includes:
trigger.manual -> data.market_bars -> factor.momentum -> factor.rank -> research_chat
"""


class ReactLoopAgent:
    def __init__(self, builder: Optional[PipelineBuilder] = None):
        self.builder = builder or PipelineBuilder()
        bind_builder(self.builder)
        self.client = AsyncOpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL'),
        )
        self.model = os.getenv('REACT_MODEL', 'gpt-4o-mini')
        self.max_iters = 14

    async def run(self, prompt: str) -> Dict[str, Any]:
        coordinator = _LoopCoordinator(
            client=self.client,
            model=self.model,
            prompt=prompt,
            iteration_limit=self.max_iters,
        )
        transcript = await coordinator.run()
        return {'pipeline': self.builder.get_pipeline(), 'messages': transcript}


class _LoopCoordinator:
    def __init__(
        self,
        client: AsyncOpenAI,
        model: str,
        prompt: str,
        iteration_limit: int,
    ) -> None:
        self.client = client
        self.model = model
        self.iteration_limit = iteration_limit
        self.max_stalled_turns = 3
        self.max_failed_turns = 4
        self.messages: List[Dict[str, Any]] = self._starting_transcript(prompt)
        self._tool_specs = get_tool_specs()
        self._stalled_turns = 0
        self._failed_turns = 0

    async def run(self) -> List[Dict[str, Any]]:
        turn_count = 0
        while turn_count < self.iteration_limit:
            turn_count += 1
            reply = await self._next_model_message()
            self.messages.append(self._format_assistant_turn(reply))

            if not reply.tool_calls:
                self._stalled_turns += 1
                if self._stalled_turns >= self.max_stalled_turns:
                    self.messages.append(self._termination_message('Stopping because the assistant kept answering without tool use.'))
                    break
                self.messages.append(
                    self._repair_prompt(
                        'The previous turn did not use tools. Inspect the catalog or repair the draft through tool calls only.'
                    )
                )
                continue

            should_finish, feedback, turn_had_failure = await self._apply_requested_actions(reply.tool_calls)
            if should_finish:
                break

            if turn_had_failure:
                self._failed_turns += 1
            else:
                self._failed_turns = 0

            if feedback:
                self._stalled_turns += 1
                if self._failed_turns >= self.max_failed_turns or self._stalled_turns >= self.max_stalled_turns:
                    self.messages.append(self._termination_message(feedback))
                    break
                self.messages.append(self._repair_prompt(feedback))
            else:
                self._stalled_turns = 0

        if turn_count >= self.iteration_limit:
            self.messages.append(self._termination_message('Stopping at the iteration limit. Export the best coherent pipeline available.'))
        return self.messages

    async def _next_model_message(self) -> Any:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self._tool_specs,
            tool_choice='auto',
            temperature=0,
        )
        return completion.choices[0].message

    async def _apply_requested_actions(self, tool_calls: List[Any]) -> Tuple[bool, str, bool]:
        feedback_parts: List[str] = []
        turn_had_failure = False
        should_finish = False

        for tool_call in tool_calls:
            tool_message, result = await self._run_one_tool(tool_call)
            self.messages.append(tool_message)

            if not result.get('success', False):
                turn_had_failure = True
                feedback_parts.append(
                    'Tool {0} failed: {1}'.format(
                        tool_call.function.name,
                        result.get('error', 'unknown error'),
                    )
                )
                continue

            if tool_call.function.name == 'get_pipeline':
                analysis = result.get('analysis', {})
                if result.get('success'):
                    should_finish = True
                else:
                    feedback_parts.append(self._pipeline_feedback(analysis))

        feedback = ' '.join(part for part in feedback_parts if part).strip()
        return should_finish, feedback, turn_had_failure

    async def _run_one_tool(self, tool_call: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        raw_arguments = tool_call.function.arguments or '{}'
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            result = {
                'success': False,
                'error': 'Tool arguments were not valid JSON: {0}'.format(exc),
                'stage': 'tool-arguments',
            }
            return self._tool_result_message(tool_call, result), result

        result = await execute_tool(tool_call.function.name, parsed_arguments)
        return self._tool_result_message(tool_call, result), result

    def _tool_result_message(self, tool_call: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'role': 'tool',
            'tool_call_id': tool_call.id,
            'name': tool_call.function.name,
            'content': json.dumps(result, ensure_ascii=True, default=str),
        }

    def _starting_transcript(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt},
        ]

    def _format_assistant_turn(self, message: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            'role': 'assistant',
            'content': message.content or '',
        }
        if message.tool_calls:
            payload['tool_calls'] = [self._encode_tool_call(tool_call) for tool_call in message.tool_calls]
        return payload

    def _encode_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        return {
            'id': tool_call.id,
            'type': 'function',
            'function': {
                'name': tool_call.function.name,
                'arguments': tool_call.function.arguments,
            },
        }

    def _repair_prompt(self, feedback: str) -> Dict[str, str]:
        return {
            'role': 'user',
            'content': (
                feedback
                + ' Continue through tool use only. Inspect, repair, or extend the draft, '
                + 'then export it with get_pipeline once the ordered path is coherent.'
            ),
        }

    def _termination_message(self, reason: str) -> Dict[str, str]:
        return {
            'role': 'user',
            'content': reason,
        }

    def _pipeline_feedback(self, analysis: Dict[str, Any]) -> str:
        errors = analysis.get('errors', []) or []
        warnings = analysis.get('warnings', []) or []
        recommendations = analysis.get('recommended_next_actions', []) or []
        parts: List[str] = []
        if errors:
            parts.append('Pipeline is not coherent yet: {0}.'.format(' '.join(errors)))
        if warnings:
            parts.append('Warnings: {0}.'.format(' '.join(warnings)))
        if recommendations:
            parts.append('Next: {0}.'.format(' '.join(recommendations)))
        if not parts:
            parts.append('Pipeline export was not accepted. Repair the draft and retry.')
        return ' '.join(parts)
