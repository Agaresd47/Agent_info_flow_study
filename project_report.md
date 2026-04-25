# Project Notes

This repo has been re-scaffolded from a quant-research planning exercise into an agent eval/dev exercise.

The current shape is intentionally narrow:

- T1 focuses on clarification behavior for ambiguous and risky coding/bash/file-operation tasks.
- T2 focuses on planner-to-worker spec transmission and revision quality.
- The runtime is deterministic so public cases can run without API keys.
- Model integration is left as a later layer after the eval objects are stable.

## Current Runtime Nodes

- `eval.task`: records the original request, required clarifications, risk markers, and forbidden actions.
- `planner.spec`: wraps a planner-written spec and applies a shallow completeness score.
- `worker.review`: checks whether a worker would find the spec clear and safe enough.
- `revision.score`: compares before/after worker reviews.

## Next Engineering Targets

1. Add more T1 fixtures around delete/move/rename collisions.
2. Split clarification quality from execution readiness in the scoring model.
3. Add a hidden-case harness separate from `tests/public/cases`.
4. Decide whether the worker is deterministic, LLM-judged, or hybrid.
5. Reconnect `agent/react_loop.py` to an injected model client only after the case schemas settle.
