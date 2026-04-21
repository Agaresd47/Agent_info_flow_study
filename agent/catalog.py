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
        output_fields: List[str],
        reference_examples: List[str],
        notes: List[str],
    ) -> None:
        self.kind = kind
        self.purpose = purpose
        self.required_fields = required_fields
        self.sample = sample
        self.output_fields = output_fields
        self.reference_examples = reference_examples
        self.notes = notes

    def summary(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "purpose": self.purpose,
            "required_fields": list(self.required_fields),
            "example_config": dict(self.sample),
            "output_fields": list(self.output_fields),
        }

    def details(self) -> Dict[str, Any]:
        payload = self.summary()
        payload["reference_examples"] = list(self.reference_examples)
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
        output_fields=["universe"],
        reference_examples=["$trigger_id['universe']"],
        notes=[
            "Usually the first step in a draft.",
            "Its output can be referenced later with $step_id['field'].",
        ],
    ),
    _StepDescriptor(
        kind="data.market_bars",
        purpose="Fetch grouped daily bar series for one or more symbols (BaoStock backend).",
        required_fields=["symbols"],
        sample={"symbols": ["sh.600000", "sz.000001"], "lookback_days": 30},
        output_fields=["<symbol> -> list[bar]"],
        reference_examples=["$data_market_bars", "$data_market_bars['sh.600000']"],
        notes=[
            "Symbols should ideally include exchange prefix (sh. or sz.).",
            "Return value is a symbol -> list[bars] mapping.",
            "Each bar includes: date, open, high, low, close, volume.",
        ],
    ),
    _StepDescriptor(
        kind="factor.momentum",
        purpose="Compute a momentum score map from grouped bars.",
        required_fields=["bars"],
        sample={"bars": "$data_market_bars", "window": 3},
        output_fields=["scores", "coverage", "window"],
        reference_examples=["$factor_momentum['scores']", "$factor_momentum['coverage']"],
        notes=[
            "The node expects grouped bars (mapping of symbol to list of candles).",
            "Downstream rank steps usually consume the 'scores' field.",
        ],
    ),
    _StepDescriptor(
        kind="factor.rank",
        purpose="Order symbols using a score mapping.",
        required_fields=["values"],
        sample={"values": "$factor_momentum['scores']", "descending": True},
        output_fields=["ordered", "top"],
        reference_examples=["$factor_rank['ordered']", "$factor_rank['top']"],
        notes=[
            "Descending true means highest score first.",
            "Returns 'ordered' (list of rows) and 'top' (list of symbols).",
        ],
    ),
    _StepDescriptor(
        kind="research_chat",
        purpose="Generate a natural-language note using an LLM.",
        required_fields=["prompt"],
        sample={"prompt": "Analyze these ranked symbols: $factor_rank['ordered']"},
        output_fields=["content", "model", "status"],
        reference_examples=["$research_chat['content']"],
        notes=[
            "Uses a chat-completion model to synthesize insights.",
            "Always include upstream step references like $step_id['field'] in the prompt.",
        ],
    ),
]
