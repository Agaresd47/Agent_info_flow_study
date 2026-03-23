from typing import Any, Dict

from ..base import BaseStep


class MarketBarsStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        # Interview task:
        # Replace this mock with a real BaoStock-backed implementation.
        #
        # Expected behavior:
        # - accept config["symbols"]
        # - accept config["lookback_days"]
        # - log in to BaoStock
        # - query daily historical bars for each requested symbol
        # - return grouped bars by symbol in the form:
        #   {
        #       "AAPL": [{"date": "...", "close": 100.0}, ...],
        #       "MSFT": [...]
        #   }
        #
        # Keep the output shape simple and consistent with the downstream
        # momentum and ranking steps.
        return {
            "status": "mock",
            "message": "Replace this mock with a real BaoStock implementation.",
        }
