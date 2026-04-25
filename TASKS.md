# Agent Eval/Dev Exercise

You have **2 hours** for this exercise.

## Project Snapshot

This repository contains a small evaluation scaffold for agent development. It is designed around two related tasks:

- **T1:** handling ambiguous, risky coding/bash/file-operation requests through clarification and spec strengthening
- **T2:** transmitting planner-written specs to a worker, collecting worker feedback, and revising the spec

The starter code is deliberately incomplete. Some parts are deterministic, some are only metadata, and the model-facing loop is intentionally thin.

Your job is to strengthen the system without changing its basic shape.

## What The System Already Supports

Step kinds currently visible to the planner:

- `eval.task`
- `planner.spec`
- `worker.review`
- `revision.score`

Reference syntax uses values such as `$step_id['field']`.

## Workstream 1: T1 Clarification Rubric

T1 measures whether an agent recognizes missing information before taking risky action.

Focus scenarios:

- file moving and renaming
- directory cleanup
- batch shell commands
- small script edits with unclear acceptance criteria

Focus files:

- `engine/nodes/eval/task.py`
- `engine/nodes/eval/planner_spec.py`
- `tests/public/cases/01_t1_clarification.yaml`

What we want from you:

1. Improve the fields used to describe ambiguity, risk, and required clarification
2. Make the rubric strict enough to catch premature execution
3. Keep public cases readable while leaving room for hidden cases

When reviewing submissions here, we care about:

- whether missing information is represented explicitly
- whether destructive or irreversible operations are treated as risky
- whether a stronger spec improves the score

## Workstream 2: T2 Planner-to-Worker Transmission

T2 measures whether a planner's spec is clear enough for a worker to understand and execute.

It does not need to test full execution at first. The primary surface is spec transmission quality:

- did the planner say enough?
- did the worker catch the intended work?
- did worker feedback help the planner produce a better second spec?

Focus files:

- `engine/nodes/eval/worker_review.py`
- `engine/nodes/eval/revision_score.py`
- `tests/public/cases/02_t2_revision.yaml`

What we want from you:

1. Make worker feedback structured and useful
2. Score whether spec v2 is better than spec v1
3. Preserve the distinction between "unclear but safe" and "clear but unsafe"

When reviewing submissions here, we care about:

- objective clarity
- file/path specificity
- constraints and forbidden actions
- acceptance criteria
- risk and rollback notes

## Workstream 3: Planner Tooling

The planner only gets a generic editing surface:

- `add_step`
- `update_step`
- `connect_steps`
- `get_catalog`
- `get_details`
- `get_pipeline`

The goal is to make the minimal tool surface usable for drafting T1/T2 evaluation pipelines.

Focus files:

- `agent/tools.py`
- `agent/catalog.py`
- `agent/react_loop.py`

What we want from you:

1. Improve tool descriptions and config schemas
2. Make catalog metadata useful to a model
3. Keep the tools generic rather than adding one-off helpers for every case

## Interview Discussion

Be ready to walk through:

1. What makes an ambiguous file-op task risky
2. How you would separate clarification quality from execution quality
3. How planner-to-worker specs should be graded
4. How you would evolve this scaffold into hidden evals and model comparisons
