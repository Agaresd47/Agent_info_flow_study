import datetime
from typing import Any, Dict

import baostock as bs

from ..base import BaseStep


class MarketBarsStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        symbols = config.get("symbols", [])
        if isinstance(symbols, str):
            symbols = [symbols]
        
        if not symbols:
            raise ValueError(
                "The 'symbols' field is required for data.market_bars and cannot be empty. "
                "BaoStock symbols should look like 'sh.600000' or 'sz.000001'."
            )

        lookback_days = int(config.get("lookback_days", 30))

        # Calculate date range
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=lookback_days)

        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        # BaoStock Login
        lg = bs.login()
        if lg.error_code != "0":
            raise RuntimeError(f"BaoStock login failed: {lg.error_msg}")

        results = {}
        failures = {}
        try:
            for symbol in symbols:
                rs = bs.query_history_k_data_plus(
                    symbol,
                    "date,code,open,high,low,close,volume",
                    start_date=start_date_str,
                    end_date=end_date_str,
                    frequency="d",
                    adjustflag="3",  # Back-adjustment
                )

                if rs.error_code != "0":
                    failures[symbol] = rs.error_msg or "Unknown BaoStock query error"
                    continue

                data_list = []
                while rs.next():
                    row = rs.get_row_data()
                    data_list.append(
                        {
                            "date": row[0],
                            "code": row[1],
                            "open": float(row[2]) if row[2] else 0.0,
                            "high": float(row[3]) if row[3] else 0.0,
                            "low": float(row[4]) if row[4] else 0.0,
                            "close": float(row[5]) if row[5] else 0.0,
                            "volume": float(row[6]) if row[6] else 0.0,
                        }
                    )
                if not data_list:
                    failures[symbol] = "No daily bars returned for the requested date window."
                    continue
                results[symbol] = data_list
        finally:
            bs.logout()

        if failures:
            failure_lines = [
                "{0}: {1}".format(symbol, message) for symbol, message in failures.items()
            ]
            if results:
                raise RuntimeError(
                    "Market data fetch failed for some symbols. "
                    "Fix the failing requests before continuing. "
                    "Failures: {0}".format("; ".join(failure_lines))
                )
            raise RuntimeError(
                "Market data fetch failed for all requested symbols. "
                "Check ticker prefixes and trading availability. "
                "Failures: {0}".format("; ".join(failure_lines))
            )

        return results
