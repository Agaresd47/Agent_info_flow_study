# Candidate Guide

This repo models a small agent-evaluation system.

You will find:

- a YAML-based evaluation runtime
- deterministic nodes for spec review and revision scoring
- a small generic tool layer
- intentionally incomplete planner/worker workflows

## Start Here

Read these in order:

1. `TASKS.md`
2. `tests/public/cases`
3. `agent/catalog.py`
4. `agent/tools.py`
5. `tests/run_tests.py`

## Useful Commands

Run everything from the repository root:

```bash
python tests/run_tests.py
```

## What To Expect

The starter repository is not supposed to be fully polished.

Some parts are deliberately light so you can improve them:

- the T1 clarification rubric is only rule-based
- the T2 worker-review schema is minimal
- hidden-case design is not implemented yet
- the planner loop is a shell, not a full production agent
