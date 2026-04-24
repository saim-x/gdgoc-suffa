from fastapi import FastAPI
from pydantic import BaseModel, Field

from core.orchestrator import run_multiagent_workflow
from sma_graph import run_sma_workflow
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


class MultiAgentAnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    timeframe: str = Field(default="swing", examples=["intraday", "swing"])
    market_context: str = Field(
        default="No additional market context provided.",
        examples=["Fed tone is softer while earnings momentum remains strong."],
    )
    risk_level: str = Field(default="medium", examples=["low", "medium", "high"])


@app.get("/")
async def root():
    return {
        "message": "GDGOC Suffa backend is running.",
        "system": "Multi-agent trading analysis starter built with FastAPI and LangGraph.",
        "available_workflows": [
            "POST /analysis/basic",
            "POST /analysis/sma",
            "POST /analysis/multiagent",
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


@app.post("/analysis/multiagent")
async def multiagent_analysis(payload: MultiAgentAnalysisRequest):
    return run_multiagent_workflow(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        market_context=payload.market_context,
        risk_level=payload.risk_level,
    )
