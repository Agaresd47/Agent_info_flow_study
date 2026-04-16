from typing import Any, Dict, List, Optional

from .context import ExecutionContext
from .registry import get_registry


class PipelineBuilder:
    def __init__(self, registry: Optional[Any] = None):
        self.registry = registry or get_registry()
        self.pipeline_id = 'builder_pipeline'
        self.pipeline_name = 'Untitled Pipeline'
        self._draft_steps: Dict[str, Dict[str, Any]] = {}
        self._runtime = ExecutionContext(self.pipeline_id)

    def add_step(self, kind: str, config: Dict[str, Any], step_id: Optional[str] = None) -> str:
        if kind not in self.registry.supported_kinds():
            raise ValueError('Unknown step kind: {0}'.format(kind))
        resolved_id = step_id or self._allocate_step_id(kind)
        self._draft_steps[resolved_id] = {
            'id': resolved_id,
            'kind': kind,
            'name': kind,
            'config': dict(config),
            'next': [],
        }
        return resolved_id

    def update_step(self, step_id: str, config: Dict[str, Any]) -> None:
        if step_id not in self._draft_steps:
            raise ValueError('Unknown step id: {0}'.format(step_id))
        current_config = self._draft_steps[step_id].setdefault('config', {})
        current_config.update(config)

    def connect_steps(self, source_id: str, target_id: str) -> None:
        if source_id not in self._draft_steps:
            raise ValueError('Unknown source step id: {0}'.format(source_id))
        if target_id not in self._draft_steps:
            raise ValueError('Unknown target step id: {0}'.format(target_id))
        chain = self._draft_steps[source_id].setdefault('next', [])
        if target_id not in chain:
            chain.append(target_id)

    async def execute_step(self, step_id: str) -> Any:
        if step_id not in self._draft_steps:
            raise ValueError('Unknown step id: {0}'.format(step_id))
        step_snapshot = self._draft_steps[step_id]
        prepared_config = self._materialize_inputs(step_snapshot.get('config', {}))
        handler = self.registry.create(step_snapshot['kind'])
        result = await handler.execute(prepared_config, self._runtime)
        self._runtime.set_output(step_id, result)
        return result

    def get_pipeline(self) -> Dict[str, Any]:
        return {
            'pipeline_id': self.pipeline_id,
            'name': self.pipeline_name,
            'steps': list(self._draft_steps.values()),
        }

    def _allocate_step_id(self, kind: str) -> str:
        stem = kind.replace('.', '_')
        candidate = stem
        sequence = 1
        while candidate in self._draft_steps:
            candidate = '{0}_{1}'.format(stem, sequence)
            sequence += 1
        return candidate

    def _materialize_inputs(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._materialize_inputs(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._materialize_inputs(item) for item in value]
        if self._is_reference(value):
            return self._read_reference(value)
        return value

    def _is_reference(self, value: Any) -> bool:
        return isinstance(value, str) and value.startswith('$')

    def _read_reference(self, reference: str) -> Any:
        try:
            return self._runtime.resolve_reference(reference)
        except Exception as exc:
            raise ValueError('Unresolved reference {0}: {1}'.format(reference, exc))

    def snapshot_step_ids(self) -> List[str]:
        return list(self._draft_steps.keys())
