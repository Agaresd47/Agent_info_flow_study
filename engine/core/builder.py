from typing import Any, Dict, List, Optional

from .context import ExecutionContext
from .registry import get_registry


class PipelineBuilder:
    def __init__(self, registry: Optional[Any] = None):
        self.registry = registry or get_registry()
        self.pipeline_id = "builder_pipeline"
        self.pipeline_name = "Untitled Pipeline"
        self._draft_steps: Dict[str, Dict[str, Any]] = {}
        self._runtime = ExecutionContext(self.pipeline_id)
        self.step_execution_results: Dict[str, Dict[str, Any]] = {}

    def add_step(self, kind: str, config: Dict[str, Any], step_id: Optional[str] = None) -> str:
        resolved_id = step_id or self._allocate_step_id(kind)
        self._draft_steps[resolved_id] = {
            "id": resolved_id,
            "kind": kind,
            "name": kind,
            "config": dict(config),
            "next": [],
        }
        return resolved_id

    def update_step(self, step_id: str, config: Dict[str, Any]) -> None:
        current_config = self._draft_steps[step_id].setdefault("config", {})
        current_config.update(config)

    def connect_steps(self, source_id: str, target_id: str) -> None:
        chain = self._draft_steps[source_id].setdefault("next", [])
        if target_id not in chain:
            chain.append(target_id)

    async def execute_step(self, step_id: str) -> Any:
        step_snapshot = self._draft_steps[step_id]
        prepared_config = self._materialize_inputs(step_snapshot.get("config", {}))
        handler = self.registry.create(step_snapshot["kind"])
        try:
            result = await handler.execute(prepared_config, self._runtime)
            self._runtime.set_output(step_id, result)
            self.step_execution_results[step_id] = {"success": True, "output": result}
            return result
        except Exception as e:
            self.step_execution_results[step_id] = {"success": False, "error": str(e)}
            raise e

    def get_pipeline(self) -> Dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "name": self.pipeline_name,
            "steps": list(self._draft_steps.values()),
        }

    def _allocate_step_id(self, kind: str) -> str:
        stem = kind.replace(".", "_")
        candidate = stem
        sequence = 1
        while candidate in self._draft_steps:
            candidate = "{0}_{1}".format(stem, sequence)
            sequence += 1
        return candidate

    def _materialize_inputs(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._materialize_inputs(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._materialize_inputs(item) for item in value]
        if isinstance(value, str):
            if self._is_whole_reference(value):
                return self._read_reference(value)
            return self._interpolate_string(value)
        return value

    def _is_whole_reference(self, value: str) -> bool:
        return value.startswith("$") and " " not in value

    def _interpolate_string(self, text: str) -> str:
        import re
        ref_pattern = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*(?:\[['\"][^'\"]+['\"]\]|\[\d+\])*")

        def replace_match(match: re.Match) -> str:
            ref = match.group(0)
            resolved = self._read_reference(ref)
            if resolved == ref: # Fallback if resolution fails
                return ref
            return str(resolved)

        return ref_pattern.sub(replace_match, text)

    def _read_reference(self, reference: str) -> Any:
        try:
            return self._runtime.resolve_reference(reference)
        except Exception:
            return reference

    def snapshot_step_ids(self) -> List[str]:
        return list(self._draft_steps.keys())

    def get_summary(self) -> List[Dict[str, Any]]:
        summary = []
        for sid, step in self._draft_steps.items():
            status = self.step_execution_results.get(sid, {"success": False, "error": "Not executed"})
            summary.append({
                "step_id": sid,
                "kind": step["kind"],
                "config": step["config"],
                "connected_to": step["next"],
                "execution_status": "Success" if status.get("success") else "Failed/Pending",
                "last_error": status.get("error") if not status.get("success") else None
            })
        return summary
