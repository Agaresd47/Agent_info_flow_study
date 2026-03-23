from typing import Any, Awaitable, Callable, Dict, List, Optional

from ..engine.core.builder import PipelineBuilder
from .catalog import get_catalog as catalog_list
from .catalog import get_details as catalog_details

ToolHandler = Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]

_active_builder: Optional[PipelineBuilder] = None


def bind_builder(builder: PipelineBuilder) -> None:
    global _active_builder
    _active_builder = builder


def get_tool_specs() -> List[Dict[str, Any]]:
    object_schema = {"type": "object"}
    return [
        _function_spec(
            name="add_step",
            description=(
                "Create a draft step inside the current research plan. "
                "If the config shape is unclear, inspect the step kind first."
            ),
            properties={
                "kind": {"type": "string"},
                "step_id": {"type": "string"},
                "config": object_schema,
            },
            required=["kind", "config"],
        ),
        _function_spec(
            name="update_step",
            description="Modify a draft step's config and immediately re-evaluate that step.",
            properties={
                "step_id": {"type": "string"},
                "config": object_schema,
            },
            required=["step_id", "config"],
        ),
        _function_spec(
            name="connect_steps",
            description="Declare that one step should run before another in the draft plan.",
            properties={
                "source_id": {"type": "string"},
                "target_id": {"type": "string"},
            },
            required=["source_id", "target_id"],
        ),
        _function_spec(
            name="get_catalog",
            description="Inspect the available step kinds at a high level.",
            properties={},
            required=[],
        ),
        _function_spec(
            name="get_details",
            description="Inspect one step kind in detail, including example config and notes.",
            properties={"kind": {"type": "string"}},
            required=["kind"],
        ),
        _function_spec(
            name="get_pipeline",
            description="Export the current draft plan when it is coherent enough to run.",
            properties={},
            required=[],
        ),
    ]


async def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if _active_builder is None:
        return {"success": False, "error": "Builder not bound", "stage": "tooling"}

    handlers = _tool_handlers(_active_builder)
    if name not in handlers:
        return {"success": False, "error": "Unknown tool: {0}".format(name)}

    try:
        return await handlers[name](arguments)
    except Exception as exc:
        return {"success": False, "error": str(exc), "stage": "tooling"}


def _function_spec(
    name: str,
    description: str,
    properties: Dict[str, Any],
    required: List[str],
) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def _tool_handlers(builder: PipelineBuilder) -> Dict[str, ToolHandler]:
    return {
        "add_step": lambda payload: _add_step(builder, payload),
        "update_step": lambda payload: _update_step(builder, payload),
        "connect_steps": lambda payload: _connect_steps(builder, payload),
        "get_catalog": lambda payload: _get_catalog(payload),
        "get_details": lambda payload: _get_details(payload),
        "get_pipeline": lambda payload: _get_pipeline(builder, payload),
    }


async def _add_step(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    created_id = builder.add_step(
        kind=payload["kind"],
        config=payload.get("config", {}),
        step_id=payload.get("step_id"),
    )
    result = await _run_step(builder, created_id)
    result["action"] = "add_step"
    return result


async def _update_step(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    step_id = payload["step_id"]
    builder.update_step(step_id, payload.get("config", {}))
    result = await _run_step(builder, step_id)
    result["action"] = "update_step"
    return result


async def _connect_steps(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    builder.connect_steps(payload["source_id"], payload["target_id"])
    return {
        "success": True,
        "action": "connect_steps",
        "source_id": payload["source_id"],
        "target_id": payload["target_id"],
    }


async def _get_catalog(_: Dict[str, Any]) -> Dict[str, Any]:
    return {"success": True, "action": "get_catalog", "catalog": catalog_list()}


async def _get_details(payload: Dict[str, Any]) -> Dict[str, Any]:
    details = catalog_details(payload["kind"])
    if "error" in details:
        return {"success": False, "action": "get_details", "error": details["error"]}
    return {"success": True, "action": "get_details", "details": details}


async def _get_pipeline(builder: PipelineBuilder, _: Dict[str, Any]) -> Dict[str, Any]:
    pipeline = builder.get_pipeline()
    if not pipeline["steps"]:
        return {
            "success": False,
            "action": "get_pipeline",
            "error": "Pipeline is empty",
            "pipeline": pipeline,
        }
    return {"success": True, "action": "get_pipeline", "pipeline": pipeline}


async def _run_step(builder: PipelineBuilder, step_id: str) -> Dict[str, Any]:
    try:
        output = await builder.execute_step(step_id)
    except Exception as exc:
        return {"success": False, "step_id": step_id, "error": str(exc), "stage": "execution"}
    return {"success": True, "step_id": step_id, "output": output, "stage": "execution"}
