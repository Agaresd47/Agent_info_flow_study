from typing import Any, Dict, List


def get_catalog() -> List[Dict[str, Any]]:
    return [descriptor.summary() for descriptor in _DESCRIPTORS]


def get_details(kind: str) -> Dict[str, Any]:
    descriptor = _by_kind().get(kind)
    if descriptor is None:
        return {"error": "Unknown kind: {0}".format(kind)}
    return descriptor.details()


class _StepDescriptor:
    def __init__(
        self,
        kind: str,
        purpose: str,
        required_fields: List[str],
        sample: Dict[str, Any],
        notes: List[str],
    ) -> None:
        self.kind = kind
        self.purpose = purpose
        self.required_fields = required_fields
        self.sample = sample
        self.notes = notes

    def summary(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "purpose": self.purpose,
            "required_fields": list(self.required_fields),
            "example_config": dict(self.sample),
        }

    def details(self) -> Dict[str, Any]:
        payload = self.summary()
        payload["notes"] = list(self.notes)
        return payload


def _by_kind() -> Dict[str, _StepDescriptor]:
    return {descriptor.kind: descriptor for descriptor in _DESCRIPTORS}


_DESCRIPTORS = [
    _StepDescriptor(
        kind="trigger.manual",
        purpose="Seed the draft with initial input values.",
        required_fields=[],
        sample={"universe": ["AAPL", "MSFT", "NVDA"]},
        notes=[
            "Usually the first step in a draft.",
            "Its output can be referenced later with $step_id['field'].",
        ],
    ),
    _StepDescriptor(
        kind="data.market_bars",
        purpose="Fetch grouped daily bar series for one or more symbols.",
        required_fields=["symbols"],
        sample={"symbols": "$trigger_manual['universe']", "lookback_days": 5},
        notes=[
            "The implementation is intentionally a mock before the interview task is completed.",
            "Return value should be a symbol -> bars mapping.",
        ],
    ),
    _StepDescriptor(
        kind="factor.momentum",
        purpose="Compute a momentum score map from grouped bars.",
        required_fields=["bars"],
        sample={"bars": "$data_market_bars", "window": 3},
        notes=[
            "The node expects grouped bars, not a single list of candles.",
            "Downstream rank steps usually consume the scores field.",
        ],
    ),
    _StepDescriptor(
        kind="factor.rank",
        purpose="Order symbols using a score mapping.",
        required_fields=["values"],
        sample={"values": "$factor_momentum['scores']", "descending": True},
        notes=[
            "Descending true means highest score first.",
            "The node returns ordered rows and a top-symbol list.",
        ],
    ),
    _StepDescriptor(
        kind="research_chat",
        purpose="Generate a natural-language note about the research output.",
        required_fields=["prompt"],
        sample={"prompt": "Explain this momentum ranking: $factor_rank['ordered']"},
        notes=[
            "This node is also a mock in the starter repo.",
            "Keep the prompt explicit about which upstream result should be described.",
        ],
    ),
]
