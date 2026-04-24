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

