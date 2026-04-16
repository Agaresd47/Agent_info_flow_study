from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class _StepDescriptor:
    kind: str
    purpose: str
    required_fields: List[str]
    config_fields: Dict[str, Dict[str, Any]]
    sample: Dict[str, Any]
    produces: Dict[str, Any]
    reference_examples: List[str]
    notes: List[str]
    typical_upstream: List[str]
    typical_downstream: List[str]

    def summary(self) -> Dict[str, Any]:
        return {
            'kind': self.kind,
            'purpose': self.purpose,
            'required_fields': list(self.required_fields),
            'config_fields': dict(self.config_fields),
            'example_config': dict(self.sample),
            'produces': dict(self.produces),
        }

    def details(self) -> Dict[str, Any]:
        payload = self.summary()
        payload['reference_examples'] = list(self.reference_examples)
        payload['typical_upstream'] = list(self.typical_upstream)
        payload['typical_downstream'] = list(self.typical_downstream)
        payload['notes'] = list(self.notes)
        return payload


def supported_kinds() -> List[str]:
    return sorted(descriptor.kind for descriptor in _DESCRIPTORS)


def get_catalog() -> List[Dict[str, Any]]:
    return [descriptor.summary() for descriptor in _DESCRIPTORS]


def get_details(kind: str) -> Dict[str, Any]:
    descriptor = _by_kind().get(kind)
    if descriptor is None:
        return {'error': 'Unknown kind: {0}'.format(kind)}
    return descriptor.details()


def get_required_fields(kind: str) -> List[str]:
    descriptor = _by_kind().get(kind)
    return list(descriptor.required_fields) if descriptor is not None else []


def get_descriptor(kind: str) -> Optional[Dict[str, Any]]:
    descriptor = _by_kind().get(kind)
    return descriptor.details() if descriptor is not None else None


def _by_kind() -> Dict[str, _StepDescriptor]:
    return {descriptor.kind: descriptor for descriptor in _DESCRIPTORS}


_DESCRIPTORS = [
    _StepDescriptor(
        kind='trigger.manual',
        purpose='Seed the draft with initial input values such as the target universe.',
        required_fields=[],
        config_fields={
            'universe': {
                'type': 'array[string]',
                'required': False,
                'description': 'List of symbols or identifiers used later in the plan.',
            },
        },
        sample={'universe': ['AAPL', 'MSFT', 'NVDA']},
        produces={'universe': ['AAPL', 'MSFT', 'NVDA']},
        reference_examples=["$trigger['universe']"],
        notes=[
            'Usually the first step in a draft.',
            'Use short stable ids like trigger, bars, momentum, rank, chat.',
        ],
        typical_upstream=[],
        typical_downstream=['data.market_bars'],
    ),
    _StepDescriptor(
        kind='data.market_bars',
        purpose='Fetch grouped daily close bars for one or more symbols.',
        required_fields=['symbols'],
        config_fields={
            'symbols': {
                'type': 'array[string] | reference',
                'required': True,
                'description': "List of symbols, often from $trigger['universe'].",
            },
            'lookback_days': {
                'type': 'integer',
                'required': False,
                'description': 'How many most recent daily bars to keep per symbol.',
                'default': 5,
            },
        },
        sample={'symbols': "$trigger['universe']", 'lookback_days': 5},
        produces={'AAPL': [{'date': '2025-01-05', 'close': 110.0}]},
        reference_examples=['$bars'],
        notes=[
            'This step returns a plain symbol -> bars mapping, not a nested object.',
            'The downstream momentum step usually consumes the whole output via $bars.',
        ],
        typical_upstream=['trigger.manual'],
        typical_downstream=['factor.momentum'],
    ),
    _StepDescriptor(
        kind='factor.momentum',
        purpose='Compute a momentum score map from grouped bars.',
        required_fields=['bars'],
        config_fields={
            'bars': {
                'type': 'reference | object',
                'required': True,
                'description': "Grouped bars, usually the full output of data.market_bars via $bars.",
            },
            'window': {
                'type': 'integer',
                'required': False,
                'description': 'Trailing window used to compare the first and last close.',
                'default': 3,
            },
        },
        sample={'bars': '$bars', 'window': 3},
        produces={'scores': {'AAPL': 0.047619}, 'coverage': 1.0, 'window': 3},
        reference_examples=["$momentum['scores']"],
        notes=[
            'The node expects grouped bars, not a single list of candles.',
            "The rank step normally consumes momentum scores via $momentum['scores']",
        ],
        typical_upstream=['data.market_bars'],
        typical_downstream=['factor.rank'],
    ),
    _StepDescriptor(
        kind='factor.rank',
        purpose='Order symbols using a score mapping.',
        required_fields=['values'],
        config_fields={
            'values': {
                'type': 'reference | object',
                'required': True,
                'description': "Score map, usually from $momentum['scores'].",
            },
            'descending': {
                'type': 'boolean',
                'required': False,
                'description': 'Set true to rank higher scores first.',
                'default': True,
            },
        },
        sample={'values': "$momentum['scores']", 'descending': True},
        produces={'ordered': [{'symbol': 'AAPL', 'score': 0.047619, 'rank': 1}], 'top': ['AAPL']},
        reference_examples=["$rank['ordered']", "$rank['top']"],
        notes=[
            'Descending true means highest score first.',
            "The research_chat prompt usually references $rank['ordered'] directly.",
        ],
        typical_upstream=['factor.momentum'],
        typical_downstream=['research_chat', 'output.report'],
    ),
    _StepDescriptor(
        kind='research_chat',
        purpose='Generate a natural-language explanation of the research output.',
        required_fields=['prompt'],
        config_fields={
            'prompt': {
                'type': 'string',
                'required': True,
                'description': 'A direct explanation request that includes upstream references inline.',
            },
            'model': {
                'type': 'string',
                'required': False,
                'description': 'Optional override for the chat model.',
            },
            'instructions': {
                'type': 'string',
                'required': False,
                'description': 'Optional system guidance for tone or scope.',
            },
        },
        sample={'prompt': "Explain this momentum ranking: $rank['ordered']"},
        produces={'content': 'Momentum is strongest in NVDA because ...', 'model': 'gpt-4o-mini'},
        reference_examples=['$chat', "$chat['content']"],
        notes=[
            'Keep the prompt explicit about which upstream result should be described.',
            'This step should usually appear near the end of the chain.',
        ],
        typical_upstream=['factor.rank'],
        typical_downstream=['output.report'],
    ),
    _StepDescriptor(
        kind='output.report',
        purpose='Collect one or more finished sections into a report-like payload.',
        required_fields=[],
        config_fields={
            'sections': {
                'type': 'array',
                'required': False,
                'description': 'Ordered report sections, often text or referenced outputs.',
            },
        },
        sample={'sections': ["$chat['content']"]},
        produces={'sections': ['...']},
        reference_examples=['$report'],
        notes=[
            'Optional final packaging step.',
            'Do not add it unless you need a report wrapper around earlier outputs.',
        ],
        typical_upstream=['research_chat', 'factor.rank'],
        typical_downstream=[],
    ),
]
