"""
Currency conversion via frankfurter.app (free, no API key needed).
Uses European Central Bank rates. One call per run, cached in memory.
"""

import requests
import logging

logger = logging.getLogger(__name__)

_cached_rate = None


def get_usd_to_gbp_rate() -> float:
    """Fetch current USD to GBP exchange rate.

    Returns:
        GBP per 1 USD (e.g. 0.79 means $1 = £0.79).
        Falls back to 0.80 if API is unreachable.
    """
    global _cached_rate

    if _cached_rate is not None:
        return _cached_rate

    try:
        response = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "GBP"},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        rate = data.get("rates", {}).get("GBP")

        if rate:
            _cached_rate = float(rate)
            logger.info(f"Exchange rate: $1 = \u00a3{_cached_rate:.4f}")
            return _cached_rate

    except Exception as e:
        logger.warning(f"Failed to fetch exchange rate: {e}. Using fallback 0.80")

    _cached_rate = 0.80
    return _cached_rate


def usd_to_gbp(amount_usd: float) -> float:
    """Convert USD amount to GBP using current rate."""
    rate = get_usd_to_gbp_rate()
    return round(amount_usd * rate, 4)
