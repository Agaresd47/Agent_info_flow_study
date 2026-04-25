from typing import Any, Dict, List

from .planner_spec import REQUIRED_SPEC_FIELDS
from .t2_common import (
    WORKER_PROMPT_FIELDS,
    WORKER_PROMPT_VERSION,
    build_worker_interpretation,
    is_empty,
    mentions_any,
    normalize_spec_payload,
    score_from_ratio,
    string_list,
    worker_false_confidence,
)
from ..base import RuntimeStep


class WorkerReviewStep(RuntimeStep):
    async def run(self, config: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        spec = normalize_spec_payload(config.get("spec"))
        required_clarifications = string_list(config.get("required_clarifications", []))
        risk_markers = string_list(config.get("risk_markers", []))

        missing_fields = [field for field in REQUIRED_SPEC_FIELDS if is_empty(spec.get(field))]
        asked_questions = string_list(spec.get("clarifying_questions", []))
        covered_clarifications = [
            item for item in required_clarifications
            if mentions_any(asked_questions, item)
        ]
        missing_clarifications = [
            item for item in required_clarifications
            if item not in covered_clarifications
        ]

        risk_controls = string_list(spec.get("risk_controls", []))
        uncovered_risks = [
            item for item in risk_markers
            if not mentions_any(risk_controls, item)
        ]

        blocking_issues = missing_fields + missing_clarifications + uncovered_risks
        interpretation = build_worker_interpretation(spec, required_clarifications)
        worker_rubric = _worker_rubric(
            missing_fields=missing_fields,
            covered_clarifications=covered_clarifications,
            required_clarifications=required_clarifications,
            uncovered_risks=uncovered_risks,
            interpretation=interpretation,
        )
        return {
            "status": "ready" if not blocking_issues else "needs_revision",
            "prompt_version": WORKER_PROMPT_VERSION,
            "worker_prompt_fields": list(WORKER_PROMPT_FIELDS),
            "spec_snapshot": spec,
            "required_clarifications": required_clarifications,
            "missing_fields": missing_fields,
            "covered_clarifications": covered_clarifications,
            "missing_clarifications": missing_clarifications,
            "uncovered_risks": uncovered_risks,
            "blocking_issue_count": len(blocking_issues),
            "worker_interpretation": interpretation,
            "understood_goal": interpretation["understood_goal"],
            "constraints_to_follow": interpretation["constraints_to_follow"],
            "information_still_missing": interpretation["information_still_missing"],
            "first_3_concrete_actions": interpretation["first_3_concrete_actions"],
            "worker_rubric": worker_rubric,
            "worker_rubric_total": sum(worker_rubric.values()),
            "false_confidence": worker_false_confidence(
                {
                    "required_clarifications": required_clarifications,
                    "information_still_missing": interpretation["information_still_missing"],
                }
            ),
            "feedback": _feedback(missing_fields, missing_clarifications, uncovered_risks),
        }


def _worker_rubric(
    missing_fields: List[str],
    covered_clarifications: List[str],
    required_clarifications: List[str],
    uncovered_risks: List[str],
    interpretation: Dict[str, Any],
) -> Dict[str, int]:
    action_count = len(string_list(interpretation.get("first_3_concrete_actions", [])))
    all_constraints = string_list(interpretation.get("constraints_to_follow", []))
    missing_info = string_list(interpretation.get("information_still_missing", []))

    goal_understanding = 2 if not missing_fields and interpretation.get("understood_goal") else 1
    if not interpretation.get("understood_goal"):
        goal_understanding = 0

    constraint_capture = 2 if all_constraints and not uncovered_risks else 1 if all_constraints else 0

    missing_info_awareness = score_from_ratio(
        len(covered_clarifications),
        len(required_clarifications),
    )

    assumption_control = 2
    if required_clarifications and len(missing_info) < len(required_clarifications):
        assumption_control = 1
    if required_clarifications and not missing_info:
        assumption_control = 0

    actionability = 2 if action_count >= 3 else 1 if action_count >= 1 else 0

    return {
        "goal_understanding": goal_understanding,
        "constraint_capture": constraint_capture,
        "missing_info_awareness": missing_info_awareness,
        "assumption_control": assumption_control,
        "actionability": actionability,
    }


def _feedback(
    missing_fields: List[str],
    missing_clarifications: List[str],
    uncovered_risks: List[str],
) -> List[str]:
    feedback: List[str] = []
    for field in missing_fields:
        feedback.append("Add spec field: {0}".format(field))
    for item in missing_clarifications:
        feedback.append("Clarify: {0}".format(item))
    for item in uncovered_risks:
        feedback.append("Add risk control for: {0}".format(item))
    return feedback
