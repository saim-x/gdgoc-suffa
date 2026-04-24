"""
Demo server -- standalone FastAPI app for the orchestration layer.

This runs independently from the main API (no modifications to main.py).
Teammates can spin it up and interact with the multi-agent pipeline
through a visual UI or raw API endpoints.

Run:
    cd api
    python -m orchestration.demo

Endpoints:
    GET  /                     Visual demo UI
    POST /api/run-pipeline     Run the mock pipeline, return full state
    POST /api/run-custom       Run with custom agent signals
    GET  /api/contracts        Show the shared contract shapes

No new dependencies -- uses fastapi + uvicorn from requirements.txt.
"""

import json
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .contracts import AgentResult
from .adapters import (
    adapt_sma_to_agent_result,
    adapt_truth_to_agent_result,
    adapt_trading_to_agent_result,
)
from .engine import (
    create_initial_state,
    handoff,
    aggregate_recommendation,
    run_orchestration,
)
from .mock_runner import (
    mock_sma_output,
    mock_trading_output,
    mock_truth_output,
    mock_risk_result,
)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Multi-Agent Orchestration Demo",
    version="0.1.0",
    description="Visual demo of the baton-passing orchestration pipeline.",
)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class PipelineRequest(BaseModel):
    ticker: str = Field(default="TSLA", examples=["TSLA", "AAPL", "NVDA"])


class CustomSignal(BaseModel):
    signal: str = Field(default="bullish", examples=["bullish", "bearish", "neutral"])
    confidence: float = Field(default=0.75, ge=0.0, le=1.0)
    summary: str = Field(default="Mock signal for demo purposes.")


class CustomPipelineRequest(BaseModel):
    ticker: str = Field(default="TSLA")
    technical: CustomSignal = Field(default_factory=CustomSignal)
    sentiment: CustomSignal = Field(default_factory=CustomSignal)
    risk: CustomSignal = Field(default_factory=CustomSignal)


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------

@app.post("/api/run-pipeline")
async def run_pipeline(req: PipelineRequest):
    """Run the mock pipeline with synthetic data and return the full state."""
    ticker = req.ticker.strip().upper()

    # Generate mock outputs from each workflow
    sma_output = mock_sma_output(ticker)
    truth_output = mock_truth_output(ticker)

    # Adapt to shared format
    technical_result = adapt_sma_to_agent_result(sma_output)
    sentiment_result = adapt_truth_to_agent_result(truth_output)
    risk_result = mock_risk_result(ticker)

    # Run orchestration
    state = run_orchestration(
        ticker=ticker,
        agent_results={
            "technical": technical_result,
            "sentiment": sentiment_result,
            "risk": risk_result,
        },
        user_profile={
            "starting_balance": 100000.0,
            "currency": "USD",
            "risk_level": "moderate",
        },
    )

    return _serialize_state(state)


@app.post("/api/run-custom")
async def run_custom_pipeline(req: CustomPipelineRequest):
    """Run the pipeline with custom agent signals (for interactive demo)."""
    ticker = req.ticker.strip().upper()

    def to_agent_result(s: CustomSignal) -> AgentResult:
        return AgentResult(
            status="completed",
            signal=s.signal,
            confidence=s.confidence,
            summary=s.summary,
            metrics={},
            details={"source_workflow": "custom_demo"},
            warnings=[],
        )

    state = run_orchestration(
        ticker=ticker,
        agent_results={
            "technical": to_agent_result(req.technical),
            "sentiment": to_agent_result(req.sentiment),
            "risk": to_agent_result(req.risk),
        },
    )

    return _serialize_state(state)


@app.get("/api/contracts")
async def show_contracts():
    """Return the shape of shared contracts for reference."""
    return {
        "AgentResult": {
            "status": "pending | completed | failed | skipped",
            "signal": "bullish | bearish | neutral | mixed | insufficient_data",
            "confidence": "float 0.0-1.0",
            "summary": "string",
            "metrics": "dict (domain-specific)",
            "details": "dict (raw output for traceability)",
            "warnings": "list[str]",
        },
        "OrchestratorState_slices": [
            "technical",
            "sentiment",
            "fundamental",
            "risk",
        ],
        "PhaseValue": [
            "perception",
            "context",
            "scoring",
            "decision",
            "execution",
        ],
        "confidence_scale": "0.0 = no confidence, 1.0 = maximum confidence",
        "signal_fusion": "confidence-weighted ensemble averaging",
    }


@app.get("/", response_class=HTMLResponse)
async def demo_ui():
    """Serve the visual demo UI."""
    html_path = os.path.join(os.path.dirname(__file__), "demo_ui.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_state(state: dict) -> dict:
    """Make the state JSON-serializable."""
    return json.loads(json.dumps(state, default=str))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    print()
    print("  =============================================")
    print("  |  Multi-Agent Orchestration Demo Server    |")
    print("  |  Open http://localhost:8100 in browser    |")
    print("  =============================================")
    print()
    uvicorn.run(
        "orchestration.demo:app",
        host="0.0.0.0",
        port=8100,
        reload=False,
    )
