from typing import Any, Dict

from ..base import RuntimeStep
from .t1_harness import run_t1_agent_eval
from .t1_runtime import build_t1_task_payload


class EvalTaskStep(RuntimeStep):
    async def run(self, config: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        task = build_t1_task_payload(config)
        run_record = run_t1_agent_eval(task, config)
        payload = dict(task)
        payload.update(run_record)
        return payload
