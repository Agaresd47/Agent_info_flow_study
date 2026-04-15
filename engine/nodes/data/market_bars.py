import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..base import BaseStep

_DATASET_CACHE: Optional[Dict[str, List[Dict[str, Any]]]] = None
_BAOSTOCK_SYMBOL_RE = re.compile(r'^(?:(sh|sz)[\.]?(\d{6})|(\d{6})[\.](SH|SZ))$', re.IGNORECASE)


class MarketBarsStep(BaseStep):
    async def execute(self, config: Dict[str, Any], context: Any) -> Dict[str, Any]:
        symbols = _coerce_symbols(config.get('symbols'))
        if not symbols:
            raise ValueError('Market bars step requires a non-empty symbols list')

        lookback_days = int(config.get('lookback_days', 5))
        if lookback_days <= 0:
            raise ValueError('lookback_days must be a positive integer')

        local_dataset = _load_local_dataset()
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        bao_requests: Dict[str, str] = {}
        unsupported: List[str] = []

        for symbol in symbols:
            normalized = _normalize_baostock_symbol(symbol)
            if normalized is not None:
                bao_requests[symbol] = normalized
                continue
            if symbol in local_dataset:
                grouped[symbol] = _slice_local_bars(local_dataset[symbol], lookback_days)
                continue
            unsupported.append(symbol)

        if unsupported:
            raise ValueError(
                'Unsupported symbols for data.market_bars: {0}. Use BaoStock symbols such as '
                'sh.600000 / sz.000001, or one of the bundled demo symbols: {1}'.format(
                    ', '.join(unsupported),
                    ', '.join(sorted(local_dataset.keys())),
                )
            )

        if bao_requests:
            grouped.update(_query_baostock_grouped_bars(bao_requests, lookback_days))

        return grouped


def _coerce_symbols(raw_symbols: Any) -> List[str]:
    if raw_symbols is None:
        return []
    if isinstance(raw_symbols, str):
        return [raw_symbols]
    if isinstance(raw_symbols, (list, tuple, set)):
        values = [str(item).strip() for item in raw_symbols if str(item).strip()]
        return values
    raise ValueError('symbols must be a string or a list of strings')


def _normalize_baostock_symbol(symbol: str) -> Optional[str]:
    text = str(symbol).strip()
    match = _BAOSTOCK_SYMBOL_RE.match(text)
    if match is None:
        return None

    if match.group(1) and match.group(2):
        exchange = match.group(1).lower()
        code = match.group(2)
    else:
        exchange = match.group(4).lower()
        code = match.group(3)
    return '{0}.{1}'.format(exchange, code)


def _query_baostock_grouped_bars(symbol_map: Dict[str, str], lookback_days: int) -> Dict[str, List[Dict[str, Any]]]:
    try:
        import baostock as bs
    except Exception as exc:
        raise ValueError('BaoStock dependency is unavailable: {0}'.format(exc))

    login_result = bs.login()
    if getattr(login_result, 'error_code', '1') != '0':
        raise ValueError(
            'BaoStock login failed: {0} {1}'.format(
                getattr(login_result, 'error_code', 'unknown'),
                getattr(login_result, 'error_msg', ''),
            ).strip()
        )

    errors: List[str] = []
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    start_date, end_date = _date_window(lookback_days)

    try:
        for requested_symbol, bao_symbol in symbol_map.items():
            query_result = bs.query_history_k_data_plus(
                bao_symbol,
                'date,code,close',
                start_date=start_date,
                end_date=end_date,
                frequency='d',
                adjustflag='3',
            )
            if getattr(query_result, 'error_code', '1') != '0':
                errors.append(
                    'query failed for {0}: {1} {2}'.format(
                        requested_symbol,
                        getattr(query_result, 'error_code', 'unknown'),
                        getattr(query_result, 'error_msg', ''),
                    ).strip()
                )
                continue

            rows: List[Dict[str, Any]] = []
            while query_result.next():
                date_value, _, close_value = query_result.get_row_data()
                if close_value in (None, ''):
                    continue
                try:
                    close = float(close_value)
                except ValueError:
                    continue
                rows.append({'date': date_value, 'close': close})

            rows.sort(key=lambda item: item['date'])
            grouped[requested_symbol] = rows[-lookback_days:]
    finally:
        try:
            bs.logout()
        except Exception:
            pass

    if errors:
        raise ValueError('BaoStock query failure: {0}'.format('; '.join(errors)))
    return grouped


def _date_window(lookback_days: int) -> Tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max((lookback_days * 3), lookback_days + 10))
    return start.isoformat(), end.isoformat()


def _slice_local_bars(series: List[Dict[str, Any]], lookback_days: int) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in series[-lookback_days:]:
        normalized.append({'date': str(item['date']), 'close': float(item['close'])})
    return normalized


def _load_local_dataset() -> Dict[str, List[Dict[str, Any]]]:
    global _DATASET_CACHE
    if _DATASET_CACHE is None:
        dataset_path = Path(__file__).resolve().parents[3] / 'datasets' / 'daily_bars.json'
        with open(dataset_path, 'r', encoding='utf-8') as handle:
            _DATASET_CACHE = json.load(handle)
    return dict(_DATASET_CACHE)
