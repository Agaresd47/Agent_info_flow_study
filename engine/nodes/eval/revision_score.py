from typing import Any, Dict

from .planner_spec import REQUIRED_SPEC_FIELDS
from .t2_common import is_empty, string_list, worker_false_confidence
from ..base import RuntimeStep


class RevisionScoreStep(RuntimeStep):
    async def run(self, config: Dict[str, Any], runtime: Any) -> Dict[str, Any]:
        before = _review(config.get("before"))
        after = _review(config.get("after"))

        before_issues = int(before.get("blocking_issue_count", 0))
        after_issues = int(after.get("blocking_issue_count", 0))
        delta = before_issues - after_issues
        worker_before = _worker_rubric(before)
        worker_after = _worker_rubric(after)
        worker_before_total = sum(worker_before.values())
        worker_after_total = sum(worker_after.values())
        delta_worker_understanding = worker_after_total - worker_before_total
        planner_before = _planner_rubric(before, None)
        planner_after = _planner_rubric(
            after,
            {
                "delta_worker_understanding": delta_worker_understanding,
                "blocking_issue_delta": delta,
                "before_review": before,
            },
        )
        false_confident_reviews = sum(
            1
            for review in (before, after)
            if worker_false_confidence(review)
        )
        remaining_misalignments = _remaining_misalignments(after)

        return {
            "before_blocking_issues": before_issues,
            "after_blocking_issues": after_issues,
            "delta": delta,
            "improved": delta > 0,
            "ready_after_revision": after.get("status") == "ready",
            "worker_rubric_before": worker_before,
            "worker_rubric_after": worker_after,
            "worker_rubric_before_total": worker_before_total,
            "worker_rubric_after_total": worker_after_total,
            "planner_rubric_before": planner_before,
            "planner_rubric_after": planner_after,
            "planner_rubric_before_total": sum(planner_before.values()),
            "planner_rubric_after_total": sum(planner_after.values()),
            "delta_worker_understanding": delta_worker_understanding,
            "misalignment_persistence_rate": remaining_misalignments / 3,
            "false_confidence_rate": false_confident_reviews / 2,
        }


def _review(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("review input must be an object")
    return value


def _worker_rubric(review: Dict[str, Any]) -> Dict[str, int]:
    rubric = review.get("worker_rubric", {})
    if not isinstance(rubric, dict):
        return {}
    return {str(key): int(value) for key, value in rubric.items()}


def _planner_rubric(review: Dict[str, Any], revision_context: Dict[str, Any] | None) -> Dict[str, int]:
    spec = review.get("spec_snapshot", {})
    required_clarifications = string_list(review.get("required_clarifications", []))
    covered_clarifications = string_list(review.get("covered_clarifications", []))
    missing_fields = [
        field for field in REQUIRED_SPEC_FIELDS
        if is_empty(spec.get(field))
    ]
    spec_completeness = 2 if not missing_fields else 1 if len(missing_fields) <= 2 else 0
    file_targeting_quality = _score_ratio(
        len(covered_clarifications),
        len(required_clarifications),
    )

    actions = string_list(spec.get("actions", []))
    constraints = string_list(spec.get("constraints", []))
    delegation_precision = 2 if len(actions) >= 3 and constraints else 1 if actions else 0

    revision_gain = 0
    overcorrection_control = 2 if review.get("status") == "ready" else 1 if not review.get("missing_fields") else 0
    if revision_context is not None:
        revision_gain = _score_revision_gain(review, revision_context)
        overcorrection_control = _score_overcorrection(review, revision_context["before_review"])

    return {
        "spec_completeness": spec_completeness,
        "file_targeting_quality": file_targeting_quality,
        "delegation_precision": delegation_precision,
        "revision_gain": revision_gain,
        "overcorrection_control": overcorrection_control,
    }


def _score_revision_gain(review: Dict[str, Any], revision_context: Dict[str, Any]) -> int:
    delta_worker_understanding = int(revision_context.get("delta_worker_understanding", 0))
    blocking_issue_delta = int(revision_context.get("blocking_issue_delta", 0))
    if delta_worker_understanding > 0 and blocking_issue_delta > 0 and review.get("status") == "ready":
        return 2
    if delta_worker_understanding > 0 or blocking_issue_delta > 0:
        return 1
    return 0


def _score_overcorrection(review: Dict[str, Any], before_review: Dict[str, Any]) -> int:
    before_goal = _goal_tokens(str(before_review.get("understood_goal", "")))
    after_goal = _goal_tokens(str(review.get("understood_goal", "")))
    before_covered = string_list(before_review.get("covered_clarifications", []))
    after_covered = string_list(review.get("covered_clarifications", []))

    if not after_goal:
        return 0
    if before_goal and not (before_goal & after_goal):
        return 1
    if len(after_covered) < len(before_covered):
        return 1
    return 2


def _remaining_misalignments(review: Dict[str, Any]) -> int:
    count = 0
    if string_list(review.get("missing_clarifications", [])):
        count += 1
    if string_list(review.get("uncovered_risks", [])):
        count += 1
    if string_list(review.get("missing_fields", [])):
        count += 1
    return count


def _score_ratio(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 2
    if numerator >= denominator:
        return 2
    if numerator > 0:
        return 1
    return 0


def _goal_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in value.lower().replace(".", " ").replace(",", " ").split()
        if len(token) > 3
    }
    stopwords = {
        "missing",
        "details",
        "stay",
        "until",
        "clarified",
        "follow",
        "goal",
        "unclear",
    }
    return {token for token in tokens if token not in stopwords}
