from datetime import datetime
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from sma_graph import run_sma_workflow
from truth_graph import run_daily_truth_summary, run_truth_workflow
from trading_graph import run_trading_workflow


app = FastAPI(title="GDGOC Suffa API", version="0.1.0")


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    timeframe: str = Field(default="swing", examples=["intraday", "swing"])
    market_context: str = Field(
        default="No additional market context provided.",
        examples=["RSI is cooling while sentiment remains optimistic."],
    )


class SmaAnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])


class TruthSignalRequest(BaseModel):
    source: Literal["x", "truth_social", "truth", "truthsocial", "twitter", "other"] = (
        "x"
    )
    author: str = Field(..., examples=["Donald Trump"])
    content: str = Field(
        ...,
        examples=[
            "BREAKING: Donald Trump announces higher tariffs on imported EV batteries effective immediately.",
        ],
    )
    symbol: str = Field(..., examples=["TSLA"])
    agent_id: str = Field(..., examples=["agent-alpha"])
    total_capital: float = Field(..., gt=0, examples=[500000])
    allocated_capital: float = Field(..., gt=0, examples=[50000])
    used_capital: float = Field(default=0, ge=0, examples=[12000])
    autonomous_mode: bool = Field(default=False)
    autonomous_min_confidence: int = Field(default=85, ge=60, le=100)
    max_position_fraction: float = Field(default=0.2, gt=0, le=1)


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
    date: str | None = Field(default=None, examples=["2026-04-24"])
    records: list[TruthSummaryRecord] = Field(default_factory=list)


@app.get("/")
async def root():
    return {
        "message": "GDGOC Suffa backend is running.",
        "system": "Multi-agent trading analysis starter built with FastAPI and LangGraph.",
        "available_workflows": [
            "POST /analysis/basic",
            "POST /analysis/sma",
            "POST /truth/analyze",
            "POST /truth/summary/daily",
        ],
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.post("/analysis/basic")
async def basic_analysis(payload: AnalysisRequest):
    result = run_trading_workflow(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        market_context=payload.market_context,
    )
    return result


@app.post("/analysis/sma")
async def sma_analysis(payload: SmaAnalysisRequest):
    return run_sma_workflow(symbol=payload.symbol)


@app.post("/truth/analyze")
async def truth_analysis(payload: TruthSignalRequest):
    return run_truth_workflow(
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


@app.post("/truth/summary/daily")
async def truth_daily_summary(payload: DailyTruthSummaryRequest):
    records = [record.model_dump() for record in payload.records]
    return run_daily_truth_summary(records=records, summary_date=payload.date)
