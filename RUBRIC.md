# Rubric

## Core Evaluation Goals

1. ReAct architecture understanding
2. Tool-call stability with generic tools
3. Correct implementation of real runtime steps:
   - `data.market_bars` using BaoStock
   - `research_chat` using a real LLM API

## Strong Signals

- Improves the handwritten loop without overcomplicating it
- Makes tool calls reliable while keeping the tool surface basic
- Implements `data.market_bars` cleanly using BaoStock data
- Replaces the mock `research_chat` step with a real API-backed implementation
- Adds focused validation or tests

## Weak Signals

- Replaces the agent loop with a framework instead of improving it
- Solves tool instability by adding many specialized tools
- Leaves `data.market_bars` mocked
- Leaves `research_chat` mocked
- Hardcodes answers only for the sample prompt
