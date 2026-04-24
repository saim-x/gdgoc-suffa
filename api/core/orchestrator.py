"""
Top-level orchestration: manages the baton-passing between agents.

WHAT THIS MODULE DOES
─────────────────────
The orchestrator doesn't DO analysis — it COORDINATES.  Think of it
as a relay-race referee:

  1. Hands the baton to Agent A (technical / perception)
  2. Records what Agent A produced
  3. Hands the baton (now enriched) to Agent B (sentiment / context)
  4. Records what Agent B produced, including what it read from Agent A
  5. Hands the enriched baton to Agent C (risk / decision)
  6. Collects the final recommendation

STATE-MACHINE FORMALISM
───────────────────────
                ┌──────────┐
                │  START    │
                └────┬─────┘
                     │
              ┌──────▼──────┐
              │  technical   │  ← perception phase
              │  (Agent A)   │
              └──────┬──────┘
                     │  handoff: technical → sentiment
              ┌──────▼──────┐
              │  sentiment   │  ← context phase
              │  (Agent B)   │
              └──────┬──────┘
                     │  handoff: sentiment → risk
              ┌──────▼──────┐
              │    risk      │  ← decision phase
              │  (Agent C)   │
              └──────┬──────┘
                     │  handoff: risk → orchestrator
              ┌──────▼──────┐
              │  aggregate   │  ← final recommendation
              └──────┬──────┘
                     │
                ┌────▼─────┐
                │   END     │
                └──────────┘

Each transition appends an AgentHandoff to the handoff_log,
creating a full audit trail of the pipeline.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .schemas import AgentError, AgentHandoff, AgentResult
from .state import AgentStatus, OrchestratorState


# ---------------------------------------------------------------------------
# State initialization
# ---------------------------------------------------------------------------

def create_initial_state(
    ticker: str,
    user_profile: dict | None = None,
    portfolio_context: dict | None = None,
) -> OrchestratorState:
    """
    Create a fresh OrchestratorState for a new analysis run.

    This is the starting state S₀ of the state machine.
    All agent slices are initialized to "pending" with empty results.
    """
    now = datetime.now(timezone.utc).isoformat()
    session_id = str(uuid4())

    empty_result: AgentResult = {
        "status": "pending",
        "signal": "insufficient_data",
        "confidence": 0.0,
        "summary": "",
        "metrics": {},
        "details": {},
        "warnings": [],
    }

    initial_status = {
        "technical": AgentStatus(
            agent_id="technical",
            phase="perception",
            status="pending",
            last_updated=now,
            result=empty_result,
        ),
        "sentiment": AgentStatus(
            agent_id="sentiment",
            phase="context",
            status="pending",
            last_updated=now,
            result=empty_result,
        ),
        "risk": AgentStatus(
            agent_id="risk",
            phase="decision",
            status="pending",
            last_updated=now,
            result=empty_result,
        ),
    }

    return OrchestratorState(
        session_id=session_id,
        ticker=ticker.strip().upper(),
        run_timestamp=now,
        technical=empty_result,
        sentiment=empty_result,
        fundamental=empty_result,
        risk=empty_result,
        agent_statuses=initial_status,
        handoff_log=[],
        user_profile=user_profile or {},
        portfolio_context=portfolio_context or {},
        market_signals=[],
        candidate_symbols=[],
        final_recommendation={},
        errors=[],
        metadata={"orchestrator_version": "0.1.0"},
    )


# ---------------------------------------------------------------------------
# Baton-pass (the core handoff function)
# ---------------------------------------------------------------------------

def handoff(
    state: OrchestratorState,
    from_agent: str,
    to_agent: str,
    result: AgentResult,
    phase: str = "perception",
) -> OrchestratorState:
    """
    Execute a baton-pass: record an agent's result and hand off to
    the next agent in the pipeline.

    This is the transition function δ(S, I) of the state machine:
      1. Write the result into the from_agent's slice
      2. Update the from_agent's status to "completed"
      3. Create an AgentHandoff envelope with a context_snapshot
      4. Append the handoff to the log
      5. Return the updated state

    The context_snapshot captures what the RECEIVING agent will see —
    essentially a summary of all completed agents' signals at this
    point in time.  This is critical for freshness tracking.
    """
    now = datetime.now(timezone.utc).isoformat()

    # 1. Write result into the sender's slice
    state[from_agent] = result  # type: ignore[literal-required]

    # 2. Update sender's status
    statuses = state.get("agent_statuses", {})
    statuses[from_agent] = AgentStatus(
        agent_id=from_agent,
        phase=phase,  # type: ignore[arg-type]
        status="completed",
        last_updated=now,
        result=result,
    )
    state["agent_statuses"] = statuses

    # 3. Build the context snapshot for the receiver
    #    (what the downstream agent will "see" when it starts)
    context_snapshot: dict[str, Any] = {
        "ticker": state.get("ticker", ""),
        "completed_agents": {},
    }
    for agent_id, agent_status in statuses.items():
        if agent_status.get("status") == "completed":
            agent_result = agent_status.get("result", {})
            context_snapshot["completed_agents"][agent_id] = {
                "signal": agent_result.get("signal", "insufficient_data"),
                "confidence": agent_result.get("confidence", 0.0),
                "summary": agent_result.get("summary", "")[:200],
            }

    # 4. Create the handoff envelope
    handoff_entry = AgentHandoff(
        from_agent=from_agent,
        to_agent=to_agent,
        phase=phase,  # type: ignore[arg-type]
        timestamp=now,
        payload=result,
        context_snapshot=context_snapshot,
    )

    # 5. Append to log (immutable-style: create a new list)
    log = list(state.get("handoff_log", []))
    log.append(handoff_entry)
    state["handoff_log"] = log

    return state


# ---------------------------------------------------------------------------
# Error recording
# ---------------------------------------------------------------------------

def record_error(
    state: OrchestratorState,
    agent_id: str,
    message: str,
    scope: str = "orchestration",
) -> OrchestratorState:
    """
    Record an agent error into the state.  The agent's status is
    set to "failed" and an AgentError is appended to the errors list.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Update agent status
    statuses = state.get("agent_statuses", {})
    statuses[agent_id] = AgentStatus(
        agent_id=agent_id,
        phase="perception",  # default; callers can override
        status="failed",
        last_updated=now,
        result=AgentResult(
            status="failed",
            signal="insufficient_data",
            confidence=0.0,
            summary=f"Agent failed: {message}",
            metrics={},
            details={},
            warnings=[],
        ),
        error=AgentError(agent=agent_id, scope=scope, message=message),
    )
    state["agent_statuses"] = statuses

    # Append to errors list
    errors = list(state.get("errors", []))
    errors.append(AgentError(agent=agent_id, scope=scope, message=message))
    state["errors"] = errors

    return state


# ---------------------------------------------------------------------------
# Final aggregation
# ---------------------------------------------------------------------------

def aggregate_recommendation(state: OrchestratorState) -> OrchestratorState:
    """
    The output function λ(S) of the state machine.

    Reads all completed agent slices and produces a final
    recommendation by weighted signal fusion.

    Signal fusion logic:
      1. Collect all completed agents' signals and confidences
      2. Score: bullish = +1, bearish = -1, neutral = 0
      3. Weighted average = Σ(score × confidence) / Σ(confidence)
      4. Map back to a signal: > 0.2 → bullish, < -0.2 → bearish, else neutral
      5. Overall confidence = mean of individual confidences

    This is analogous to ensemble averaging in ML —
    each agent is a "weak learner" and the orchestrator
    fuses their predictions with confidence weighting.
    """
    signal_scores = {"bullish": 1.0, "bearish": -1.0, "neutral": 0.0, "mixed": 0.0}
    agent_slices = ["technical", "sentiment", "fundamental", "risk"]

    weighted_sum = 0.0
    total_weight = 0.0
    contributing_agents: list[str] = []
    signals_used: list[dict] = []

    for agent_id in agent_slices:
        result: AgentResult = state.get(agent_id, {})  # type: ignore[assignment]
        if result.get("status") != "completed":
            continue

        signal = result.get("signal", "insufficient_data")
        confidence = float(result.get("confidence", 0.0))

        if signal in signal_scores and confidence > 0:
            score = signal_scores[signal]
            weighted_sum += score * confidence
            total_weight += confidence
            contributing_agents.append(agent_id)
            signals_used.append({
                "agent": agent_id,
                "signal": signal,
                "confidence": confidence,
                "weight_contribution": round(score * confidence, 4),
            })

    # Compute composite
    if total_weight > 0:
        composite = weighted_sum / total_weight
        overall_confidence = total_weight / len(contributing_agents)
    else:
        composite = 0.0
        overall_confidence = 0.0

    # Map composite score to final signal
    if composite > 0.2:
        final_signal = "bullish"
    elif composite < -0.2:
        final_signal = "bearish"
    else:
        final_signal = "neutral"

    state["final_recommendation"] = {
        "signal": final_signal,
        "composite_score": round(composite, 4),
        "overall_confidence": round(overall_confidence, 4),
        "contributing_agents": contributing_agents,
        "signals_used": signals_used,
        "recommendation": _generate_recommendation_text(
            final_signal, composite, overall_confidence, contributing_agents
        ),
    }

    return state


def _generate_recommendation_text(
    signal: str,
    composite: float,
    confidence: float,
    agents: list[str],
) -> str:
    """Generate a human-readable recommendation summary."""
    agent_list = ", ".join(agents) if agents else "none"
    strength = "strong" if abs(composite) > 0.6 else "moderate" if abs(composite) > 0.3 else "weak"

    return (
        f"Based on {len(agents)} contributing agent(s) ({agent_list}), "
        f"the overall signal is {strength} {signal} "
        f"(composite score: {composite:+.2f}, "
        f"confidence: {confidence:.0%})."
    )


# ---------------------------------------------------------------------------
# Pipeline runner (ties it all together)
# ---------------------------------------------------------------------------

def run_orchestration(
    ticker: str,
    agent_results: dict[str, AgentResult],
    user_profile: dict | None = None,
    portfolio_context: dict | None = None,
) -> OrchestratorState:
    """
    Run the full orchestration pipeline with pre-computed agent results.

    This is the "synchronous" mode — useful when agent results have
    already been computed (e.g. by the existing graph workflows) and
    you just need the orchestrator to fuse them.

    For the LangGraph-based async mode, see build_orchestrator_graph().

    Parameters
    ----------
    ticker : str
        The symbol under analysis (e.g. "AAPL").
    agent_results : dict[str, AgentResult]
        Pre-computed results keyed by agent_id.
        Expected keys: "technical", "sentiment", "fundamental", "risk"
        (any subset is fine — missing agents are skipped).
    user_profile : dict, optional
        User profile context.
    portfolio_context : dict, optional
        Portfolio/capital context.

    Returns
    -------
    OrchestratorState
        The final state with all handoffs recorded and a
        final_recommendation computed.
    """
    state = create_initial_state(ticker, user_profile, portfolio_context)

    # Define the pipeline order — this is the baton relay sequence
    pipeline = [
        ("technical", "sentiment", "perception"),
        ("sentiment", "risk", "context"),
        ("risk", "orchestrator", "decision"),
    ]

    for from_agent, to_agent, phase in pipeline:
        result = agent_results.get(from_agent)
        if result is not None:
            state = handoff(state, from_agent, to_agent, result, phase)

    # Handle fundamental if provided (runs in parallel conceptually)
    fundamental_result = agent_results.get("fundamental")
    if fundamental_result is not None:
        state = handoff(state, "fundamental", "risk", fundamental_result, "context")

    # Aggregate final recommendation
    state = aggregate_recommendation(state)

    return state
