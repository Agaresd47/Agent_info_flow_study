from typing import Any, Dict

from ..base import BaseStep


class MomentumStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        bars = config.get("bars", {})
        if not isinstance(bars, dict) or not bars:
            raise ValueError("Momentum factor needs a dictionary of bars. Check your data connection ($data_id).")

        scores: Dict[str, float] = {}
        total = len(bars)
        valid = 0
        window = int(config.get("window", 3))
        for symbol, series in bars.items():
            closes = [item["close"] for item in series][-max(window, 2):] if isinstance(series, list) else []
            if len(closes) < 2:
                continue
            scores[symbol] = round((closes[-1] / closes[0]) - 1.0, 6)
            valid += 1
        coverage = round(valid / total, 6) if total else 0.0
        return {"scores": scores, "coverage": coverage, "window": window}
