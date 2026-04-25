from typing import Any, Dict, List, Sequence


WORKER_PROMPT_VERSION = "worker_interpretation_v1"
WORKER_PROMPT_FIELDS = [
    "understood_goal",
    "constraints_to_follow",
    "information_still_missing",
    "first_3_concrete_actions",
]


def normalize_spec_payload(value: Any) -> Dict[str, Any]:
    spec = value.get("spec", value) if isinstance(value, dict) else {}
    if not isinstance(spec, dict):
        raise ValueError("spec must resolve to an object")
    return spec


def string_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, list):
        raise ValueError("Expected a string or list of strings")
    return [str(item) for item in value]


def is_empty(value: Any) -> bool:
    return value in (None, "", [], {})


def canonicalize_label(value: str) -> str:
    return " ".join(
        "".join(ch.lower() if ch.isalnum() else " " for ch in value).split()
    )


def mentions_any(haystack: Sequence[str], needle: str) -> bool:
    normalized = canonicalize_label(needle)
    return any(normalized in canonicalize_label(item) for item in haystack)


def unique_strings(items: Sequence[str]) -> List[str]:
    seen = set()
    output: List[str] = []
    for item in items:
        normalized = canonicalize_label(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(item)
    return output


def score_from_ratio(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 2
    ratio = numerator / denominator
    if ratio >= 1.0:
        return 2
    if ratio > 0:
        return 1
    return 0


def build_worker_interpretation(
    spec: Dict[str, Any],
    required_clarifications: Sequence[str],
) -> Dict[str, Any]:
    questions = string_list(spec.get("clarifying_questions", []))
    covered_missing_info = [
        item for item in required_clarifications if mentions_any(questions, item)
    ]
    actions = string_list(spec.get("actions", []))
    first_actions = actions[:3]
    if not first_actions:
        first_actions = ["Clarify the task before taking action."]

    constraints = unique_strings(
        string_list(spec.get("constraints", [])) + string_list(spec.get("risk_controls", []))
    )

    understood_goal = str(spec.get("objective") or "Goal is unclear.")
    if covered_missing_info:
        understood_goal = "{0} Missing details stay unresolved until clarified.".format(
            understood_goal
        )

    return {
        "understood_goal": understood_goal,
        "constraints_to_follow": constraints,
        "information_still_missing": covered_missing_info,
        "first_3_concrete_actions": first_actions,
    }


def worker_false_confidence(review: Dict[str, Any]) -> bool:
    required_count = len(string_list(review.get("required_clarifications", [])))
    understood_missing = len(string_list(review.get("information_still_missing", [])))
    return required_count > 0 and understood_missing == 0
