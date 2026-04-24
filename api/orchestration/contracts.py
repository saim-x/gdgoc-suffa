"""
Orchestration-local contracts for multi-agent communication.

WHY THIS FILE EXISTS (instead of modifying core/schemas.py)
───────────────────────────────────────────────────────────
To avoid merge conflicts, this module defines all orchestration-
specific types locally.  We IMPORT (read-only) the base types
that teammates defined in core/schemas.py, then EXTEND them here
with our own communication-layer types.

At merge time, these types can be promoted into core/ if the
team agrees.

WHAT WE IMPORT FROM core/schemas.py (read-only)
────────────────────────────────────────────────
  - SignalValue   ("bullish" | "bearish" | "neutral" | ...)
  - StatusValue   ("pending" | "completed" | "failed" | "skipped")
  - AgentResult   (the universal agent output contract)
  - AgentError    (error reporting)
  - MarketSignal  (market-level signal)

WHAT WE DEFINE HERE (orchestration-owned)
─────────────────────────────────────────
  - PhaseValue         cognitive pipeline phases
  - AgentHandoff       message envelope for baton-passing
  - AgentStatus        runtime status of an individual agent
  - OrchestratorState  the master baton (shared state)
"""

import sys
import os
from typing import Literal, TypedDict

# ---------------------------------------------------------------------------
# Import base types from teammates' shared contracts (READ-ONLY).
#
# We add the parent directory to sys.path so we can import from
# api/core/ without modifying its __init__.py or any of its files.
# ---------------------------------------------------------------------------
_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

from core.schemas import (  # noqa: E402
    AgentError,
    AgentResult,
    MarketSignal,
    SignalValue,
    StatusValue,
)


# ---------------------------------------------------------------------------
# Phase vocabulary
# ---------------------------------------------------------------------------

PhaseValue = Literal[
    "perception",   # raw data ingestion & feature extraction
    "context",      # contextual enrichment (sentiment, news, social)
    "scoring",      # confidence / relevance scoring
    "decision",     # action routing (execute / hold / block)
    "execution",    # trade execution & confirmation
]
"""
Cognitive phases of the agent pipeline.

Maps to a perception-cognition-action loop:
  perception  ->  the agent observes raw market data
  context     ->  the agent enriches with external signals
  scoring     ->  the agent ranks / scores the opportunity
  decision    ->  the agent decides what action to take
  execution   ->  the agent carries out the action
"""


# ---------------------------------------------------------------------------
# Handoff envelope
# ---------------------------------------------------------------------------

class AgentHandoff(TypedDict, total=False):
    """
    A timestamped envelope recording one agent handing structured
    data to the next agent in the pipeline.

    Contains WHO sent it, WHO receives it, WHAT was sent (the
    AgentResult payload), and WHAT the sender was looking at when
    it made its decision (context_snapshot).

    The context_snapshot is critical for downstream agents to
    assess signal freshness -- e.g. "was the sentiment signal
    computed before or after the price spike?"
    """
    from_agent: str             # e.g. "technical", "sentiment", "risk"
    to_agent: str               # e.g. "sentiment", "risk", "orchestrator"
    phase: PhaseValue           # which cognitive stage produced this
    timestamp: str              # ISO 8601 (e.g. "2026-04-24T22:00:00Z")
    payload: AgentResult        # the structured data being handed off
    context_snapshot: dict      # what the sender "saw" when it decided


# ---------------------------------------------------------------------------
# Agent runtime status
# ---------------------------------------------------------------------------

class AgentStatus(TypedDict, total=False):
    """
    Runtime status of a single agent within the orchestration.

    Tracks what phase the agent is in, whether it has completed,
    its latest output, and any error it encountered.
    """
    agent_id: str               # e.g. "technical", "sentiment", "risk"
    phase: PhaseValue           # current cognitive phase
    status: StatusValue         # "pending" | "completed" | "failed" | "skipped"
    last_updated: str           # ISO 8601 timestamp
    result: AgentResult         # latest structured output from this agent
    error: AgentError


# ---------------------------------------------------------------------------
# User / Portfolio context (local copies to avoid importing from core/state)
# ---------------------------------------------------------------------------

class UserProfile(TypedDict, total=False):
    """User profile -- mirrors core/state.py but defined locally."""
    starting_balance: float
    currency: str
    risk_level: str
    max_positions: int


class PortfolioContext(TypedDict, total=False):
    """Portfolio context -- mirrors core/state.py but defined locally."""
    cash_available: float
    current_positions: list[dict]
    buying_power: float
    position_sizing_rules: dict


# ---------------------------------------------------------------------------
# The Master Baton
# ---------------------------------------------------------------------------

class OrchestratorState(TypedDict, total=False):
    """
    The master baton -- the single source of truth for the entire
    multi-agent analysis pipeline.

    +-------------------------------------------------------------+
    |  Design Rule: each agent READS the full state but WRITES    |
    |  only to its own designated slice.                          |
    |                                                             |
    |  This is a blackboard architecture -- a shared memory space |
    |  where agents read from and write to designated regions.    |
    +-------------------------------------------------------------+

    State-Machine Compliance
    ------------------------
    Formally, this is a Mealy-machine state vector:
      S  = current OrchestratorState (all agent slices + handoff log)
      I  = a new agent's output (an AgentResult)
      d(S, I) = transition fn (update the relevant slice, append handoff)
      l(S, I) = output fn (check completion -> emit final recommendation)

    The transition function is deterministic: same input on same
    state always produces the same next state.  This makes the
    system testable, reproducible, and debuggable.
    """

    # --- Session identity -------------------------------------------------
    session_id: str                         # unique run identifier
    ticker: str                             # the symbol under analysis
    run_timestamp: str                      # ISO 8601 -- when orchestration started

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
    # "attention history" in a Transformer -- you can trace exactly
    # what each agent saw and when.
    handoff_log: list[AgentHandoff]

    # --- Context ----------------------------------------------------------
    user_profile: UserProfile
    portfolio_context: PortfolioContext
    market_signals: list[MarketSignal]
    candidate_symbols: list[str]

    # --- Final outputs ----------------------------------------------------
    final_recommendation: dict
    errors: list[AgentError]
    metadata: dict
