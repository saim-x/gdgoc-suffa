"""RSI-14 indicator — pure-function, standardized output."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """Return the RSI for the last `period` closes."""
    if len(closes) < period + 1:
        return None

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]

    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def run_rsi_indicator(asset: str, closes: list[float]) -> dict:
    """
    Produce a standardized signal from the RSI-14 indicator.

    Returns:
        {asset, signal, confidence_score, reasoning, timestamp}
    """
    now = datetime.now(timezone.utc).isoformat()

    if len(closes) < 15:
        return {
            "asset": asset,
            "signal": "hold",
            "confidence_score": 0,
            "reasoning": f"Insufficient data for RSI-14 ({len(closes)} candles, 15 required).",
            "timestamp": now,
        }

    rsi = compute_rsi(closes, 14)

    if rsi >= 70:
        signal = "sell"
        # Overbought — higher RSI = stronger sell signal
        raw_confidence = min(50 + (rsi - 70) * 1.5, 95)
        reasoning = f"RSI-14 at {rsi:.1f} indicates overbought conditions. Mean-reversion selling pressure likely."
    elif rsi <= 30:
        signal = "buy"
        # Oversold — lower RSI = stronger buy signal
        raw_confidence = min(50 + (30 - rsi) * 1.5, 95)
        reasoning = f"RSI-14 at {rsi:.1f} indicates oversold conditions. Bounce-back buying opportunity."
    else:
        signal = "hold"
        # Neutral zone — confidence inversely related to distance from extremes
        distance_from_center = abs(rsi - 50)
        raw_confidence = 40 + distance_from_center * 0.5
        if rsi > 55:
            reasoning = f"RSI-14 at {rsi:.1f} is mildly elevated but not overbought. Slight bearish lean."
        elif rsi < 45:
            reasoning = f"RSI-14 at {rsi:.1f} is mildly depressed but not oversold. Slight bullish lean."
        else:
            reasoning = f"RSI-14 at {rsi:.1f} is neutral. No directional momentum signal."

    return {
        "asset": asset,
        "signal": signal,
        "confidence_score": int(raw_confidence),
        "reasoning": reasoning,
        "timestamp": now,
    }
