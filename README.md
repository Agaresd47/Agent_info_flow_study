# Quant Research Drafting Interview

`quant_react_interview` is a standalone take-home repo built around a small research-planning runtime.

The codebase has two distinct layers:

- a step executor that runs YAML research plans
- a handwritten LLM planner that assembles those plans through tool calls

The starter version is intentionally incomplete. Some behavior is real, some is fragile, and a few integrations are still placeholders on purpose.

## What This Repo Is For

This project is meant to evaluate how a candidate works across:

- handwritten LLM-agent control loops
- generic tool-call design
- runtime integration work
- code reading and incremental improvement in an unfamiliar repo

## Repository Landmarks

- [TASKS.md](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/TASKS.md): interview requirements
- [CANDIDATE_README.md](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/CANDIDATE_README.md): short candidate-oriented starting guide
- [test.py](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/test.py): manual planner-to-runtime smoke script
- [tests/run_tests.py](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/tests/run_tests.py): lightweight regression runner
- [examples/momentum_pipeline.yaml](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/examples/momentum_pipeline.yaml): example runtime plan

## Project Shape

The planner side lives under [agent](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/agent) and stays intentionally minimal:

- a handwritten loop
- a small generic tool surface
- step metadata used to help tool calling

The runtime side lives under [engine](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/engine):

- DSL/spec parsing
- execution state tracking
- runtime registry
- step implementations

## Running Locally

```
python -m venv venv
source venv/bin/activate
./venv/bin/python3 -m pip install --upgrade pip
./venv/bin/python3 -m pip install -r requirements.txt
```

Run commands from [quant_react_interview](/Users/wangshuo/Codes/nodie_interview/quant_react_interview):

```bash
python3 tests/run_tests.py
python3 test.py
```

If you want to exercise real API-backed behavior, make sure your environment variables for model access are configured before running `test.py`.
