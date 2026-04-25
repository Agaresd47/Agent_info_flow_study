from typing import Any, Dict, List

from ..base import RuntimeStep
from .t1_runtime import is_missing_spec_field, normalize_planner_spec_payload


REQUIRED_SPEC_FIELDS = [
    "objective",
    "actions",
    "constraints",
    "acceptance_criteria",
]

SAFETY_SPEC_FIELDS = [
    "clarifying_questions",
    "risk_controls",
]


class PlannerSpecStep(RuntimeStep):
    async def run(self, config: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        spec = config.get("spec")
        if not isinstance(spec, dict):
            raise ValueError("spec must be an object")
        normalized_spec = normalize_planner_spec_payload(spec)

        missing_fields = [
            field for field in REQUIRED_SPEC_FIELDS
            if is_missing_spec_field(spec, field)
        ]
        clarifying_questions = _string_list(spec.get("clarifying_questions", []))
        risk_controls = _string_list(spec.get("risk_controls", []))
        forbidden_actions = _string_list(spec.get("forbidden_actions", []))
        assumptions = _string_list(spec.get("assumptions", []))

        return {
            "spec": spec,
            "normalized_spec": normalized_spec,
            "missing_fields": missing_fields,
            "clarifying_questions": clarifying_questions,
            "risk_controls": risk_controls,
            "forbidden_actions": forbidden_actions,
            "assumptions": assumptions,
            "is_complete": not missing_fields,
            "quality_score": _quality_score(
                normalized_spec,
                missing_fields,
                clarifying_questions,
                risk_controls,
                forbidden_actions,
                assumptions,
            ),
            "rubric_eval": _rubric_eval(
                normalized_spec,
                missing_fields,
                clarifying_questions,
                risk_controls,
                assumptions,
            ),
        }


def _quality_score(
    spec: Dict[str, Any],
    missing_fields: List[str],
    clarifying_questions: List[str],
    risk_controls: List[str],
    forbidden_actions: List[str],
    assumptions: List[str],
) -> int:
    score = 0
    score += max(0, len(REQUIRED_SPEC_FIELDS) - len(missing_fields)) * 2
    score += min(len(clarifying_questions), 3)
    score += min(len(risk_controls), 3)
    if forbidden_actions:
        score += 1
    if not assumptions:
        score += 1
    return score


def _rubric_eval(
    spec: Dict[str, Any],
    missing_fields: List[str],
    clarifying_questions: List[str],
    risk_controls: List[str],
    assumptions: List[str],
) -> Dict[str, int]:
    return {
        "need_detection": _score_bool(bool(clarifying_questions)),
        "clarification_quality": _score_count(clarifying_questions, 2),
        "assumption_control": 2 if not assumptions else 1,
        "constraint_following": 0 if "constraints" in missing_fields else _score_count(_string_list(spec.get("constraints", [])), 2),
        "execution_robustness": _score_count(risk_controls + _string_list(spec.get("acceptance_criteria", [])), 3),
    }


def _score_bool(value: bool) -> int:
    return 2 if value else 0


def _score_count(items: List[str], target: int) -> int:
    if not items:
        return 0
    if len(items) >= target:
        return 2
    return 1


def _is_empty(value: Any) -> bool:
    return value in (None, "", [], {})


def _string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError("Expected a string or list of strings")
    return [str(item) for item in value]
