"""Background scheduler — single async loop for signal generation and cleanup."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import database as db
from config import DEFAULT_WATCHLIST, SIGNAL_POLL_INTERVAL_SECONDS
from engine.signal_engine import generate_signal
from engine.agent_manager import process_signal_for_agents

logger = logging.getLogger(__name__)

_running = False
_task: asyncio.Task | None = None


async def _signal_loop() -> None:
    """Main background loop: generate signals → feed to agents → cleanup expired pending."""
    global _running
    _running = True
    logger.info("Scheduler started. Polling every %ds for %d symbols.", SIGNAL_POLL_INTERVAL_SECONDS, len(DEFAULT_WATCHLIST))

    while _running:
        try:
            # Expire stale pending approvals
            expired_count = await db.expire_pending()
            if expired_count > 0:
                logger.info("Expired %d pending approvals", expired_count)

            # Generate signals for all watchlist symbols
            for symbol in DEFAULT_WATCHLIST:
                if not _running:
                    break
                try:
                    signal = await generate_signal(symbol)
                    if signal.get("is_duplicate"):
                        continue
                    # Feed to agents
                    await process_signal_for_agents(signal)
                except Exception as exc:
                    logger.error("Signal loop error for %s: %s", symbol, exc)

                # Small delay between symbols to avoid hammering yfinance
                await asyncio.sleep(0.5)

        except Exception as exc:
            logger.error("Scheduler loop error: %s", exc, exc_info=True)

        # Wait for next cycle
        try:
            await asyncio.sleep(SIGNAL_POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            break

    logger.info("Scheduler stopped.")


def start_scheduler() -> None:
    """Start the background signal loop."""
    global _task
    if _task is not None and not _task.done():
        logger.warning("Scheduler already running")
        return
    _task = asyncio.create_task(_signal_loop())
    logger.info("Scheduler task created")


def stop_scheduler() -> None:
    """Stop the background signal loop."""
    global _running, _task
    _running = False
    if _task is not None and not _task.done():
        _task.cancel()
    _task = None
    logger.info("Scheduler stop requested")


def is_running() -> bool:
    return _running and _task is not None and not _task.done()
