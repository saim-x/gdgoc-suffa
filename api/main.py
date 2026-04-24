"""
GDGOC Suffa Trading Backend — FastAPI Application

Full REST API for multi-agent trading simulation.
Backward-compatible with existing truth_graph endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Existing graphs (backward compat)
from truth_graph import run_truth_workflow, run_daily_truth_summary
from sma_graph import run_sma_workflow

# New engine
import database as db
from config import DEFAULT_WATCHLIST
from engine.signal_engine import generate_signal, generate_signals_batch
from engine.agent_manager import process_signal_for_agents, approve_pending_trade, reject_pending_trade
from engine.trade_executor import close_trade, get_portfolio_state, build_daily_summary
from engine.scheduler import start_scheduler, stop_scheduler, is_running

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    await db.init_database()
    start_scheduler()
    logger.info("Backend ready.")
    yield
    logger.info("Shutting down...")
    stop_scheduler()


# ── App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="GDGOC Suffa Trading API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request Models ────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    symbol: str = Field(..., examples=["TSLA"])
    context: str = Field(default="", examples=["Recent tariff announcement"])


class BatchAnalyzeRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: DEFAULT_WATCHLIST[:4])
    context: str = Field(default="")


class AgentUpdateRequest(BaseModel):
    name: str | None = None
    assigned_capital: float | None = None
    confidence_threshold: int | None = None
    status: str | None = None


class AutonomousToggleRequest(BaseModel):
    enabled: bool = Field(..., examples=[True])


class RiskLevelRequest(BaseModel):
    level: Literal["low", "medium", "high"] = Field(..., examples=["medium"])


# Legacy models (backward compat)
class TruthSignalRequest(BaseModel):
    source: Literal["x", "truth_social", "truth", "truthsocial", "twitter", "other"] = "x"
    author: str = Field(..., examples=["Donald Trump"])
    content: str = Field(..., examples=["BREAKING: Higher tariffs on EV batteries."])
    symbol: str = Field(..., examples=["TSLA"])
    agent_id: str = Field(..., examples=["agent-orion"])
    total_capital: float = Field(..., gt=0, examples=[500000])
    allocated_capital: float = Field(..., gt=0, examples=[50000])
    used_capital: float = Field(default=0, ge=0, examples=[12000])
    autonomous_mode: bool = Field(default=False)
    autonomous_min_confidence: int = Field(default=85, ge=60, le=100)
    max_position_fraction: float = Field(default=0.2, gt=0, le=1)


class SmaAnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])


class TruthSummaryRecord(BaseModel):
    agent_id: str
    symbol: str
    source: str
    confidence_score: int = Field(..., ge=0, le=100)
    action: Literal["execute", "request_approval", "no_action", "blocked"]
    rationale: str
    pnl: float = 0.0
    executed_at: datetime
    position_size: float = Field(default=0.0, ge=0)


class DailyTruthSummaryRequest(BaseModel):
    date: str | None = Field(default=None, examples=["2026-04-25"])
    records: list[TruthSummaryRecord] = Field(default_factory=list)


# ── Health & Root ─────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "GDGOC Suffa trading backend is running.",
        "version": "1.0.0",
        "scheduler_active": is_running(),
        "endpoints": {
            "signals": "GET /signals",
            "agents": "GET /agents",
            "portfolio": "GET /portfolio",
            "trades": "GET /trades",
            "activity": "GET /activity",
            "pending": "GET /pending",
            "analyze": "POST /analyze/{symbol}",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "ok", "scheduler": is_running()}


# ── Signals ───────────────────────────────────────────────────────────

@app.get("/signals")
async def list_signals(
    asset: str | None = Query(None, description="Filter by asset symbol"),
    limit: int = Query(50, ge=1, le=200),
):
    """List recent signals with optional asset filter."""
    signals = await db.get_signals(limit=limit, asset=asset)
    return {"signals": signals, "count": len(signals)}


@app.post("/analyze-batch")
async def analyze_batch(payload: BatchAnalyzeRequest):
    """Trigger analysis for multiple symbols."""
    try:
        signals = await generate_signals_batch(payload.symbols, payload.context)
        all_actions = []
        for signal in signals:
            actions = await process_signal_for_agents(signal)
            all_actions.extend(actions)
        return {
            "signals": signals,
            "agent_actions": all_actions,
            "count": len(signals),
        }
    except Exception as exc:
        logger.error("Batch analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze/{symbol}")
async def analyze_symbol(symbol: str, payload: AnalyzeRequest | None = None):
    """
    Trigger full analysis pipeline for a symbol.
    Runs SMA + RSI + Sentiment → aggregate → feed to agents.
    """
    try:
        context = payload.context if payload else ""
        signal = await generate_signal(symbol.strip().upper(), context)
        agent_actions = await process_signal_for_agents(signal)
        return {
            "signal": signal,
            "agent_actions": agent_actions,
        }
    except Exception as exc:
        logger.error("Analysis failed for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Agents ────────────────────────────────────────────────────────────

@app.get("/agents")
async def list_agents():
    """List all agents with current state."""
    agents = await db.get_agents()
    return {"agents": agents, "count": len(agents)}


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    agent = await db.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdateRequest):
    """Update an agent's config."""
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    agent = await db.update_agent(agent_id, **fields)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ── Portfolio ─────────────────────────────────────────────────────────

@app.get("/portfolio")
async def get_portfolio():
    """Get complete portfolio state with live P&L."""
    return await get_portfolio_state()


@app.post("/settings/autonomous")
async def toggle_autonomous(payload: AutonomousToggleRequest):
    """Toggle autonomous execution mode."""
    await db.update_portfolio(autonomous_mode=int(payload.enabled))
    return {"autonomous_mode": payload.enabled}


@app.post("/settings/risk")
async def set_risk_level(payload: RiskLevelRequest):
    """Set the portfolio risk level."""
    await db.update_portfolio(risk_level=payload.level)
    return {"risk_level": payload.level}


# ── Trades ────────────────────────────────────────────────────────────

@app.get("/trades")
async def list_trades(
    status: str | None = Query(None, description="Filter: open, closed"),
    agent_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List trades with optional filters."""
    trades = await db.get_trades(status=status, agent_id=agent_id, limit=limit)
    return {"trades": trades, "count": len(trades)}


@app.get("/trades/active")
async def get_active_trades():
    """Get currently open trades with live P&L."""
    portfolio = await get_portfolio_state()
    return {"trades": portfolio["active_positions"], "count": portfolio["position_count"]}


@app.post("/trades/{trade_id}/close")
async def close_trade_endpoint(trade_id: str):
    """Close an open trade at current market price."""
    result = await close_trade(trade_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trade not found or already closed")
    return result


# ── Pending Approvals ─────────────────────────────────────────────────

@app.get("/pending")
async def list_pending():
    """List pending trade approvals."""
    pending = await db.get_pending()
    return {"pending": pending, "count": len(pending)}


@app.post("/pending/{pending_id}/approve")
async def approve_trade(pending_id: str):
    """Approve a pending trade — executes immediately."""
    result = await approve_pending_trade(pending_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pending trade not found or already resolved")
    return result


@app.post("/pending/{pending_id}/reject")
async def reject_trade(pending_id: str):
    """Reject a pending trade."""
    result = await reject_pending_trade(pending_id)
    if not result:
        raise HTTPException(status_code=404, detail="Pending trade not found or already resolved")
    return result


# ── Activity ──────────────────────────────────────────────────────────

@app.get("/activity")
async def list_activity(
    type: str | None = Query(None, description="Filter: executed, pending, rejected"),
    limit: int = Query(100, ge=1, le=500),
):
    """Activity feed with optional type filter."""
    items = await db.get_activity(type_filter=type, limit=limit)
    return {"activity": items, "count": len(items)}


# ── Daily Summary ─────────────────────────────────────────────────────

@app.get("/summary/daily")
async def get_daily_summary_endpoint(date: str | None = Query(None)):
    """Get the daily trading summary. Generates fresh if not found."""
    existing = await db.get_daily_summary(date)
    if existing:
        return existing
    # Generate on the fly
    return await build_daily_summary(date)


@app.post("/summary/daily")
async def generate_daily_summary(date: str | None = Query(None)):
    """Force-generate a daily summary."""
    return await build_daily_summary(date)


# ── Legacy Endpoints (backward compat) ────────────────────────────────

@app.post("/truth/analyze")
async def truth_analysis(payload: TruthSignalRequest):
    """Legacy truth-layer analysis — kept for frontend compatibility."""
    try:
        result = run_truth_workflow(
            source=payload.source,
            author=payload.author,
            content=payload.content,
            symbol=payload.symbol,
            agent_id=payload.agent_id,
            total_capital=payload.total_capital,
            allocated_capital=payload.allocated_capital,
            used_capital=payload.used_capital,
            autonomous_mode=payload.autonomous_mode,
            autonomous_min_confidence=payload.autonomous_min_confidence,
            max_position_fraction=payload.max_position_fraction,
        )

        # Also persist as a signal in the new system
        direction = result.get("direction", "neutral")
        signal_map = {"bullish": "buy", "bearish": "sell", "neutral": "hold"}
        await db.insert_signal(
            asset=result.get("symbol", payload.symbol),
            signal=signal_map.get(direction, "hold"),
            confidence_score=result.get("confidence_score", 0),
            reasoning=result.get("decision_rationale", ""),
            agent_id=payload.agent_id,
        )

        # Persist activity
        action = result.get("action", "no_action")
        activity_type = "executed" if action == "execute" else ("pending" if action == "request_approval" else "rejected")
        await db.insert_activity(
            type_=activity_type,
            asset=result.get("symbol", payload.symbol),
            confidence=result.get("confidence_score", 0),
            action=signal_map.get(direction, "hold"),
            pnl=0,
            note=result.get("decision_rationale", ""),
            agent_id=payload.agent_id,
        )

        # If execute, create a trade record
        if action == "execute":
            from engine.data_ingest import get_current_price
            from config import TRADE_FEE_RATE, SLIPPAGE_RATE
            price = get_current_price(payload.symbol)
            if price > 0:
                pos_size = result.get("suggested_position_size", 0)
                if pos_size > 0:
                    await db.insert_trade(
                        agent_id=payload.agent_id,
                        asset=payload.symbol,
                        direction=signal_map.get(direction, "hold"),
                        entry_price=price,
                        position_size=pos_size,
                        fee=round(pos_size * TRADE_FEE_RATE, 2),
                        slippage=round(price * SLIPPAGE_RATE, 4),
                        confidence=result.get("confidence_score", 0),
                    )

        # If pending, create a pending approval record
        if action == "request_approval":
            await db.insert_pending(
                agent_id=payload.agent_id,
                asset=payload.symbol,
                direction=signal_map.get(direction, "hold"),
                confidence=result.get("confidence_score", 0),
                position_size=result.get("suggested_position_size", 0),
                rationale=result.get("decision_rationale", ""),
            )

        return result
    except Exception as exc:
        logger.error("Truth analysis failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/truth/summary/daily")
async def truth_daily_summary(payload: DailyTruthSummaryRequest):
    """Legacy daily summary endpoint."""
    records = [record.model_dump() for record in payload.records]
    return run_daily_truth_summary(records=records, summary_date=payload.date)


@app.post("/analysis/sma")
async def sma_analysis(payload: SmaAnalysisRequest):
    """Legacy SMA analysis endpoint."""
    return run_sma_workflow(symbol=payload.symbol)
