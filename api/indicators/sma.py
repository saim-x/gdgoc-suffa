"""SMA-20 indicator — pure-function, standardized output."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def compute_sma(closes: list[float], period: int = 20) -> float | None:
    """Return the simple moving average for the last `period` closes."""
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def run_sma_indicator(asset: str, closes: list[float]) -> dict:
    """
    Produce a standardized signal from the SMA-20 indicator.

    Returns:
        {asset, signal, confidence_score, reasoning, timestamp}
    """
    now = datetime.now(timezone.utc).isoformat()

    if len(closes) < 20:
        return {
            "asset": asset,
            "signal": "hold",
            "confidence_score": 0,
            "reasoning": f"Insufficient data for SMA-20 ({len(closes)} candles available, 20 required).",
            "timestamp": now,
        }

    sma_20 = compute_sma(closes, 20)
    latest = closes[-1]
    diff = round(latest - sma_20, 4)
    pct_diff = round(abs(diff) / sma_20 * 100, 2) if sma_20 else 0

    # Score based on distance from SMA
    if latest > sma_20:
        signal = "buy"
        # Stronger signal the further above
        raw_confidence = min(50 + pct_diff * 12, 95)
        reasoning = f"Price ${latest:.2f} is {pct_diff:.1f}% above 20-day SMA ${sma_20:.2f}, suggesting upward momentum."
    elif latest < sma_20:
        signal = "sell"
        raw_confidence = min(50 + pct_diff * 12, 95)
        reasoning = f"Price ${latest:.2f} is {pct_diff:.1f}% below 20-day SMA ${sma_20:.2f}, suggesting downward pressure."
    else:
        signal = "hold"
        raw_confidence = 50
        reasoning = f"Price ${latest:.2f} is sitting right on the 20-day SMA, direction unclear."

    return {
        "asset": asset,
        "signal": signal,
        "confidence_score": int(raw_confidence),
        "reasoning": reasoning,
        "timestamp": now,
    }
