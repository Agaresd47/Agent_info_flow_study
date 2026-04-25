from typing import Any, Dict, List, Sequence


def build_slot_match_prompt(question: str, missing_slots: Sequence[Dict[str, Any]]) -> str:
    allowed_slots = [str(slot.get("slot_name") or "slot") for slot in missing_slots]
    return (
        "Classify the assistant question into exactly one slot_name from the allowed list, or no_match.\n"
        "Allowed slot_names: {slots}\n"
        "Question: {question}\n"
        "Return only the slot_name or no_match."
    ).format(slots=", ".join(allowed_slots), question=question)


def build_slot_classification_prompt(allowed_slots: Sequence[str], question: str) -> str:
    return (
        "Classify the assistant question into exactly one slot_name from the allowed list, or no_match.\n"
        "Allowed slot_names: {slots}\n"
        "Question: {question}\n"
        "Return only the slot_name or no_match."
    ).format(slots=", ".join(str(slot) for slot in allowed_slots), question=question)


def match_slot(question: str, missing_slots: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    normalized_question = _tokenize(question)
    best_slot = None
    best_score = 0.0
    for slot in missing_slots:
        candidates = [str(slot.get("slot_name") or ""), str(slot.get("description") or "")]
        score = max(_overlap_score(normalized_question, _tokenize(candidate)) for candidate in candidates)
        if score > best_score:
            best_slot = slot
            best_score = score
    if best_slot is None or best_score == 0:
        return {
            "question": question,
            "slot_name": "no_match",
            "matched": False,
            "match_score": 0.0,
        }
    return {
        "question": question,
        "slot_name": str(best_slot.get("slot_name") or "no_match"),
        "matched": True,
        "match_score": round(best_score, 3),
    }


def parse_slot_name(raw_output: str, allowed_slots: List[str]) -> str:
    normalized = raw_output.strip().strip("`'\" ").split()[0] if raw_output.strip() else ""
    for slot_name in allowed_slots:
        if normalized == slot_name or slot_name in raw_output:
            return slot_name
    if "no_match" in raw_output:
        return "no_match"
    return "no_match"


def _tokenize(text: str) -> List[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in str(text))
    return [token for token in cleaned.split() if token]


def _overlap_score(left: Sequence[str], right: Sequence[str]) -> float:
    if not left or not right:
        return 0.0
    left_tokens = set(left)
    right_tokens = set(right)
    overlap = left_tokens & right_tokens
    if not overlap:
        return 0.0
    return len(overlap) / max(len(right_tokens), 1)
