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
    config_schema = {
        "type": "object",
        "description": "Configuration for the step. Use only the fields that match the selected step kind.",
        "properties": {
            "universe": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Universe list for trigger.manual output.",
            },
            "symbols": {
                "description": "List of BaoStock symbols or a reference like '$trigger_id[\"universe\"]'.",
                "anyOf": [
                    {"type": "array", "items": {"type": "string"}},
                    {"type": "string"}
                ]
            },
            "lookback_days": {"type": "integer", "description": "Number of calendar days to request from BaoStock."},
            "bars": {"type": "string", "description": "Reference to grouped bar output, e.g. '$data_market_bars'."},
            "window": {"type": "integer", "description": "Lookback window used by factor.momentum."},
            "values": {"type": "string", "description": "Reference to a score dictionary, e.g. '$factor_momentum[\"scores\"]'."},
            "descending": {"type": "boolean", "description": "Sort highest-to-lowest when true; default true."},
            "prompt": {"type": "string", "description": "Prompt text for research_chat, often containing references like '$factor_rank[\"ordered\"]'."},
            "model": {"type": "string", "description": "Optional model override for research_chat."},
        }
    }
    return [
        _function_spec(
            name="add_step",
            description=(
                "Create a draft step inside the current research plan. "
                "Provide the config fields required for the selected kind."
            ),
            properties={
                "kind": {"type": "string"},
                "step_id": {"type": "string"},
                "config": config_schema,
            },
            required=["kind", "config"],
        ),
        _function_spec(
            name="update_step",
            description="Modify a draft step's config and immediately re-evaluate that step.",
            properties={
                "step_id": {"type": "string"},
                "config": config_schema,
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
            description=(
                "Inspect the available research step kinds at a high level. "
                "Use this to discover available building blocks and their main outputs."
            ),
            properties={},
            required=[],
        ),
        _function_spec(
            name="get_details",
            description=(
                "Inspect a specific step kind in detail, including its required fields, "
                "config schema, output fields, reference examples, and usage notes. "
                "Use this before add_step or update_step to confirm the expected configuration shape."
            ),
            properties={"kind": {"type": "string"}},
            required=["kind"],
        ),
        _function_spec(
            name="get_pipeline",
            description=(
                "Export the current draft plan. Only call this when the plan is fully "
                "connected and all steps have executed successfully."
            ),
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
    result["current_draft_summary"] = builder.get_summary()
    return result


async def _update_step(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    step_id = payload["step_id"]
    builder.update_step(step_id, payload.get("config", {}))
    result = await _run_step(builder, step_id)
    result["action"] = "update_step"
    result["current_draft_summary"] = builder.get_summary()
    return result


async def _connect_steps(builder: PipelineBuilder, payload: Dict[str, Any]) -> Dict[str, Any]:
    builder.connect_steps(payload["source_id"], payload["target_id"])
    return {
        "success": True,
        "action": "connect_steps",
        "source_id": payload["source_id"],
        "target_id": payload["target_id"],
        "current_draft_summary": builder.get_summary(),
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

    # Verify all steps have successfully executed
    failures = []
    for step in pipeline["steps"]:
        sid = step["id"]
        status = builder.step_execution_results.get(sid, {})
        if not status.get("success"):
            error_msg = status.get("error", "Step has not been successfully executed yet.")
            failures.append(f"Step '{sid}' ({step['kind']}): {error_msg}")

    if failures:
        return {
            "success": False,
            "action": "get_pipeline",
            "error": "Pipeline export is blocked until every step executes successfully.",
            "failures": failures,
            "pipeline": pipeline,
        }

    return {"success": True, "action": "get_pipeline", "pipeline": pipeline}


async def _run_step(builder: PipelineBuilder, step_id: str) -> Dict[str, Any]:
    try:
        output = await builder.execute_step(step_id)
    except Exception as exc:
        return {"success": False, "step_id": step_id, "error": str(exc), "stage": "execution"}
    return {"success": True, "step_id": step_id, "output": output, "stage": "execution"}
