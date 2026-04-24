"""
Adapter functions: translate domain-specific agent outputs into the
shared AgentResult contract.

WHY ADAPTERS?
─────────────
Each teammate's workflow (sma_graph, trading_graph, truth_graph) returns
data in its own shape.  The orchestrator needs a uniform format so agents
can read each other's outputs without knowing internal details.

Think of these as "embedding projectors" in multi-modal ML:
  • A text encoder produces a 768-dim vector
  • An image encoder produces a 512-dim vector
  • To fuse them, you project both into a shared 256-dim space

Same idea here: each adapter projects a domain-specific output dict
into the shared AgentResult space.

DESIGN RULES
────────────
1. Adapters are PURE FUNCTIONS — no side effects, no mutations.
2. They never modify the original dict; they create a new AgentResult.
3. Confidence is normalized to float 0.0–1.0 (the shared standard).
4. The original domain output is preserved in AgentResult["details"]
   for full traceability.
"""

from .schemas import AgentResult, SignalValue


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_signal(raw: str) -> SignalValue:
    """
    Map a raw signal string from any workflow into the shared
    SignalValue vocabulary.

    The existing workflows use slightly different vocabularies:
      • sma_graph / truth_graph  →  "bullish" | "bearish" | "neutral"
      • trading_graph            →  free-text (needs LLM post-processing)

    This function handles the structured cases.  Free-text signals
    default to "insufficient_data" until an LLM classifier is added.
    """
    normalized = raw.strip().lower()
    valid: dict[str, SignalValue] = {
        "bullish": "bullish",
        "bearish": "bearish",
        "neutral": "neutral",
        "mixed": "mixed",
    }
    return valid.get(normalized, "insufficient_data")


def _clamp_confidence(value: float, source_min: float, source_max: float) -> float:
    """
    Normalize a confidence value from [source_min, source_max] to [0.0, 1.0].

    Example: truth_graph gives confidence as int 0–100.
             _clamp_confidence(85, 0, 100)  →  0.85
    """
    if source_max == source_min:
        return 0.0
    normalized = (value - source_min) / (source_max - source_min)
    return max(0.0, min(1.0, round(normalized, 4)))


# ---------------------------------------------------------------------------
# SMA Workflow → AgentResult
# ---------------------------------------------------------------------------

def adapt_sma_to_agent_result(sma_output: dict) -> AgentResult:
    """
    Translate the output of run_sma_workflow() into an AgentResult.

    SMA workflow output shape (from sma_graph.py):
    {
        "workflow": "sma_20_single_stock",
        "agents": [...],
        "symbol": "AAPL",
        "candles_analyzed": 63,
        "latest_close": 175.50,
        "sma_20": 172.30,
        "signal": "bullish",
        "reason": "Price is 3.2 above the 20-day SMA..."
    }

    Confidence heuristic: we derive confidence from the magnitude
    of the price-vs-SMA deviation.  A price 5%+ above SMA → high
    confidence bullish; sitting right on it → low confidence.
    """
    latest_close = float(sma_output.get("latest_close", 0.0))
    sma_20 = float(sma_output.get("sma_20", 0.0))

    # Derive a confidence proxy from price-SMA deviation
    if sma_20 > 0:
        deviation_pct = abs(latest_close - sma_20) / sma_20
        # Map 0–5% deviation to 0.3–0.9 confidence range
        confidence = min(0.9, 0.3 + (deviation_pct * 12.0))
    else:
        confidence = 0.0

    return AgentResult(
        status="completed",
        signal=_normalize_signal(sma_output.get("signal", "")),
        confidence=round(confidence, 4),
        summary=sma_output.get("reason", ""),
        metrics={
            "latest_close": latest_close,
            "sma_20": sma_20,
            "candles_analyzed": sma_output.get("candles_analyzed", 0),
            "deviation_pct": round(deviation_pct, 4) if sma_20 > 0 else 0.0,
        },
        details={"source_workflow": "sma_20_single_stock", "raw_output": sma_output},
        warnings=[],
    )


# ---------------------------------------------------------------------------
# Trading Workflow → AgentResult
# ---------------------------------------------------------------------------

def adapt_trading_to_agent_result(trading_output: dict) -> AgentResult:
    """
    Translate the output of run_trading_workflow() into an AgentResult.

    Trading workflow output shape (from trading_graph.py):
    {
        "symbol": "AAPL",
        "timeframe": "swing",
        "market_context": "...",
        "technical_view": "... (free text from LLM) ...",
        "sentiment_view": "... (free text from LLM) ...",
        "final_signal": "Bias: bullish\\nConfidence: high\\n..."
    }

    NOTE: The trading graph produces FREE-TEXT LLM output.
    We cannot reliably extract a structured signal without an
    additional LLM classification step.  For now, we mark the
    signal as "insufficient_data" and store the raw views.
    A future enhancement can add a classifier node.
    """
    final_signal = trading_output.get("final_signal", "")

    # Best-effort signal extraction from the LLM's "Bias:" line
    signal: SignalValue = "insufficient_data"
    confidence = 0.5  # default medium confidence for LLM outputs

    final_lower = final_signal.lower()
    if "bias:" in final_lower:
        bias_line = final_lower.split("bias:")[1].split("\n")[0].strip()
        if "bullish" in bias_line:
            signal = "bullish"
        elif "bearish" in bias_line:
            signal = "bearish"
        elif "neutral" in bias_line:
            signal = "neutral"

    if "confidence:" in final_lower:
        conf_line = final_lower.split("confidence:")[1].split("\n")[0].strip()
        if "high" in conf_line or "strong" in conf_line:
            confidence = 0.85
        elif "medium" in conf_line or "moderate" in conf_line:
            confidence = 0.6
        elif "low" in conf_line or "weak" in conf_line:
            confidence = 0.35

    return AgentResult(
        status="completed",
        signal=signal,
        confidence=round(confidence, 4),
        summary=final_signal[:500] if final_signal else "No signal produced.",
        metrics={
            "timeframe": trading_output.get("timeframe", ""),
        },
        details={
            "source_workflow": "multi_agent_trading",
            "technical_view": trading_output.get("technical_view", ""),
            "sentiment_view": trading_output.get("sentiment_view", ""),
            "raw_output": trading_output,
        },
        warnings=(
            ["signal_extracted_from_free_text"]
            if signal != "insufficient_data"
            else ["free_text_output_not_classifiable"]
        ),
    )


# ---------------------------------------------------------------------------
# Truth Workflow → AgentResult
# ---------------------------------------------------------------------------

def adapt_truth_to_agent_result(truth_output: dict) -> AgentResult:
    """
    Translate the output of run_truth_workflow() into an AgentResult.

    Truth workflow output shape (from truth_graph.py):
    {
        "workflow": "truth_signal_router",
        "agent_id": "agent-alpha",
        "source": "x",
        "author": "Donald Trump",
        "symbol": "TSLA",
        "direction": "bearish",
        "confidence_score": 82,         ← int 0–100
        "action": "request_approval",
        "notification_required": true,
        "suggested_position_size": 12500.0,
        "remaining_allocated_capital": 38000.0,
        "decision_rationale": "..."
    }

    Confidence: truth_graph uses int 0–100, we normalize to 0.0–1.0.
    """
    raw_confidence = float(truth_output.get("confidence_score", 0))

    return AgentResult(
        status="completed",
        signal=_normalize_signal(truth_output.get("direction", "")),
        confidence=_clamp_confidence(raw_confidence, 0.0, 100.0),
        summary=truth_output.get("decision_rationale", ""),
        metrics={
            "confidence_score_raw": int(raw_confidence),
            "action": truth_output.get("action", ""),
            "suggested_position_size": truth_output.get("suggested_position_size", 0.0),
            "remaining_capital": truth_output.get("remaining_allocated_capital", 0.0),
            "notification_required": truth_output.get("notification_required", False),
        },
        details={
            "source_workflow": "truth_signal_router",
            "source": truth_output.get("source", ""),
            "author": truth_output.get("author", ""),
            "agent_id": truth_output.get("agent_id", ""),
            "raw_output": truth_output,
        },
        warnings=[],
    )
