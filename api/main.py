from fastapi import FastAPI
from pydantic import BaseModel, Field

from trading_graph import run_trading_workflow


app = FastAPI(title="GDGOC Suffa API", version="0.1.0")


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    timeframe: str = Field(default="swing", examples=["intraday", "swing"])
    market_context: str = Field(
        default="No additional market context provided.",
        examples=["RSI is cooling while sentiment remains optimistic."],
    )


@app.get("/")
async def root():
    return {
        "message": "GDGOC Suffa backend is running.",
        "system": "Multi-agent trading analysis starter built with FastAPI and LangGraph.",
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
