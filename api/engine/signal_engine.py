"""Signal engine — runs all indicators and produces unified signal for a symbol."""

from __future__ import annotations

import logging

from indicators.sma import run_sma_indicator
from indicators.rsi import run_rsi_indicator
from indicators.sentiment import run_sentiment_indicator
from indicators.aggregator import aggregate_signals
from engine.data_ingest import fetch_price_data

import database as db

logger = logging.getLogger(__name__)


async def generate_signal(asset: str, context: str = "") -> dict:
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

    # Step 3: Aggregate
    unified = aggregate_signals([sma_result, rsi_result, sentiment_result])

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

    logger.info(
        "Signal generated for %s: %s @ %d%% confidence",
        asset, unified["signal"], unified["confidence_score"],
    )

    return unified


async def generate_signals_batch(assets: list[str], context: str = "") -> list[dict]:
    """Run signal generation for multiple assets."""
    results = []
    for asset in assets:
        try:
            result = await generate_signal(asset, context)
            results.append(result)
        except Exception as exc:
            logger.error("Signal generation failed for %s: %s", asset, exc)
    return results
