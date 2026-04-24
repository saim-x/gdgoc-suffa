"""Shared schema definitions for agent inputs and outputs."""

from typing import Literal, TypedDict


SignalValue = Literal["bullish", "bearish", "neutral", "mixed", "insufficient_data"]
StatusValue = Literal["pending", "completed", "failed", "skipped"]


class AgentError(TypedDict, total=False):
    agent: str
    scope: str
    message: str


class AgentResult(TypedDict, total=False):
    status: StatusValue
    signal: SignalValue
    confidence: float
    summary: str
    metrics: dict
    details: dict
    warnings: list[str]


class MarketSignal(TypedDict, total=False):
    source: str
    topic: str
    signal: SignalValue
    confidence: float
    summary: str
    affected_sectors: list[str]
    affected_symbols: list[str]
    details: dict


class CandidateIdea(TypedDict, total=False):
    symbol: str
    source_agents: list[str]
    why_selected: str
    priority: float


class OpportunityRecommendation(TypedDict, total=False):
    symbol: str
    composite_score: float
    recommended_action: str
    thesis: str
    supporting_agents: list[str]


# ---------------------------------------------------------------------------
# Multi-agent communication contracts (added by feature/multi-agent-comms)
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

Conceptually maps to a perception-cognition-action loop:
  perception  →  the agent observes raw market data
  context     →  the agent enriches with external signals
  scoring     →  the agent ranks / scores the opportunity
  decision    →  the agent decides what action to take
  execution   →  the agent carries out the action
"""


class AgentHandoff(TypedDict, total=False):
    """
    A timestamped envelope recording one agent handing structured
    data to the next agent in the pipeline.

    Think of it as the *message* in a message-passing system:
    it contains WHO sent it, WHO receives it, WHAT was sent
    (the AgentResult payload), and WHAT the sender was looking
    at when it made its decision (context_snapshot).

    The context_snapshot is critical for downstream agents to
    assess signal freshness — e.g. "was the sentiment signal
    computed before or after the price spike?"
    """
    from_agent: str             # e.g. "technical", "sentiment", "risk"
    to_agent: str               # e.g. "sentiment", "risk", "orchestrator"
    phase: PhaseValue           # which cognitive stage produced this
    timestamp: str              # ISO 8601 (e.g. "2026-04-24T22:00:00Z")
    payload: AgentResult        # the structured data being handed off
    context_snapshot: dict      # what the sender "saw" when it decided

