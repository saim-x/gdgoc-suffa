"""Multi-indicator aggregator — weighted merge into unified signal."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import INDICATOR_WEIGHTS

logger = logging.getLogger(__name__)

# Map signals to numeric direction for averaging
_SIGNAL_DIRECTION = {"buy": 1, "sell": -1, "hold": 0}


def aggregate_signals(indicator_results: list[dict]) -> dict:
    """
    Aggregate multiple indicator signals into a unified confidence score.

    Strategy: weighted-average direction + weighted-average confidence.
    The majority direction wins; confidence is the weighted mean of
    individual confidence scores.

    Args:
        indicator_results: list of standardized indicator outputs, each with
            keys: asset, signal, confidence_score, reasoning, timestamp
            plus an "indicator" key naming the source (sma, rsi, sentiment).

    Returns:
        Unified signal dict with composite confidence and per-indicator breakdown.
    """
    if not indicator_results:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "asset": "UNKNOWN",
            "signal": "hold",
            "confidence_score": 0,
            "reasoning": "No indicator data available.",
            "timestamp": now,
            "indicator_breakdown": {},
        }

    asset = indicator_results[0].get("asset", "UNKNOWN")
    now = datetime.now(timezone.utc).isoformat()

    # Build weighted scores
    weighted_direction = 0.0
    weighted_confidence = 0.0
    total_weight = 0.0
    breakdown = {}
    reasons = []

    for result in indicator_results:
        indicator_name = result.get("indicator", "unknown")
        weight = INDICATOR_WEIGHTS.get(indicator_name, 0.1)

        direction_val = _SIGNAL_DIRECTION.get(result["signal"], 0)
        confidence = result.get("confidence_score", 50)

        weighted_direction += direction_val * weight * (confidence / 100)
        weighted_confidence += confidence * weight
        total_weight += weight

        breakdown[indicator_name] = {
            "signal": result["signal"],
            "confidence_score": confidence,
            "reasoning": result.get("reasoning", ""),
        }
        reasons.append(f"{indicator_name.upper()}: {result['signal']} ({confidence}%)")

    # Normalize
    if total_weight > 0:
        weighted_confidence /= total_weight

    # Determine final direction via weighted vote
    if weighted_direction > 0.1:
        signal = "buy"
    elif weighted_direction < -0.1:
        signal = "sell"
    else:
        signal = "hold"

    confidence_score = int(min(max(weighted_confidence, 0), 100))
    reasoning = "Aggregated from: " + "; ".join(reasons) + "."

    return {
        "asset": asset,
        "signal": signal,
        "confidence_score": confidence_score,
        "reasoning": reasoning,
        "timestamp": now,
        "indicator_breakdown": breakdown,
    }
