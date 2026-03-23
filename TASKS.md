# Quant Research Drafting Exercise

You have **2 hours** for this exercise.

## Project Snapshot

This repository contains a small research-drafting system with two moving parts:

- a YAML runtime that executes step-based research plans
- a handwritten agent loop that asks an LLM to assemble those plans through tool calls

The starter code is deliberately uneven. Some parts are real, some are placeholders, and some are just not robust enough yet.

Your job is to strengthen the system without changing its basic product shape.

## What The System Already Supports

Step kinds currently visible to the planner:

- `trigger.manual`
- `data.market_bars`
- `factor.momentum`
- `factor.rank`
- `research_chat`
- `output.report`

Reference syntax uses values such as `$step_id['field']`.

## Workstream 1: Replace The Mock Runtime Steps

Two runtime steps are placeholders in the starter repo:

- `data.market_bars`
- `research_chat`

We want them turned into real integrations.

### `data.market_bars`

Implement this step with the BaoStock API.

Expected support:

- `symbols`
- `lookback_days`

Expected behavior:

- log in to BaoStock
- request daily bars for the requested symbols
- convert the response into grouped bars by symbol
- surface query failures clearly

You may choose a reasonable date-window strategy from `lookback_days`.

### `research_chat`

Implement this step with a real chat-completions API.

Expected support:

- `prompt`
- a sensible default model, or a configurable model field

Expected behavior:

- send the prompt to a real model
- return generated text in a structured payload
- surface API failures clearly

Focus files:

- `engine/nodes/data/market_bars.py`
- `engine/nodes/ai/research_chat.py`

## Workstream 2: Planner Runtime Reliability

The handwritten agent loop is serviceable, but it is easy to derail.

Today it tends to:

- stop after an unhelpful assistant turn
- fail to recover after a bad tool call
- produce brittle conversations when tool outputs are ambiguous

Focus files:

- `agent/react_loop.py`

What we want from you:

1. Make the loop more resilient while keeping it handwritten
2. Keep the control flow understandable
3. Prevent runaway behavior with a clear stop strategy

When reviewing submissions here, we care about:

- message sequencing
- tool-result handling
- failure recovery
- termination rules

## Workstream 3: Stable Planning With Generic Tools

This repo intentionally does **not** provide per-step helper tools.

The planner only gets a basic editing surface:

- `add_step`
- `update_step`
- `connect_steps`
- `get_catalog`
- `get_details`
- `get_pipeline`

The goal is to make that minimal tool surface usable for a simple research request.

Target request:

> Use the market bars to compute momentum, rank the symbols by momentum, and then explain the ranking.

Focus files:

- `agent/tools.py`
- `agent/catalog.py`
- any planner prompt or loop logic you think is relevant

What we want from you:

1. Improve how the planner learns step shapes and config structure
2. Keep the tool surface generic
3. Increase the chances of getting a meaningful pipeline rather than an empty or hollow one

When reviewing submissions here, we care about:

- tool descriptions
- schema clarity
- metadata quality
- how you handle open-ended config dictionaries

## Interview Discussion

Be ready to walk through:

1. The control model you chose for the handwritten agent loop
2. The limits of generic tools for LLM planning
3. What makes a node catalog actually useful to a model
4. How you would evolve this codebase for richer factor-research workflows
