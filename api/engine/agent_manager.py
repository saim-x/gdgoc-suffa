"""Agent manager — single decision logic, three cosmetic variants."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import database as db
from config import TRADE_FEE_RATE, SLIPPAGE_RATE, PENDING_EXPIRY_SECONDS
from engine.data_ingest import get_current_price

logger = logging.getLogger(__name__)


async def process_signal_for_agents(signal: dict) -> list[dict]:
    """
    Feed a unified signal to all active agents.
    Each agent applies its own confidence threshold to decide:
      - confidence >= 90  → auto execute
      - 60 <= confidence < 90 → pending approval (unless autonomous)
      - confidence < 60 → ignore

    Returns list of action records.
    """
    agents = await db.get_agents()
    portfolio = await db.get_portfolio()
    autonomous = portfolio.get("autonomous_mode", False)
    results = []

    for agent in agents:
        if agent["status"] != "active":
            continue

        try:
            action_record = await _agent_decide(agent, signal, autonomous)
            results.append(action_record)
        except Exception as exc:
            logger.error("Agent %s failed on signal %s: %s", agent["id"], signal.get("id"), exc)

    return results


async def _agent_decide(agent: dict, signal: dict, autonomous: bool) -> dict:
    """Core decision logic — identical for all agents, threshold varies."""
    confidence = signal["confidence_score"]
    threshold = agent.get("confidence_threshold", 85)
    asset = signal["asset"]
    direction = signal["signal"]  # buy/sell/hold

    if direction == "hold":
        # Hold signals are silently skipped — no activity spam
        return {
            "agent_id": agent["id"],
            "action": "no_action",
            "confidence": confidence,
            "asset": asset,
            "reason": "Hold signal — no directional bias",
        }

    if confidence < 60:
        await db.insert_activity(
            type_="rejected",
            asset=asset,
            confidence=confidence,
            action=direction,
            pnl=0,
            note=f"Agent {agent['name']}: {direction.upper()} signal for {asset} at {confidence}% confidence — below 60% threshold.",
            agent_id=agent["id"],
        )
        return {
            "agent_id": agent["id"],
            "action": "no_action",
            "confidence": confidence,
            "asset": asset,
            "reason": "Below execution threshold",
        }

    # Calculate position size
    available = agent["assigned_capital"] - agent["used_capital"]
    max_fraction = 0.2  # max 20% of agent capital per trade
    position_size = round(min(available, agent["assigned_capital"] * max_fraction), 2)

    if position_size <= 0:
        await db.insert_activity(
            type_="rejected",
            asset=asset,
            confidence=confidence,
            action=direction,
            pnl=0,
            note=f"Agent {agent['name']} has no available capital. Trade blocked.",
            agent_id=agent["id"],
        )
        return {
            "agent_id": agent["id"],
            "action": "blocked",
            "confidence": confidence,
            "asset": asset,
            "reason": "No available capital",
        }

    if confidence >= 90 or (autonomous and confidence >= threshold):
        # Auto execute
        return await _execute_trade(agent, signal, position_size)
    elif confidence >= 60:
        # Pending approval
        pending = await db.insert_pending(
            agent_id=agent["id"],
            asset=asset,
            direction=direction,
            confidence=confidence,
            position_size=position_size,
            rationale=signal.get("reasoning", ""),
            signal_id=signal.get("id"),
            expires_seconds=PENDING_EXPIRY_SECONDS,
        )
        if not pending.get("deduplicated"):
            await db.insert_activity(
                type_="pending",
                asset=asset,
                confidence=confidence,
                action=direction,
                pnl=0,
                note=f"Agent {agent['name']}: Trade pending approval ({confidence}% confidence).",
                agent_id=agent["id"],
            )
        return {
            "agent_id": agent["id"],
            "action": "request_approval",
            "pending_id": pending["id"],
            "confidence": confidence,
            "asset": asset,
            "position_size": position_size,
            "reason": "Awaiting user approval" if not pending.get("deduplicated") else "Updated existing pending approval",
        }

    return {"agent_id": agent["id"], "action": "no_action", "asset": asset}


async def _execute_trade(agent: dict, signal: dict, position_size: float) -> dict:
    """Execute a simulated trade with fee and slippage."""
    asset = signal["asset"]
    direction = signal["signal"]
    entry_price = get_current_price(asset)

    if entry_price <= 0:
        logger.warning("Cannot execute trade for %s — no price data", asset)
        return {"agent_id": agent["id"], "action": "blocked", "reason": "No price data"}

    # Apply slippage to entry
    if direction == "buy":
        entry_price = round(entry_price * (1 + SLIPPAGE_RATE), 4)
    else:
        entry_price = round(entry_price * (1 - SLIPPAGE_RATE), 4)

    fee = round(position_size * TRADE_FEE_RATE, 2)

    trade = await db.insert_trade(
        agent_id=agent["id"],
        asset=asset,
        direction=direction,
        entry_price=entry_price,
        position_size=position_size,
        fee=fee,
        slippage=round(entry_price * SLIPPAGE_RATE, 4),
        confidence=signal["confidence_score"],
        signal_id=signal.get("id"),
    )
    if not trade:
        await db.insert_activity(
            type_="rejected",
            asset=asset,
            confidence=signal["confidence_score"],
            action=direction,
            pnl=0,
            note=f"Agent {agent['name']}: Trade blocked by capital guard.",
            agent_id=agent["id"],
        )
        return {
            "agent_id": agent["id"],
            "action": "blocked",
            "confidence": signal["confidence_score"],
            "asset": asset,
            "direction": direction,
            "reason": "Capital limit exceeded",
        }

    await db.insert_activity(
        type_="executed",
        asset=asset,
        confidence=signal["confidence_score"],
        action=direction,
        pnl=0,
        note=f"Agent {agent['name']}: Executed {direction} on {asset} @ ${entry_price:.2f}, size ${position_size:.2f}, fee ${fee:.2f}.",
        agent_id=agent["id"],
    )

    logger.info(
        "Trade executed: %s %s %s @ %.2f, size %.2f, fee %.2f",
        agent["name"], direction, asset, entry_price, position_size, fee,
    )

    return {
        "agent_id": agent["id"],
        "action": "execute",
        "trade_id": trade["id"],
        "confidence": signal["confidence_score"],
        "asset": asset,
        "direction": direction,
        "entry_price": entry_price,
        "position_size": position_size,
        "fee": fee,
    }


async def approve_pending_trade(pending_id: str) -> dict | None:
    """Approve a pending trade — execute it."""
    pending = await db.get_pending_by_id(pending_id, status="pending")
    if not pending:
        return None

    agent = await db.get_agent(pending["agent_id"])
    if not agent:
        return None

    available = float(agent["assigned_capital"]) - float(agent["used_capital"])
    if (float(pending["position_size"]) - available) > 1e-9:
        await db.insert_activity(
            type_="rejected",
            asset=pending["asset"],
            confidence=pending["confidence"],
            action=pending["direction"],
            pnl=0,
            note=f"Approval blocked for {agent['name']}: capital limit exceeded.",
            agent_id=agent["id"],
        )
        return {
            "pending_id": pending_id,
            "agent_id": agent["id"],
            "action": "blocked",
            "reason": "Agent capital limit exceeded",
        }

    signal = {
        "asset": pending["asset"],
        "signal": pending["direction"],
        "confidence_score": pending["confidence"],
        "reasoning": pending.get("rationale", ""),
        "id": pending.get("signal_id"),
    }

    executed = await _execute_trade(agent, signal, pending["position_size"])
    if executed.get("action") != "execute":
        return executed

    resolved = await db.resolve_pending(pending_id, approved=True)
    if not resolved:
        logger.warning("Pending %s executed but could not be marked approved", pending_id)

    return executed


async def reject_pending_trade(pending_id: str) -> dict | None:
    """Reject a pending trade."""
    resolved = await db.resolve_pending(pending_id, approved=False)
    if not resolved:
        return None

    await db.insert_activity(
        type_="rejected",
        asset=resolved["asset"],
        confidence=resolved["confidence"],
        action=resolved["direction"],
        pnl=0,
        note="User rejected pending trade.",
        agent_id=resolved["agent_id"],
    )

    return resolved
