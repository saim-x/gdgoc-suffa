"""Shared state contracts for multi-agent workflows."""

from typing import TypedDict

from .schemas import AgentError, AgentResult, CandidateIdea, MarketSignal, OpportunityRecommendation


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
