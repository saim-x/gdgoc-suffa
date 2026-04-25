"""Trade executor — close trades, portfolio updates, daily summaries."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from statistics import mean

import database as db
from engine.data_ingest import get_current_price
from config import TRADE_FEE_RATE, SLIPPAGE_RATE

logger = logging.getLogger(__name__)


async def close_trade(trade_id: str) -> dict | None:
    """
    Close an open trade at the current market price.
    Applies exit slippage and updates portfolio.
    """
    trades = await db.get_trades(status="open")
    trade = next((t for t in trades if t["id"] == trade_id), None)
    if not trade:
        return None

    exit_price = get_current_price(trade["asset"])
    if exit_price <= 0:
        logger.warning("Cannot close trade %s — no price data for %s", trade_id, trade["asset"])
        return None

    # Apply exit slippage
    if trade["direction"] == "buy":
        exit_price = round(exit_price * (1 - SLIPPAGE_RATE), 4)
    else:
        exit_price = round(exit_price * (1 + SLIPPAGE_RATE), 4)

    result = await db.close_trade(trade_id, exit_price)

    if result:
        await db.insert_activity(
            type_="executed",
            asset=result["asset"],
            confidence=result.get("confidence", 0),
            action="sell" if trade["direction"] == "buy" else "buy",
            pnl=result["pnl"],
            note=f"Closed {trade['direction']} @ ${exit_price:.2f}. P&L: ${result['pnl']:.2f}.",
            agent_id=result["agent_id"],
        )
        logger.info("Trade %s closed. P&L: %.2f", trade_id, result["pnl"])

        # Update today's P&L in portfolio
        today = datetime.now(timezone.utc).date().isoformat()
        portfolio = await db.get_portfolio()
        today_trades = await db.get_trades(status="closed")
        today_pnl = sum(
            t["pnl"] for t in today_trades
            if t.get("closed_at", "").startswith(today)
        )
        await db.update_portfolio(today_pnl=round(today_pnl, 2))

    return result


async def get_portfolio_state() -> dict:
    """Build comprehensive portfolio state for the API."""
    portfolio = await db.get_portfolio()
    agents = await db.get_agents()
    open_trades = await db.get_trades(status="open")

    # Calculate live P&L for open trades
    active_positions = []
    unrealized_pnl = 0.0
    for trade in open_trades:
        current = get_current_price(trade["asset"])
        live_pnl = 0.0
        if current > 0 and trade.get("entry_price", 0) > 0 and trade.get("position_size", 0) > 0:
            direction = trade.get("direction")
            if direction == "buy":
                live_pnl = round(
                    (current - trade["entry_price"]) / trade["entry_price"] * trade["position_size"] - trade["fee"],
                    2,
                )
            elif direction == "sell":
                live_pnl = round(
                    (trade["entry_price"] - current) / trade["entry_price"] * trade["position_size"] - trade["fee"],
                    2,
                )

        unrealized_pnl += live_pnl
        active_positions.append({
            "id": trade["id"],
            "asset": trade["asset"],
            "direction": trade["direction"],
            "entry_price": trade["entry_price"],
            "current_price": current,
            "position_size": trade["position_size"],
            "pnl": live_pnl,
            "opened_at": trade["opened_at"],
            "agent_id": trade["agent_id"],
        })

    total_allocated = sum(a["assigned_capital"] for a in agents if a["status"] == "active")
    total_used = sum(a["used_capital"] for a in agents)

    return {
        "total_capital": portfolio.get("total_capital", 0),
        "available_capital": portfolio.get("available_capital", 0),
        "total_pnl": round(portfolio.get("total_pnl", 0) + unrealized_pnl, 2),
        "today_pnl": portfolio.get("today_pnl", 0),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "autonomous_mode": portfolio.get("autonomous_mode", False),
        "risk_level": portfolio.get("risk_level", "medium"),
        "total_allocated": total_allocated,
        "total_used": round(total_used, 2),
        "active_positions": active_positions,
        "position_count": len(active_positions),
    }


async def build_daily_summary(date_str: str | None = None) -> dict:
    """Generate and persist a daily trading summary."""
    if not date_str:
        date_str = datetime.now(timezone.utc).date().isoformat()

    all_trades = await db.get_trades()
    day_trades = [t for t in all_trades if t.get("opened_at", "").startswith(date_str)]
    closed_day = [t for t in day_trades if t["status"] == "closed"]

    trades_executed = len(day_trades)
    wins = [t for t in closed_day if t["pnl"] > 0]
    losses = [t for t in closed_day if t["pnl"] < 0]
    total_pnl = round(sum(t["pnl"] for t in closed_day), 2)
    win_rate = round((len(wins) / len(closed_day)) * 100, 1) if closed_day else 0.0
    avg_conf = round(mean(t.get("confidence", 0) for t in day_trades), 1) if day_trades else 0.0

    # Generate insights
    insights = []
    if wins:
        best = max(wins, key=lambda t: t["pnl"])
        insights.append(f"Best trade: {best['asset']} +${best['pnl']:.2f}")
    if losses:
        worst = min(losses, key=lambda t: t["pnl"])
        insights.append(f"Worst trade: {worst['asset']} -${abs(worst['pnl']):.2f}")
    if trades_executed:
        insights.append(f"{trades_executed} trades executed with {avg_conf:.0f}% avg confidence")
    if total_pnl > 0:
        insights.append(f"Net positive day: +${total_pnl:.2f}")
    elif total_pnl < 0:
        insights.append(f"Net negative day: -${abs(total_pnl):.2f}")

    summary_data = {
        "trades_executed": trades_executed,
        "win_count": len(wins),
        "loss_count": len(losses),
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "avg_confidence": avg_conf,
        "insights": insights,
    }

    return await db.upsert_daily_summary(date_str, summary_data)
