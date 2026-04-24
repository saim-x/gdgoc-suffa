"""Signal engine — runs all indicators and produces unified signal for a symbol."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from config import SIGNAL_DEDUP_CONFIDENCE_DELTA, SIGNAL_DEDUP_WINDOW_SECONDS
from indicators.sma import run_sma_indicator
from indicators.rsi import run_rsi_indicator
from indicators.sentiment import run_sentiment_indicator
from indicators.aggregator import aggregate_signals
from engine.data_ingest import fetch_price_data
from engine.mirofish_layer import run_mirofish_processing_layer

import database as db

logger = logging.getLogger(__name__)


def _is_recent_duplicate(previous_signal: dict | None, candidate_signal: dict) -> bool:
    if not previous_signal:
        return False
    if previous_signal.get("asset") != candidate_signal.get("asset"):
        return False
    if previous_signal.get("signal") != candidate_signal.get("signal"):
        return False

    prev_conf = int(previous_signal.get("confidence_score", 0))
    next_conf = int(candidate_signal.get("confidence_score", 0))
    if abs(prev_conf - next_conf) > SIGNAL_DEDUP_CONFIDENCE_DELTA:
        return False

    created_at = previous_signal.get("created_at")
    if not isinstance(created_at, str):
        return False
    try:
        created_dt = datetime.fromisoformat(created_at)
    except ValueError:
        return False
    if created_dt.tzinfo is None:
        created_dt = created_dt.replace(tzinfo=timezone.utc)

    age_seconds = (datetime.now(timezone.utc) - created_dt).total_seconds()
    return age_seconds <= SIGNAL_DEDUP_WINDOW_SECONDS


async def generate_signal(asset: str, context: str = "", dedupe: bool = True) -> dict:
    """
    Full signal pipeline for one asset:
    1. Fetch market data
    2. Run SMA-20, RSI-14, Groq Sentiment
    3. Aggregate into unified signal
    4. Persist to database

    Returns the unified signal dict.
    """
    asset = asset.strip().upper()
    logger.info("Generating signal for %s", asset)

    # Step 1: Fetch price data
    closes = fetch_price_data(asset)

    # Step 2: Run all indicators
    sma_result = run_sma_indicator(asset, closes)
    sma_result["indicator"] = "sma"

    rsi_result = run_rsi_indicator(asset, closes)
    rsi_result["indicator"] = "rsi"

    sentiment_result = run_sentiment_indicator(asset, context)
    sentiment_result["indicator"] = "sentiment"

    # Step 2.5: MiroFish swarm consensus layer (additional processing layer)
    mirofish_result = run_mirofish_processing_layer(
        asset=asset,
        indicator_results=[sma_result, rsi_result, sentiment_result],
        closes=closes,
        context=context,
    )
    mirofish_result["indicator"] = "mirofish"

    # Step 3: Aggregate
    unified = aggregate_signals([sma_result, rsi_result, sentiment_result, mirofish_result])

    # Skip storing duplicate near-identical signals generated too recently.
    if dedupe:
        previous = await db.get_latest_signal(unified["asset"])
        if _is_recent_duplicate(previous, unified):
            logger.info(
                "Skipping duplicate signal for %s (%s @ %d%% already generated recently)",
                unified["asset"],
                unified["signal"],
                unified["confidence_score"],
            )
            duplicate = dict(previous)
            duplicate["is_duplicate"] = True
            return duplicate

    # Step 4: Persist
    stored = await db.insert_signal(
        asset=unified["asset"],
        signal=unified["signal"],
        confidence_score=unified["confidence_score"],
        reasoning=unified["reasoning"],
        indicator_breakdown=unified.get("indicator_breakdown"),
    )

    # Merge DB id into result
    unified["id"] = stored["id"]
    unified["created_at"] = stored["created_at"]
    unified["is_duplicate"] = False

    logger.info(
        "Signal generated for %s: %s @ %d%% confidence",
        asset, unified["signal"], unified["confidence_score"],
    )

    return unified


async def generate_signals_batch(assets: list[str], context: str = "", dedupe: bool = True) -> list[dict]:
    """Run signal generation for multiple assets."""
    results = []
    for asset in assets:
        try:
            result = await generate_signal(asset, context, dedupe=dedupe)
            results.append(result)
        except Exception as exc:
            logger.error("Signal generation failed for %s: %s", asset, exc)
    return results
