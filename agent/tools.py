from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from ..engine.core.builder import PipelineBuilder
from .catalog import get_catalog as catalog_list
from .catalog import get_details as catalog_details
from .catalog import get_required_fields, supported_kinds

ToolHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

_active_builder: Optional[PipelineBuilder] = None


def bind_builder(builder: PipelineBuilder) -> None:
    global _active_builder
    _active_builder = builder


def get_tool_specs() -> List[Dict[str, Any]]:
    supported = supported_kinds()
    config_schema = {
        'type': 'object',
        'description': (
            'Open-ended config object for the step. Inspect get_details(kind) before guessing fields. '
            "References must use strings like $trigger['universe'] or $rank['ordered']."
        ),
        'additionalProperties': True,
    }
    return [
        _function_spec(
            name='add_step',
            description=(
                'Create one draft step. Prefer short ids like trigger, bars, momentum, rank, chat. '
                'Only use supported kinds. If the config shape is unclear, call get_details first.'
            ),
            properties={
                'kind': {
                    'type': 'string',
                    'enum': supported,
                    'description': 'One supported step kind from the catalog.',
                },
                'step_id': {
                    'type': 'string',
                    'description': 'Optional stable id such as trigger, bars, momentum, rank, chat, report.',
                },
                'config': config_schema,
            },
            required=['kind', 'config'],
        ),
        _function_spec(
            name='update_step',
            description=(
                'Modify one existing step config and immediately re-evaluate it. '
                'Use this after a failed add_step or when you need to repair missing fields or references.'
            ),
            properties={
                'step_id': {'type': 'string', 'description': 'Existing step id to repair or refine.'},
                'config': config_schema,
            },
            required=['step_id', 'config'],
        ),
        _function_spec(
            name='connect_steps',
            description=(
                'Declare an execution edge from source_id to target_id. '
                'Use this even when references already imply data flow so the final pipeline is clearly ordered.'
            ),
            properties={
                'source_id': {'type': 'string', 'description': 'Upstream step id.'},
                'target_id': {'type': 'string', 'description': 'Downstream step id.'},
            },
            required=['source_id', 'target_id'],
        ),
        _function_spec(
            name='get_catalog',
            description=(
                'Inspect all available step kinds at a high level. '
                'Use this at the start when you need the overall shape of the planner surface.'
            ),
            properties={},
            required=[],
        ),
        _function_spec(
            name='get_details',
            description=(
                'Inspect one step kind in detail, including config fields, output shape, references, and planning notes.'
            ),
            properties={
                'kind': {
                    'type': 'string',
                    'enum': supported,
                    'description': 'Supported step kind to inspect.',
                },
            },
            required=['kind'],
        ),
        _function_spec(
            name='get_pipeline',
            description=(
                'Export the current draft. Only do this when the draft is connected, has the required fields, '
                'and looks coherent enough to run end-to-end.'
            ),
            properties={},
            required=[],
        ),
    ]


async def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if _active_builder is None:
        return {'success': False, 'error': 'Builder not bound', 'stage': 'tooling'}

    handlers = _tool_handlers(_active_builder)
    if name not in handlers:
        return {'success': False, 'error': 'Unknown tool: {0}'.format(name), 'stage': 'tooling'}

    try:
        return await handlers[name](arguments)
    except Exception as exc:
        return {'success': False, 'error': str(exc), 'stage': 'tooling'}


def _function_spec(
    name: str,
    description: str,
    properties: Dict[str, Any],
    required: List[str],
) -> Dict[str, Any]:
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': {
                'type': 'object',
                'properties': properties,
                'required': required,
            },
        },
    }


def _tool_handlers(builder: PipelineBuilder) -> Dict[str, ToolHandler]:
    return {
        'add_step': lambda payload: _add_step(builder, payload),
        'update_step': lambda payload: _update_step(builder, payload),
        'connect_steps': lambda payload: _connect_steps(builder, payload),
        'get_catalog': lambda payload: _get_catalog(payload),
        'get_details': lambda payload: _get_details(payload),
        'get_pipeline': lambda payload: _get_pipeline(builder, payload),
    }


async def _add_step(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    created_id = builder.add_step(
        kind=payload['kind'],
        config=payload.get('config', {}),
        step_id=payload.get('step_id'),
    )
    result = await _run_step(builder, created_id)
    result['action'] = 'add_step'
    result['current_step_ids'] = builder.snapshot_step_ids()
    return result


async def _update_step(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    step_id = payload['step_id']
    builder.update_step(step_id, payload.get('config', {}))
    result = await _run_step(builder, step_id)
    result['action'] = 'update_step'
    result['current_step_ids'] = builder.snapshot_step_ids()
    return result


async def _connect_steps(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    builder.connect_steps(payload['source_id'], payload['target_id'])
    pipeline = builder.get_pipeline()
    return {
        'success': True,
        'action': 'connect_steps',
        'source_id': payload['source_id'],
        'target_id': payload['target_id'],
        'edge_count': _count_edges(pipeline),
    }


async def _get_catalog(_: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'success': True,
        'action': 'get_catalog',
        'catalog': catalog_list(),
        'planning_hint': 'Use get_details for exact config fields before add_step.',
    }


async def _get_details(payload: Dict[str, Any]) -> Dict[str, Any]:
    details = catalog_details(payload['kind'])
    if 'error' in details:
        return {'success': False, 'action': 'get_details', 'error': details['error']}
    return {'success': True, 'action': 'get_details', 'details': details}


async def _get_pipeline(builder: PipelineBuilder, _: Dict[str, Any]) -> Dict[str, Any]:
    pipeline = builder.get_pipeline()
    analysis = _assess_pipeline(pipeline)
    return {
        'success': analysis['is_coherent'],
        'action': 'get_pipeline',
        'pipeline': pipeline,
        'analysis': analysis,
    }


async def _run_step(builder: PipelineBuilder, step_id: str) -> Dict[str, Any]:
    try:
        output = await builder.execute_step(step_id)
    except Exception as exc:
        return {'success': False, 'step_id': step_id, 'error': str(exc), 'stage': 'execution'}
    return {'success': True, 'step_id': step_id, 'output': output, 'stage': 'execution'}


def _assess_pipeline(pipeline: Dict[str, Any]) -> Dict[str, Any]:
    steps = list(pipeline.get('steps', []))
    if not steps:
        return {
            'is_coherent': False,
            'step_count': 0,
            'errors': ['Pipeline is empty.'],
            'warnings': [],
            'recommended_next_actions': ['Add the first step, usually trigger.manual.'],
        }

    step_ids = [step.get('id') for step in steps]
    known_ids = set(step_ids)
    errors: List[str] = []
    warnings: List[str] = []

    if len(step_ids) != len(known_ids):
        errors.append('Step ids must be unique.')

    dependencies = _collect_dependencies(steps)
    edge_count = _count_edges(pipeline)

    for step in steps:
        step_id = step.get('id', '<missing>')
        kind = step.get('kind', '')
        if kind not in supported_kinds():
            errors.append('Step {0} uses unsupported kind {1}.'.format(step_id, kind))
            continue

        config = step.get('config', {}) or {}
        missing = [field for field in get_required_fields(kind) if field not in config]
        if missing:
            errors.append('Step {0} is missing required fields: {1}.'.format(step_id, ', '.join(missing)))

        unresolved = _unknown_reference_roots(config, known_ids)
        if unresolved:
            errors.append(
                'Step {0} references unknown step ids: {1}.'.format(step_id, ', '.join(sorted(unresolved)))
            )

        if len(steps) > 1 and not dependencies.get(step_id) and not (step.get('next') or []):
            warnings.append('Step {0} is disconnected from the rest of the draft.'.format(step_id))

    if len(steps) > 1 and edge_count == 0 and all(not parents for parents in dependencies.values()):
        errors.append('Pipeline has multiple steps but no ordering edges or references between them.')

    connected_components = _count_components(steps, dependencies)
    if len(steps) > 1 and connected_components > 1:
        warnings.append('Pipeline currently has {0} disconnected components.'.format(connected_components))

    ordered_kinds = [step.get('kind') for step in steps]
    if {'trigger.manual', 'data.market_bars', 'factor.momentum', 'factor.rank', 'research_chat'}.issubset(set(ordered_kinds)):
        pass
    elif any(kind in ordered_kinds for kind in ('data.market_bars', 'factor.momentum', 'factor.rank', 'research_chat')):
        warnings.append('Momentum-ranking drafts usually include trigger.manual, data.market_bars, factor.momentum, factor.rank, and research_chat.')

    suggestions = _build_recommendations(errors, warnings)
    return {
        'is_coherent': not errors and connected_components <= 1,
        'step_count': len(steps),
        'edge_count': edge_count,
        'errors': errors,
        'warnings': warnings,
        'recommended_next_actions': suggestions,
    }


def _collect_dependencies(steps: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    known_ids = {step.get('id') for step in steps}
    dependencies: Dict[str, Set[str]] = {step.get('id'): set() for step in steps}
    for step in steps:
        step_id = step.get('id')
        for downstream_id in step.get('next') or []:
            if downstream_id in dependencies:
                dependencies[downstream_id].add(step_id)
        for source_id in _extract_refs(step.get('config', {})):
            if source_id in known_ids:
                dependencies[step_id].add(source_id)
    return dependencies


def _count_edges(pipeline: Dict[str, Any]) -> int:
    return sum(len(step.get('next') or []) for step in pipeline.get('steps', []))


def _extract_refs(value: Any) -> Set[str]:
    refs: Set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            refs.update(_extract_refs(item))
        return refs
    if isinstance(value, list):
        for item in value:
            refs.update(_extract_refs(item))
        return refs
    if isinstance(value, str) and value.startswith('$'):
        refs.add(value[1:].split('[')[0].split('.')[0])
    return refs


def _unknown_reference_roots(value: Any, known_ids: Set[str]) -> Set[str]:
    return {ref for ref in _extract_refs(value) if ref not in known_ids}


def _count_components(steps: List[Dict[str, Any]], dependencies: Dict[str, Set[str]]) -> int:
    if not steps:
        return 0

    adjacency: Dict[str, Set[str]] = {step.get('id'): set() for step in steps}
    for step_id, parents in dependencies.items():
        for parent in parents:
            adjacency.setdefault(step_id, set()).add(parent)
            adjacency.setdefault(parent, set()).add(step_id)
    for step in steps:
        step_id = step.get('id')
        for child in step.get('next') or []:
            adjacency.setdefault(step_id, set()).add(child)
            adjacency.setdefault(child, set()).add(step_id)

    remaining = set(adjacency.keys())
    components = 0
    while remaining:
        start = remaining.pop()
        stack = [start]
        components += 1
        while stack:
            node = stack.pop()
            for neighbor in adjacency.get(node, set()):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return components


def _build_recommendations(errors: List[str], warnings: List[str]) -> List[str]:
    recommendations: List[str] = []
    if any('missing required fields' in item for item in errors):
        recommendations.append('Inspect the failing kind with get_details, then repair the config with update_step.')
    if any('references unknown step ids' in item for item in errors):
        recommendations.append('Add the missing upstream step first, or fix the reference string to an existing step id.')
    if any('multiple steps but no ordering edges' in item for item in errors):
        recommendations.append('Connect related steps with connect_steps so the plan has a clear execution order.')
    if any('disconnected' in item for item in warnings):
        recommendations.append('Connect or remove disconnected steps before exporting the pipeline.')
    if not recommendations:
        recommendations.append('The draft looks coherent enough to export.')
    return recommendations
