"""Market data ingestion with 30-second TTL cache."""

from __future__ import annotations

import logging
import time
from typing import Any

import yfinance as yf

from config import YFINANCE_CACHE_TTL_SECONDS

logger = logging.getLogger(__name__)

# In-memory cache: {symbol: {"closes": [...], "fetched_at": float, "current_price": float}}
_cache: dict[str, dict[str, Any]] = {}


def _is_stale(symbol: str) -> bool:
    entry = _cache.get(symbol)
    if entry is None:
        return True
    return (time.time() - entry["fetched_at"]) > YFINANCE_CACHE_TTL_SECONDS


def fetch_price_data(symbol: str, period: str = "3mo", interval: str = "1d") -> list[float]:
    """
    Fetch closing prices for a symbol. Uses in-memory cache with 30s TTL.
    Returns empty list on failure.
    """
    symbol = symbol.strip().upper()

    if not _is_stale(symbol):
        return _cache[symbol]["closes"]

    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)

        if history.empty:
            logger.warning("No market data returned for %s", symbol)
            return _cache.get(symbol, {}).get("closes", [])

        closes = [round(float(c), 4) for c in history["Close"].dropna().tolist()]
        current_price = closes[-1] if closes else 0.0

        _cache[symbol] = {
            "closes": closes,
            "current_price": current_price,
            "fetched_at": time.time(),
        }

        logger.debug("Fetched %d candles for %s (latest: %.2f)", len(closes), symbol, current_price)
        return closes

    except Exception as exc:
        logger.error("Failed to fetch data for %s: %s", symbol, exc)
        # Return stale cache if available
        return _cache.get(symbol, {}).get("closes", [])


def get_current_price(symbol: str) -> float:
    """Get the latest closing price for a symbol."""
    symbol = symbol.strip().upper()

    if not _is_stale(symbol):
        return _cache[symbol].get("current_price", 0.0)

    closes = fetch_price_data(symbol)
    return closes[-1] if closes else 0.0


def clear_cache() -> None:
    """Clear the entire price cache."""
    _cache.clear()


def get_cache_status() -> dict[str, Any]:
    """Return cache diagnostics."""
    now = time.time()
    return {
        symbol: {
            "candles": len(entry["closes"]),
            "current_price": entry["current_price"],
            "age_seconds": round(now - entry["fetched_at"], 1),
            "stale": (now - entry["fetched_at"]) > YFINANCE_CACHE_TTL_SECONDS,
        }
        for symbol, entry in _cache.items()
    }
