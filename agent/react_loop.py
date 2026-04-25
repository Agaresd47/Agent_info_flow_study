import json
from typing import Any, Dict, List, Optional

from ..engine.core.builder import PipelineBuilder
from .tools import bind_builder, execute_tool, get_tool_specs

SYSTEM_PROMPT = """You build draft agent-evaluation pipelines through tool use.

Guidelines:
1. 'add_step' and 'update_step' expect a 'config' object with the fields required by the eval step kind.
   Common patterns:
   - eval.task: {"request": "Clean up this folder", "expected_clarifications": ["target folder"], "risk_markers": ["delete"]}
   - planner.spec: {"spec": {"objective": "...", "actions": [...], "constraints": [...], "acceptance_criteria": [...]}}
   - worker.review: {"spec": "$spec_v1", "required_clarifications": "$task['expected_clarifications']", "risk_markers": "$task['risk_markers']"}
   - revision.score: {"before": "$review_v1", "after": "$review_v2"}
2. When you choose a step_id, reuse that exact id in later references. Do not invent a new id in config strings.
3. Use '$step_id' references to pass outputs between steps.
4. If a step fails validation or execution, inspect the state and repair it with 'update_step'.
5. Use 'connect_steps' to define execution order.
6. Export with 'get_pipeline' only after every step has executed successfully.
"""


class ReactLoopAgent:
    def __init__(self, builder: Optional[PipelineBuilder] = None, client: Optional[Any] = None, model: str = "scaffold-model"):
        self.builder = builder or PipelineBuilder()
        bind_builder(self.builder)
        self.client = client
        self.model = model
        self.max_iters = 12

    async def run(self, prompt: str) -> Dict[str, Any]:
        if self.client is None:
            raise RuntimeError("ReactLoopAgent needs an injected chat client before it can run model-backed planning.")
        coordinator = _LoopCoordinator(
            client=self.client,
            model=self.model,
            prompt=prompt,
            iteration_limit=self.max_iters,
        )
        outcome = await coordinator.run()
        return {
            "pipeline": self.builder.get_pipeline(),
            "messages": outcome["messages"],
            "status": outcome["status"],
            "termination_reason": outcome["termination_reason"],
            "draft_summary": outcome["draft_summary"],
        }


class _LoopCoordinator:
    def __init__(
        self,
        client: Any,
        model: str,
        prompt: str,
        iteration_limit: int,
    ) -> None:
        self.client = client
        self.model = model
        self.iteration_limit = iteration_limit
        self.messages: List[Dict[str, Any]] = self._starting_transcript(prompt)
        self._tool_specs = get_tool_specs()

    async def run(self) -> List[Dict[str, Any]]:
        turn_count = 0
        consecutive_nudges = 0

        while turn_count < self.iteration_limit:
            turn_count += 1
            reply = await self._next_model_message()
            self.messages.append(self._format_assistant_turn(reply))

            if not reply.tool_calls:
                consecutive_nudges += 1
                state_summary = self._get_current_draft_summary()
                self.messages.append(self._idle_message(consecutive_nudges, state_summary))
                if consecutive_nudges >= 4:
                    return self._finish(
                        status="incomplete",
                        termination_reason="idle_limit",
                    )
                continue

            consecutive_nudges = 0
            tool_results = await self._apply_requested_actions(reply.tool_calls)
            failures = [result for result in tool_results if not result.get("success", True)]
            if failures:
                state_summary = self._get_current_draft_summary()
                self.messages.append(self._failure_message(failures, state_summary))

            # Exit if get_pipeline succeeded
            finished = any(
                r.get("name") == "get_pipeline" and r.get("success")
                for r in tool_results
            )
            if finished:
                return self._finish(
                    status="success",
                    termination_reason="pipeline_exported",
                )

        return self._finish(
            status="incomplete",
            termination_reason="iteration_limit",
        )

    def _get_current_draft_summary(self) -> List[Dict[str, Any]]:
        # Requires bind_builder
        from .tools import _active_builder
        if _active_builder:
            return _active_builder.get_summary()
        return []

    async def _next_model_message(self) -> Any:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=self._tool_specs,
            tool_choice="auto",
            temperature=0,
        )
        return completion.choices[0].message

    async def _apply_requested_actions(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
        results = []
        for tool_call in tool_calls:
            tool_message = await self._run_one_tool(tool_call)
            self.messages.append(tool_message)
            content = json.loads(tool_message["content"])
            results.append(
                {
                    "name": tool_call.function.name,
                    "success": content.get("success", True),
                    "content": content,
                    "error_stage": content.get("stage"),
                    "step_id": content.get("step_id"),
                    "error": content.get("error"),
                }
            )
        return results

    async def _run_one_tool(self, tool_call: Any) -> Dict[str, Any]:
        raw_arguments = tool_call.function.arguments or "{}"
        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            return {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": json.dumps(
                    {
                        "success": False,
                        "error": (
                            "Tool arguments must be valid JSON. "
                            "Revise the arguments and retry the tool call. "
                            "JSON parse error: {0}".format(str(exc))
                        ),
                        "stage": "tooling",
                        "raw_arguments": raw_arguments,
                    },
                    ensure_ascii=True,
                ),
            }
        result = await execute_tool(tool_call.function.name, parsed_arguments)
        return {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": tool_call.function.name,
            "content": json.dumps(result, ensure_ascii=True),
        }

    def _starting_transcript(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def _format_assistant_turn(self, message: Any) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if message.tool_calls:
            payload["tool_calls"] = [self._encode_tool_call(tool_call) for tool_call in message.tool_calls]
        return payload

    def _encode_tool_call(self, tool_call: Any) -> Dict[str, Any]:
        return {
            "id": tool_call.id,
            "type": "function",
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }

    def _idle_message(
        self,
        consecutive_nudges: int,
        state_summary: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, str]:
        if consecutive_nudges == 1:
            content = "Continue with tool use. Inspect the draft, add missing steps, or export when it is ready."
        elif consecutive_nudges == 2:
            content = "No tool call was made in the last turn. Use a tool to inspect or modify the draft before continuing."
        elif consecutive_nudges == 3:
            content = (
                "The draft is not advancing. Use tools to repair or export it now. "
                "If you need more context, inspect the catalog or step details."
            )
        else:
            content = (
                "The draft has stalled for several turns. This run will stop unless you advance it through tool use."
            )
        if state_summary:
            content += "\n\nCurrent Draft State:\n" + json.dumps(state_summary, indent=2)

        return {
            "role": "user",
            "content": content,
        }

    def _failure_message(
        self,
        failures: List[Dict[str, Any]],
        state_summary: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        payload = {
            "failures": [
                {
                    "tool": failure["name"],
                    "stage": failure.get("error_stage"),
                    "step_id": failure.get("step_id"),
                    "error": failure.get("error"),
                }
                for failure in failures
            ],
            "draft_summary": state_summary,
            "guidance": "Review the failures, repair invalid steps with update_step, and retry only when the draft is consistent.",
        }
        return {
            "role": "user",
            "content": "Tool execution failed.\n\n" + json.dumps(payload, indent=2),
        }

    def _finish(self, status: str, termination_reason: str) -> Dict[str, Any]:
        return {
            "messages": self.messages,
            "status": status,
            "termination_reason": termination_reason,
            "draft_summary": self._get_current_draft_summary(),
        }
