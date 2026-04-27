# Agent Eval/Dev Interview Scaffold

This repository is a starter scaffold for evaluating agent behavior around ambiguous coding, shell, and file-operation work.

The codebase has two layers:

- a YAML runtime that executes small evaluation pipelines
- a minimal planner/tool scaffold used to draft and revise task specs

The current target has two tracks:

- **T1:** multi-turn requirement clarification and spec strengthening for risky coding/bash/file-op tasks
- **T2:** planner-to-worker spec transmission, worker feedback, and one-round spec revision

## Planned Model Lineup

The current planned external model lineup for benchmark comparison is:

- `Claude Haiku 4.5`: lightweight strong international baseline
- `Qwen3-Coder-Next`: primary domestic coding/agent model
- `GLM-5`: strong domestic reference
- `Qwen3 32B dense`: weaker non-specialized control

Current expectation is to access these through Amazon Bedrock rather than direct provider APIs. Task-level model allocation for T1, T2, and judge roles is still intentionally left open.

## Repository Landmarks

- `TASKS.md`: interview requirements and expected workstreams
- `CANDIDATE_README.md`: candidate-oriented starting guide
- `tests/public/cases`: public YAML cases for the evaluation runtime
- `tests/run_tests.py`: lightweight regression runner
- `agent/catalog.py`: available eval-step metadata exposed to a planner
- `agent/tools.py`: generic draft-editing tools

## Project Shape

The runtime side lives under `engine`:

- DSL/spec parsing
- execution state tracking
- runtime registry
- small deterministic eval nodes

The planner side lives under `agent`:

- generic tool schemas
- step catalog/details
- a handwritten loop shell that can later be connected to an LLM client

## Running Locally

```bash
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python tests/run_tests.py
```

The scaffold is intentionally light. The first implementation milestone is to make the evaluation objects crisp before wiring in model calls or hidden grading.
