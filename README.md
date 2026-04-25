# Agent Eval/Dev Interview Scaffold

This repository is a starter scaffold for evaluating agent behavior around ambiguous coding, shell, and file-operation work.

The codebase has two layers:

- a YAML runtime that executes small evaluation pipelines
- a minimal planner/tool scaffold used to draft and revise task specs

The current target has two tracks:

- **T1:** multi-turn requirement clarification and spec strengthening for risky coding/bash/file-op tasks
- **T2:** planner-to-worker spec transmission, worker feedback, and one-round spec revision

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
