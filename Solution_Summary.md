# Solution Summary

I worked on the three parts listed in `TASKS.md`.

For the runtime part, I replaced the placeholder code in `data.market_bars` and `research_chat` with actual implementations.

For the agent part, I kept the existing handwritten loop and focused on making it more stable when tool calls fail or when the assistant does not make useful progress.

For planning, I kept the generic tool interface and improved the catalog and tool metadata so the model has a clearer view of step inputs, outputs, and references.

One practical issue in this repository is that the public examples use symbols like `AAPL`, `MSFT`, and `NVDA`, while BaoStock uses a different symbol format. Because of that, I kept a fallback path in `data.market_bars` so the existing examples and tests still work in this repo.

I also tightened the pipeline export check so the loop does not stop too early on an incomplete draft.

A few smaller changes were added to improve reliability, including clearer execution errors, better draft validation before export, and more explicit handling of failed tool calls.

Some parts still depend on local environment setup, especially the OpenAI-based chat step and BaoStock access.
