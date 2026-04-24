"""SQLite persistence layer with async support and mutex-protected writes."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from config import DATABASE_PATH, DEFAULT_AGENTS, DEFAULT_TOTAL_CAPITAL

logger = logging.getLogger(__name__)

# Global mutex for write operations (trade execution, capital allocation)
_write_lock = asyncio.Lock()

# ── Schema ────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    strategy        TEXT NOT NULL,
    assigned_capital REAL NOT NULL DEFAULT 0,
    used_capital    REAL NOT NULL DEFAULT 0,
    confidence_threshold INTEGER NOT NULL DEFAULT 85,
    status          TEXT NOT NULL DEFAULT 'active',
    performance     REAL NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio (
    id              TEXT PRIMARY KEY DEFAULT 'main',
    total_capital   REAL NOT NULL,
    available_capital REAL NOT NULL,
    total_pnl       REAL NOT NULL DEFAULT 0,
    today_pnl       REAL NOT NULL DEFAULT 0,
    autonomous_mode INTEGER NOT NULL DEFAULT 0,
    risk_level      TEXT NOT NULL DEFAULT 'medium',
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id              TEXT PRIMARY KEY,
    asset           TEXT NOT NULL,
    signal          TEXT NOT NULL,
    confidence_score INTEGER NOT NULL,
    reasoning       TEXT NOT NULL,
    indicator_breakdown TEXT NOT NULL DEFAULT '{}',
    agent_id        TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    asset           TEXT NOT NULL,
    direction       TEXT NOT NULL,
    entry_price     REAL NOT NULL,
    exit_price      REAL,
    position_size   REAL NOT NULL,
    fee             REAL NOT NULL DEFAULT 0,
    slippage        REAL NOT NULL DEFAULT 0,
    pnl             REAL NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'open',
    signal_id       TEXT,
    confidence      INTEGER NOT NULL DEFAULT 0,
    opened_at       TEXT NOT NULL,
    closed_at       TEXT
);

CREATE TABLE IF NOT EXISTS pending_approvals (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    asset           TEXT NOT NULL,
    direction       TEXT NOT NULL,
    confidence      INTEGER NOT NULL,
    position_size   REAL NOT NULL,
    rationale       TEXT NOT NULL DEFAULT '',
    signal_id       TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TEXT NOT NULL,
    expires_at      TEXT NOT NULL,
    resolved_at     TEXT
);

CREATE TABLE IF NOT EXISTS activity (
    id              TEXT PRIMARY KEY,
    timestamp       TEXT NOT NULL,
    type            TEXT NOT NULL,
    asset           TEXT NOT NULL,
    confidence      INTEGER NOT NULL DEFAULT 0,
    action          TEXT NOT NULL DEFAULT 'hold',
    pnl             REAL NOT NULL DEFAULT 0,
    note            TEXT NOT NULL DEFAULT '',
    agent_id        TEXT
);

CREATE TABLE IF NOT EXISTS daily_summaries (
    id              TEXT PRIMARY KEY,
    date            TEXT NOT NULL UNIQUE,
    trades_executed INTEGER NOT NULL DEFAULT 0,
    win_count       INTEGER NOT NULL DEFAULT 0,
    loss_count      INTEGER NOT NULL DEFAULT 0,
    total_pnl       REAL NOT NULL DEFAULT 0,
    win_rate        REAL NOT NULL DEFAULT 0,
    avg_confidence  REAL NOT NULL DEFAULT 0,
    insights        TEXT NOT NULL DEFAULT '[]',
    created_at      TEXT NOT NULL
);
"""


# ── Connection Helper ─────────────────────────────────────────────────

async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_database() -> None:
    """Create tables and seed default data if empty."""
    db = await get_db()
    try:
        await db.executescript(_SCHEMA)
        await db.commit()

        # Seed portfolio if missing
        row = await db.execute_fetchall("SELECT id FROM portfolio WHERE id = 'main'")
        if not row:
            now = _now()
            await db.execute(
                "INSERT INTO portfolio (id, total_capital, available_capital, updated_at) VALUES (?, ?, ?, ?)",
                ("main", DEFAULT_TOTAL_CAPITAL, DEFAULT_TOTAL_CAPITAL, now),
            )
            await db.commit()
            logger.info("Seeded portfolio with %.2f capital", DEFAULT_TOTAL_CAPITAL)

        # Seed agents if missing
        existing = await db.execute_fetchall("SELECT id FROM agents")
        existing_ids = {r["id"] for r in existing}
        now = _now()
        for agent_def in DEFAULT_AGENTS:
            if agent_def["id"] not in existing_ids:
                await db.execute(
                    """INSERT INTO agents (id, name, strategy, assigned_capital, confidence_threshold, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        agent_def["id"], agent_def["name"], agent_def["strategy"],
                        agent_def["assigned_capital"], agent_def["confidence_threshold"],
                        agent_def["status"], now, now,
                    ),
                )
        await db.commit()
        logger.info("Database initialized successfully")
    finally:
        await db.close()


# ── Helpers ───────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return str(uuid.uuid4())[:12]


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows: list) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


# ── Portfolio CRUD ────────────────────────────────────────────────────

async def get_portfolio() -> dict[str, Any]:
    db = await get_db()
    try:
        row = await db.execute_fetchall("SELECT * FROM portfolio WHERE id = 'main'")
        if row:
            d = dict(row[0])
            d["autonomous_mode"] = bool(d["autonomous_mode"])
            return d
        return {}
    finally:
        await db.close()


async def update_portfolio(**fields: Any) -> None:
    async with _write_lock:
        db = await get_db()
        try:
            fields["updated_at"] = _now()
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + ["main"]
            await db.execute(f"UPDATE portfolio SET {set_clause} WHERE id = ?", values)
            await db.commit()
        finally:
            await db.close()


# ── Agents CRUD ───────────────────────────────────────────────────────

async def get_agents() -> list[dict[str, Any]]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM agents ORDER BY name")
        return _rows_to_list(rows)
    finally:
        await db.close()


async def get_agent(agent_id: str) -> dict[str, Any] | None:
    db = await get_db()
    try:
        rows = await db.execute_fetchall("SELECT * FROM agents WHERE id = ?", (agent_id,))
        return _row_to_dict(rows[0]) if rows else None
    finally:
        await db.close()


async def update_agent(agent_id: str, **fields: Any) -> dict[str, Any] | None:
    async with _write_lock:
        db = await get_db()
        try:
            fields["updated_at"] = _now()
            set_clause = ", ".join(f"{k} = ?" for k in fields)
            values = list(fields.values()) + [agent_id]
            await db.execute(f"UPDATE agents SET {set_clause} WHERE id = ?", values)
            await db.commit()
            rows = await db.execute_fetchall("SELECT * FROM agents WHERE id = ?", (agent_id,))
            return _row_to_dict(rows[0]) if rows else None
        finally:
            await db.close()


# ── Signals CRUD ──────────────────────────────────────────────────────

async def insert_signal(
    asset: str, signal: str, confidence_score: int, reasoning: str,
    indicator_breakdown: dict | None = None, agent_id: str | None = None,
) -> dict[str, Any]:
    signal_id = f"sig-{_uuid()}"
    now = _now()
    breakdown_json = json.dumps(indicator_breakdown or {})
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO signals (id, asset, signal, confidence_score, reasoning, indicator_breakdown, agent_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (signal_id, asset, signal, confidence_score, reasoning, breakdown_json, agent_id, now),
        )
        await db.commit()
        return {
            "id": signal_id, "asset": asset, "signal": signal,
            "confidence_score": confidence_score, "reasoning": reasoning,
            "indicator_breakdown": indicator_breakdown or {},
            "agent_id": agent_id, "created_at": now,
        }
    finally:
        await db.close()


async def get_signals(limit: int = 50, asset: str | None = None) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        if asset:
            rows = await db.execute_fetchall(
                "SELECT * FROM signals WHERE asset = ? ORDER BY created_at DESC LIMIT ?",
                (asset.upper(), limit),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,),
            )
        result = _rows_to_list(rows)
        for r in result:
            r["indicator_breakdown"] = json.loads(r.get("indicator_breakdown", "{}"))
        return result
    finally:
        await db.close()


# ── Trades CRUD ───────────────────────────────────────────────────────

async def insert_trade(
    agent_id: str, asset: str, direction: str, entry_price: float,
    position_size: float, fee: float, slippage: float,
    confidence: int = 0, signal_id: str | None = None,
) -> dict[str, Any]:
    trade_id = f"trd-{_uuid()}"
    now = _now()
    async with _write_lock:
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO trades (id, agent_id, asset, direction, entry_price, position_size, fee, slippage, confidence, signal_id, opened_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
                (trade_id, agent_id, asset, direction, entry_price, position_size, fee, slippage, confidence, signal_id, now),
            )
            # Update agent used_capital
            await db.execute(
                "UPDATE agents SET used_capital = used_capital + ?, updated_at = ? WHERE id = ?",
                (position_size, now, agent_id),
            )
            # Update portfolio available_capital
            await db.execute(
                "UPDATE portfolio SET available_capital = available_capital - ?, updated_at = ? WHERE id = 'main'",
                (position_size, now),
            )
            await db.commit()
            return {
                "id": trade_id, "agent_id": agent_id, "asset": asset,
                "direction": direction, "entry_price": entry_price,
                "position_size": position_size, "fee": fee, "slippage": slippage,
                "pnl": 0, "status": "open", "confidence": confidence,
                "signal_id": signal_id, "opened_at": now,
            }
        finally:
            await db.close()


async def close_trade(trade_id: str, exit_price: float) -> dict[str, Any] | None:
    async with _write_lock:
        db = await get_db()
        try:
            rows = await db.execute_fetchall("SELECT * FROM trades WHERE id = ? AND status = 'open'", (trade_id,))
            if not rows:
                return None
            trade = dict(rows[0])
            now = _now()

            entry = trade["entry_price"]
            size = trade["position_size"]
            fee = trade["fee"]
            direction = trade["direction"]

            if direction == "buy":
                raw_pnl = (exit_price - entry) / entry * size
            else:
                raw_pnl = (entry - exit_price) / entry * size

            pnl = round(raw_pnl - fee, 2)

            await db.execute(
                "UPDATE trades SET exit_price = ?, pnl = ?, status = 'closed', closed_at = ? WHERE id = ?",
                (exit_price, pnl, now, trade_id),
            )
            # Return capital + pnl to agent and portfolio
            await db.execute(
                "UPDATE agents SET used_capital = MAX(0, used_capital - ?), performance = performance + ?, updated_at = ? WHERE id = ?",
                (size, pnl, now, trade["agent_id"]),
            )
            await db.execute(
                "UPDATE portfolio SET available_capital = available_capital + ? + ?, total_pnl = total_pnl + ?, updated_at = ? WHERE id = 'main'",
                (size, pnl, pnl, now),
            )
            await db.commit()

            trade.update(exit_price=exit_price, pnl=pnl, status="closed", closed_at=now)
            return trade
        finally:
            await db.close()


async def get_trades(status: str | None = None, agent_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        conditions = []
        params: list[Any] = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        rows = await db.execute_fetchall(
            f"SELECT * FROM trades {where} ORDER BY opened_at DESC LIMIT ?",
            (*params, limit),
        )
        return _rows_to_list(rows)
    finally:
        await db.close()


# ── Pending Approvals CRUD ────────────────────────────────────────────

async def insert_pending(
    agent_id: str, asset: str, direction: str, confidence: int,
    position_size: float, rationale: str, signal_id: str | None = None,
    expires_seconds: int = 120,
) -> dict[str, Any]:
    pending_id = f"pnd-{_uuid()}"
    now = datetime.now(timezone.utc)
    expires = (now + __import__("datetime").timedelta(seconds=expires_seconds)).isoformat()
    now_str = now.isoformat()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO pending_approvals (id, agent_id, asset, direction, confidence, position_size, rationale, signal_id, status, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (pending_id, agent_id, asset, direction, confidence, position_size, rationale, signal_id, now_str, expires),
        )
        await db.commit()
        return {
            "id": pending_id, "agent_id": agent_id, "asset": asset,
            "direction": direction, "confidence": confidence,
            "position_size": position_size, "rationale": rationale,
            "signal_id": signal_id, "status": "pending",
            "created_at": now_str, "expires_at": expires,
        }
    finally:
        await db.close()


async def get_pending(status: str = "pending") -> list[dict[str, Any]]:
    db = await get_db()
    try:
        rows = await db.execute_fetchall(
            "SELECT * FROM pending_approvals WHERE status = ? ORDER BY created_at DESC",
            (status,),
        )
        return _rows_to_list(rows)
    finally:
        await db.close()


async def resolve_pending(pending_id: str, approved: bool) -> dict[str, Any] | None:
    async with _write_lock:
        db = await get_db()
        try:
            rows = await db.execute_fetchall(
                "SELECT * FROM pending_approvals WHERE id = ? AND status = 'pending'",
                (pending_id,),
            )
            if not rows:
                return None
            now = _now()
            new_status = "approved" if approved else "rejected"
            await db.execute(
                "UPDATE pending_approvals SET status = ?, resolved_at = ? WHERE id = ?",
                (new_status, now, pending_id),
            )
            await db.commit()
            result = dict(rows[0])
            result["status"] = new_status
            result["resolved_at"] = now
            return result
        finally:
            await db.close()


async def expire_pending() -> int:
    """Expire pending approvals past their expiry time. Returns count expired."""
    now = _now()
    async with _write_lock:
        db = await get_db()
        try:
            cursor = await db.execute(
                "UPDATE pending_approvals SET status = 'expired', resolved_at = ? WHERE status = 'pending' AND expires_at <= ?",
                (now, now),
            )
            await db.commit()
            return cursor.rowcount
        finally:
            await db.close()


# ── Activity CRUD ─────────────────────────────────────────────────────

async def insert_activity(
    type_: str, asset: str, confidence: int = 0, action: str = "hold",
    pnl: float = 0, note: str = "", agent_id: str | None = None,
) -> dict[str, Any]:
    activity_id = f"act-{_uuid()}"
    now = _now()
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO activity (id, timestamp, type, asset, confidence, action, pnl, note, agent_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (activity_id, now, type_, asset, confidence, action, pnl, note, agent_id),
        )
        await db.commit()
        return {
            "id": activity_id, "timestamp": now, "type": type_,
            "asset": asset, "confidence": confidence, "action": action,
            "pnl": pnl, "note": note, "agent_id": agent_id,
        }
    finally:
        await db.close()


async def get_activity(type_filter: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    db = await get_db()
    try:
        if type_filter and type_filter != "all":
            rows = await db.execute_fetchall(
                "SELECT * FROM activity WHERE type = ? ORDER BY timestamp DESC LIMIT ?",
                (type_filter, limit),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM activity ORDER BY timestamp DESC LIMIT ?", (limit,),
            )
        return _rows_to_list(rows)
    finally:
        await db.close()


# ── Daily Summaries ───────────────────────────────────────────────────

async def upsert_daily_summary(date_str: str, summary_data: dict[str, Any]) -> dict[str, Any]:
    summary_id = f"sum-{_uuid()}"
    now = _now()
    db = await get_db()
    try:
        existing = await db.execute_fetchall(
            "SELECT id FROM daily_summaries WHERE date = ?", (date_str,),
        )
        insights_json = json.dumps(summary_data.get("insights", []))
        if existing:
            await db.execute(
                """UPDATE daily_summaries SET trades_executed = ?, win_count = ?, loss_count = ?,
                   total_pnl = ?, win_rate = ?, avg_confidence = ?, insights = ?
                   WHERE date = ?""",
                (
                    summary_data.get("trades_executed", 0),
                    summary_data.get("win_count", 0),
                    summary_data.get("loss_count", 0),
                    summary_data.get("total_pnl", 0),
                    summary_data.get("win_rate", 0),
                    summary_data.get("avg_confidence", 0),
                    insights_json,
                    date_str,
                ),
            )
        else:
            await db.execute(
                """INSERT INTO daily_summaries (id, date, trades_executed, win_count, loss_count,
                   total_pnl, win_rate, avg_confidence, insights, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary_id, date_str,
                    summary_data.get("trades_executed", 0),
                    summary_data.get("win_count", 0),
                    summary_data.get("loss_count", 0),
                    summary_data.get("total_pnl", 0),
                    summary_data.get("win_rate", 0),
                    summary_data.get("avg_confidence", 0),
                    insights_json, now,
                ),
            )
        await db.commit()
        return {"date": date_str, **summary_data}
    finally:
        await db.close()


async def get_daily_summary(date_str: str | None = None) -> dict[str, Any] | None:
    db = await get_db()
    try:
        if date_str:
            rows = await db.execute_fetchall(
                "SELECT * FROM daily_summaries WHERE date = ?", (date_str,),
            )
        else:
            rows = await db.execute_fetchall(
                "SELECT * FROM daily_summaries ORDER BY date DESC LIMIT 1",
            )
        if not rows:
            return None
        d = dict(rows[0])
        d["insights"] = json.loads(d.get("insights", "[]"))
        return d
    finally:
        await db.close()
