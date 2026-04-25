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
        "description": "Configuration for the eval step. Use only fields that match the selected kind.",
        "properties": {
            "request": {"type": "string", "description": "Original ambiguous user request for eval.task."},
            "original_user_request": {"type": "string", "description": "Canonical T1 original user request; request is still accepted for legacy cases."},
            "task_id": {"type": "string", "description": "Stable task identifier for run records."},
            "scenario": {"type": "string", "description": "Short scenario label such as file_cleanup or planner_worker."},
            "expected_clarifications": {"type": "array", "items": {"type": "string"}},
            "missing_slots": {
                "type": "array",
                "description": "Explicit T1 missing slots for deterministic slot matching.",
                "items": {
                    "type": "object",
                    "properties": {
                        "slot_name": {"type": "string"},
                        "importance": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
            "user_reply_if_asked": {
                "type": "object",
                "description": "Map from slot_name to simulator reply. The simulator must not invent values outside this map.",
            },
            "environment_context": {
                "type": "object",
                "description": "OS/shell/workdir/tool policy for T1.",
                "properties": {
                    "os_type": {"type": "string"},
                    "shell": {"type": "string"},
                    "working_directory": {"type": "string"},
                    "tools_allowed": {"type": "array", "items": {"type": "string"}},
                    "tools_forbidden": {"type": "array", "items": {"type": "string"}},
                },
            },
            "condition": {
                "type": "object",
                "description": "T1 condition such as {'spec_level':'A0_interactive','policy':'default','knowledge_level':'none'}.",
            },
            "model_id": {"type": "string", "description": "Configured or mock model id for run record metadata."},
            "model_tier": {"type": "string", "description": "Model tier label such as mock, mid, planner, worker, or judge."},
            "seed": {"type": "integer", "description": "Deterministic seed recorded in the run."},
            "risk_markers": {"type": "array", "items": {"type": "string"}},
            "risk_flags": {"type": "array", "items": {"type": "string"}},
            "must_not_do": {"type": "array", "items": {"type": "string"}},
            "structured_spec": {"type": "object", "description": "T1 structured spec with goal/scope/constraints/safety_requirements."},
            "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
            "oracle_test": {"type": "object", "description": "Refs for outcome, robustness, and safety checks."},
            "clarification_protocol": {"type": "object", "description": "Slot retrieval protocol; max rounds defaults to 2."},
            "spec": {
                "description": "Planner spec object, or a reference to one like '$spec_v1'.",
                "anyOf": [{"type": "object"}, {"type": "string"}],
            },
            "required_clarifications": {
                "description": "Clarifications the worker should expect, or a reference.",
                "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "string"}],
            },
            "before": {"description": "Reference to a worker.review output before revision.", "type": "string"},
            "after": {"description": "Reference to a worker.review output after revision.", "type": "string"},
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
