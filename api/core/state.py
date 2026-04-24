"""Shared state contracts for multi-agent workflows."""

from typing import TypedDict

from .schemas import (
    AgentError,
    AgentHandoff,
    AgentResult,
    CandidateIdea,
    MarketSignal,
    OpportunityRecommendation,
    PhaseValue,
    StatusValue,
)


class UserProfile(TypedDict, total=False):
    starting_balance: float
    currency: str
    risk_level: str
    max_positions: int


class PortfolioContext(TypedDict, total=False):
    cash_available: float
    current_positions: list[dict]
    buying_power: float
    position_sizing_rules: dict


class SymbolAnalysis(TypedDict, total=False):
    technical: AgentResult
    fundamental: AgentResult
    sentiment: AgentResult
    risk: AgentResult


class AppState(TypedDict, total=False):
    session_id: str
    user_profile: UserProfile
    portfolio_context: PortfolioContext
    market_signals: list[MarketSignal]
    themes: list[MarketSignal]
    candidate_symbols: list[str]
    candidate_ideas: list[CandidateIdea]
    symbol_analyses: dict[str, SymbolAnalysis]
    ranked_opportunities: list[OpportunityRecommendation]
    allocation_plan: dict
    final_recommendation: dict
    errors: list[AgentError]
    metadata: dict


# ---------------------------------------------------------------------------
# Multi-agent orchestration state (added by feature/multi-agent-comms)
# ---------------------------------------------------------------------------

class AgentStatus(TypedDict, total=False):
    """
    Runtime status of a single agent within the orchestration.

    Tracks what phase the agent is in, whether it has completed,
    its latest output, and any error it encountered.
    """
    agent_id: str                   # e.g. "technical", "sentiment", "risk"
    phase: PhaseValue               # current cognitive phase
    status: StatusValue             # "pending" | "completed" | "failed" | "skipped"
    last_updated: str               # ISO 8601 timestamp
    result: AgentResult             # latest structured output from this agent
    error: AgentError


class OrchestratorState(TypedDict, total=False):
    """
    The master baton — the single source of truth for the entire
    multi-agent analysis pipeline.

    ┌─────────────────────────────────────────────────────────────┐
    │  Design Rule: each agent READS the full state but WRITES   │
    │  only to its own designated slice.                         │
    │                                                            │
    │  This is a blackboard architecture — a shared memory space │
    │  where agents read from and write to designated regions.   │
    └─────────────────────────────────────────────────────────────┘

    State-Machine Compliance
    ────────────────────────
    Formally, this is a Mealy-machine state vector:
      S  = current OrchestratorState (all agent slices + handoff log)
      I  = a new agent's output (an AgentResult)
      δ(S, I) = transition fn (update the relevant slice, append handoff)
      λ(S, I) = output fn (check completion → emit final recommendation)

    The transition function is deterministic: same input on same
    state always produces the same next state.  This makes the
    system testable, reproducible, and debuggable.
    """

    # --- Session identity -------------------------------------------------
    session_id: str                         # unique run identifier
    ticker: str                             # the symbol under analysis
    run_timestamp: str                      # ISO 8601 — when orchestration started

    # --- Agent result slices ----------------------------------------------
    # Each agent owns exactly one slice.  The key names match the
    # domain folders under api/agents/ for consistency.
    technical: AgentResult                  # perception / technical analysis
    sentiment: AgentResult                  # context / sentiment & social signals
    fundamental: AgentResult                # fundamental / financial data
    risk: AgentResult                       # risk assessment / final scoring

    # --- Agent runtime tracking -------------------------------------------
    agent_statuses: dict[str, AgentStatus]  # keyed by agent_id

    # --- Handoff log (append-only) ----------------------------------------
    # Every baton-pass is recorded here.  Think of it as the
    # "attention history" in a Transformer — you can trace exactly
    # what each agent saw and when.
    handoff_log: list[AgentHandoff]

    # --- Inherited context (from AppState) --------------------------------
    user_profile: UserProfile
    portfolio_context: PortfolioContext
    market_signals: list[MarketSignal]
    candidate_symbols: list[str]

    # --- Final outputs ----------------------------------------------------
    final_recommendation: dict
    errors: list[AgentError]
    metadata: dict

