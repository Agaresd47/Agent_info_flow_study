from typing import Any, Dict

from ..base import RuntimeStep
from .t1_runtime import build_t1_task_payload, run_t1_auto_eval


class EvalTaskStep(RuntimeStep):
    async def run(self, config: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        task = build_t1_task_payload(config)
        run_record = run_t1_auto_eval(task, config)
        payload = dict(task)
        payload.update(run_record)
        return payload
