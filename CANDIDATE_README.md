# Candidate Guide

This repo models a small quant-research drafting system.

You will find:

- a YAML-based execution runtime
- a handwritten LLM planning loop
- a minimal generic tool layer
- runtime steps that are intentionally unfinished

## Start Here

Read these in order:

1. [TASKS.md](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/TASKS.md)
2. [examples/momentum_pipeline.yaml](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/examples/momentum_pipeline.yaml)
3. [test.py](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/test.py)
4. [tests/public/cases](/Users/wangshuo/Codes/nodie_interview/quant_react_interview/tests/public/cases)

## Useful Commands

Run everything from [quant_react_interview](/Users/wangshuo/Codes/nodie_interview/quant_react_interview):

```bash
python3 tests/run_tests.py
python3 test.py
```

## What To Expect

The starter repository is not supposed to be fully polished.

Some parts are deliberately weak so you can improve them:

- the planner loop needs better recovery behavior
- the generic tool surface needs better guidance for config-heavy tool calls
- some runtime nodes are still mocks and should be replaced with real integrations
