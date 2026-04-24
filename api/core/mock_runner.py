"""
Mock Runner -- test the baton-passing pipeline without real APIs.

PURPOSE
-------
This script simulates the full multi-agent orchestration pipeline
using synthetic (but realistic) data.  It verifies that:

  1. The OrchestratorState initializes correctly
  2. Each agent's handoff writes to the correct slice
  3. The handoff_log records every baton-pass
  4. The final recommendation aggregates all signals correctly
  5. No data is lost between transitions

Run this script standalone:
    cd api
    python -m core.mock_runner

Or import and call run_mock_pipeline() from tests.
"""

import json
import sys
from datetime import datetime, timezone

from .adapters import (
    adapt_sma_to_agent_result,
    adapt_trading_to_agent_result,
    adapt_truth_to_agent_result,
)
from .orchestrator import create_initial_state, handoff, aggregate_recommendation
from .schemas import AgentResult


# ---------------------------------------------------------------------------
# Mock data generators
# ---------------------------------------------------------------------------

def mock_sma_output(ticker: str = "TSLA") -> dict:
    """
    Simulate what run_sma_workflow() would return.
    Scenario: TSLA price is above SMA-20 -> bullish signal.
    """
    return {
        "workflow": "sma_20_single_stock",
        "agents": ["data_collector", "sma_analyst", "signal_summarizer"],
        "symbol": ticker,
        "candles_analyzed": 63,
        "latest_close": 248.50,
        "sma_20": 235.80,
        "signal": "bullish",
        "reason": "Price is 12.7 above the 20-day SMA, which suggests short-term upward momentum.",
    }


def mock_trading_output(ticker: str = "TSLA") -> dict:
    """
    Simulate what run_trading_workflow() would return.
    Scenario: LLM-based analysis gives a moderate bullish signal.
    """
    return {
        "symbol": ticker,
        "timeframe": "swing",
        "market_context": "EV sector momentum accelerating after tariff relief.",
        "technical_view": (
            "RSI is trending upward at 62. MACD crossover confirmed 3 days ago. "
            "Key resistance at $255. Volume profile shows accumulation at $240-$248."
        ),
        "sentiment_view": (
            "Social media sentiment is increasingly bullish on TSLA. "
            "Institutional flow data shows net buying. "
            "Retail trader positioning is overcrowded but not extreme."
        ),
        "final_signal": (
            "Bias: bullish\n"
            "Confidence: moderate\n"
            "Setup: Long entry on pullback to $244-$246 with stop at $238\n"
            "Risk: Medium -- watch for sector rotation and earnings vol"
        ),
    }


def mock_truth_output(ticker: str = "TSLA") -> dict:
    """
    Simulate what run_truth_workflow() would return.
    Scenario: Trump tweets about EV tariff relief -> bullish for TSLA.
    """
    return {
        "workflow": "truth_signal_router",
        "agent_id": "agent-alpha",
        "source": "x",
        "author": "Donald Trump",
        "symbol": ticker,
        "direction": "bullish",
        "confidence_score": 78,
        "action": "request_approval",
        "notification_required": True,
        "suggested_position_size": 15000.0,
        "remaining_allocated_capital": 38000.0,
        "decision_rationale": (
            "Source=x (weight 14) and author influence score=30. "
            "Directional read is bullish with confidence 78%. "
            "Signal keywords: stimulus, deal reached. "
            "Direct mention of TSLA detected in the post. "
            "Confidence is medium-tier, so user approval is required."
        ),
    }


def mock_risk_result(ticker: str = "TSLA") -> AgentResult:
    """
    Create a synthetic risk-agent result.
    Since no risk agent exists yet, this is a pure mock.
    Scenario: moderate risk based on market volatility.
    """
    return AgentResult(
        status="completed",
        signal="bullish",
        confidence=0.65,
        summary=(
            f"Risk assessment for {ticker}: Moderate risk profile. "
            "Position sizing should stay conservative given upcoming earnings. "
            "Max recommended allocation: 3% of portfolio."
        ),
        metrics={
            "risk_level": "moderate",
            "max_allocation_pct": 0.03,
            "volatility_regime": "elevated",
            "days_to_earnings": 18,
        },
        details={"source_workflow": "mock_risk_agent"},
        warnings=["earnings_approaching"],
    )


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

def run_mock_pipeline(
    ticker: str = "TSLA",
    verbose: bool = True,
) -> dict:
    """
    Run the full mock pipeline and return the final OrchestratorState.

    Steps:
      1. Generate mock outputs from each workflow
      2. Adapt them into AgentResult format
      3. Run the orchestration pipeline with baton-passing
      4. Aggregate the final recommendation
      5. Validate state integrity
    """
    if verbose:
        _header("MULTI-AGENT MOCK PIPELINE")
        print(f"  Ticker: {ticker}")
        print(f"  Time:   {datetime.now(timezone.utc).isoformat()}")
        print()

    # -- Step 1: Generate mock workflow outputs ----------------------------
    if verbose:
        _header("STEP 1 -- Generate Mock Workflow Outputs")

    sma_output = mock_sma_output(ticker)
    trading_output = mock_trading_output(ticker)
    truth_output = mock_truth_output(ticker)

    if verbose:
        _print_dict("SMA Workflow Output", sma_output)
        _print_dict("Trading Workflow Output", trading_output)
        _print_dict("Truth Workflow Output", truth_output)

    # -- Step 2: Adapt to shared AgentResult format ------------------------
    if verbose:
        _header("STEP 2 -- Adapt to Shared AgentResult Format")

    technical_result = adapt_sma_to_agent_result(sma_output)
    sentiment_result = adapt_truth_to_agent_result(truth_output)
    risk_result = mock_risk_result(ticker)

    if verbose:
        _print_dict("Technical AgentResult (from SMA)", dict(technical_result))
        _print_dict("Sentiment AgentResult (from Truth)", dict(sentiment_result))
        _print_dict("Risk AgentResult (mock)", dict(risk_result))

    # -- Step 3: Initialize orchestrator state -----------------------------
    if verbose:
        _header("STEP 3 -- Initialize Orchestrator State")

    state = create_initial_state(
        ticker=ticker,
        user_profile={
            "starting_balance": 100000.0,
            "currency": "USD",
            "risk_level": "moderate",
            "max_positions": 5,
        },
        portfolio_context={
            "cash_available": 75000.0,
            "current_positions": [],
            "buying_power": 75000.0,
        },
    )

    if verbose:
        print(f"  Session ID:  {state['session_id']}")
        print(f"  Ticker:      {state['ticker']}")
        print(f"  Timestamp:   {state['run_timestamp']}")
        print(f"  Agents:      {list(state['agent_statuses'].keys())}")
        print()

    # -- Step 4: Execute baton-passing pipeline ----------------------------
    if verbose:
        _header("STEP 4 -- Execute Baton-Passing Pipeline")

    # Handoff 1: Technical -> Sentiment
    if verbose:
        print("  > Handoff 1: technical -> sentiment (phase: perception)")
    state = handoff(state, "technical", "sentiment", technical_result, "perception")
    if verbose:
        _print_handoff(state["handoff_log"][-1])

    # Handoff 2: Sentiment -> Risk
    if verbose:
        print("  > Handoff 2: sentiment -> risk (phase: context)")
    state = handoff(state, "sentiment", "risk", sentiment_result, "context")
    if verbose:
        _print_handoff(state["handoff_log"][-1])

    # Handoff 3: Risk -> Orchestrator
    if verbose:
        print("  > Handoff 3: risk -> orchestrator (phase: decision)")
    state = handoff(state, "risk", "orchestrator", risk_result, "decision")
    if verbose:
        _print_handoff(state["handoff_log"][-1])

    # -- Step 5: Aggregate final recommendation ----------------------------
    if verbose:
        _header("STEP 5 -- Aggregate Final Recommendation")

    state = aggregate_recommendation(state)

    if verbose:
        _print_dict("Final Recommendation", state["final_recommendation"])

    # -- Step 6: Validate state integrity ----------------------------------
    if verbose:
        _header("STEP 6 -- State Integrity Validation")

    validation = _validate_state(state)

    if verbose:
        for check, passed in validation.items():
            icon = "[PASS]" if passed else "[FAIL]"
            print(f"  {icon} {check}")
        print()

        all_passed = all(validation.values())
        if all_passed:
            print("  =============================================")
            print("  |  ALL CHECKS PASSED -- Pipeline is valid   |")
            print("  =============================================")
        else:
            print("  =============================================")
            print("  |  SOME CHECKS FAILED -- Review the output  |")
            print("  =============================================")
            failed = [k for k, v in validation.items() if not v]
            print(f"  Failed: {', '.join(failed)}")
        print()

    return dict(state)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate_state(state: dict) -> dict[str, bool]:
    """Run integrity checks on the final state."""
    checks: dict[str, bool] = {}

    # Check 1: All agent slices populated
    for agent in ["technical", "sentiment", "risk"]:
        result = state.get(agent, {})
        checks[f"{agent}_slice_populated"] = result.get("status") == "completed"

    # Check 2: Handoff log has correct number of entries
    log = state.get("handoff_log", [])
    checks["handoff_log_has_3_entries"] = len(log) == 3

    # Check 3: Handoff log ordering is correct
    if len(log) >= 3:
        checks["handoff_order_correct"] = (
            log[0].get("from_agent") == "technical"
            and log[1].get("from_agent") == "sentiment"
            and log[2].get("from_agent") == "risk"
        )
    else:
        checks["handoff_order_correct"] = False

    # Check 4: Context snapshots accumulate correctly
    if len(log) >= 2:
        second_snapshot = log[1].get("context_snapshot", {})
        completed_in_snapshot = second_snapshot.get("completed_agents", {})
        checks["context_accumulation"] = "technical" in completed_in_snapshot
    else:
        checks["context_accumulation"] = False

    # Check 5: Final recommendation exists and has a signal
    rec = state.get("final_recommendation", {})
    checks["final_recommendation_present"] = (
        "signal" in rec and "composite_score" in rec
    )

    # Check 6: No errors recorded
    checks["no_errors"] = len(state.get("errors", [])) == 0

    # Check 7: Session metadata intact
    checks["session_metadata_intact"] = (
        bool(state.get("session_id"))
        and bool(state.get("ticker"))
        and bool(state.get("run_timestamp"))
    )

    return checks


# ---------------------------------------------------------------------------
# Pretty-printing helpers
# ---------------------------------------------------------------------------

def _header(title: str) -> None:
    width = max(len(title) + 4, 50)
    print()
    print("-" * width)
    print(f"  {title}")
    print("-" * width)
    print()


def _print_dict(label: str, d: dict) -> None:
    print(f"  +-- {label}")
    # Compact JSON, but readable
    formatted = json.dumps(d, indent=4, default=str)
    for line in formatted.split("\n"):
        print(f"  |   {line}")
    print("  +--")
    print()


def _print_handoff(h: dict) -> None:
    print(f"    From:  {h.get('from_agent', '?')}")
    print(f"    To:    {h.get('to_agent', '?')}")
    print(f"    Phase: {h.get('phase', '?')}")
    print(f"    Time:  {h.get('timestamp', '?')}")
    snapshot = h.get("context_snapshot", {})
    completed = snapshot.get("completed_agents", {})
    if completed:
        print("    Context visible to receiver:")
        for agent_id, info in completed.items():
            sig = info.get("signal", "?")
            conf = info.get("confidence", 0)
            print(f"      * {agent_id}: signal={sig}, confidence={conf:.2f}")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "TSLA"
    run_mock_pipeline(ticker=ticker, verbose=True)
