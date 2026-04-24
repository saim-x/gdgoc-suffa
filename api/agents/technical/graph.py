"""Phase 4 technical analysis graph aligned to shared multi-agent state."""

from typing import TypedDict

import yfinance as yf
from langgraph.graph import END, START, StateGraph

from core.schemas import AgentResult, CandidateIdea
from core.state import SymbolAnalysis


class TechnicalScanResult(TypedDict):
    symbol: str
    latest_close: float
    sma_20: float
    rsi_14: float
    trend_signal: str
    momentum_signal: str
    signal: str
    score: int
    reason: str
    candles_analyzed: int


class TechnicalWatchlistState(TypedDict):
    symbols: list[str]
    raw_price_data: dict[str, list[float]]
    scan_results: list[TechnicalScanResult]
    top_candidates: list[str]


def collect_price_data(state: TechnicalWatchlistState) -> TechnicalWatchlistState:
    raw_price_data: dict[str, list[float]] = {}

    for symbol in state["symbols"]:
        normalized_symbol = symbol.strip().upper()
        history = yf.Ticker(normalized_symbol).history(period="3mo", interval="1d")
        closes = history["Close"].dropna().tolist() if not history.empty else []
        raw_price_data[normalized_symbol] = [float(close) for close in closes]

    state["raw_price_data"] = raw_price_data
    return state


def calculate_rsi(closes: list[float], period: int = 14) -> float:
    deltas = [current - previous for previous, current in zip(closes[:-1], closes[1:])]
    recent_deltas = deltas[-period:]

    gains = [delta for delta in recent_deltas if delta > 0]
    losses = [-delta for delta in recent_deltas if delta < 0]

    average_gain = sum(gains) / period
    average_loss = sum(losses) / period

    if average_loss == 0:
        return 100.0

    rs = average_gain / average_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_sma_signal(state: TechnicalWatchlistState) -> TechnicalWatchlistState:
    scan_results: list[TechnicalScanResult] = []

    for symbol, closes in state["raw_price_data"].items():
        candles_analyzed = len(closes)
        if candles_analyzed < 20:
            scan_results.append(
                {
                    "symbol": symbol,
                    "latest_close": 0.0,
                    "sma_20": 0.0,
                    "rsi_14": 0.0,
                    "trend_signal": "insufficient_data",
                    "momentum_signal": "insufficient_data",
                    "signal": "insufficient_data",
                    "score": 0,
                    "reason": "Not enough daily candle data to compute SMA20 and RSI14.",
                    "candles_analyzed": candles_analyzed,
                }
            )
            continue

        latest_close = round(closes[-1], 2)
        sma_20 = round(sum(closes[-20:]) / 20, 2)
        rsi_14 = calculate_rsi(closes)

        if latest_close > sma_20:
            trend_signal = "bullish"
        elif latest_close < sma_20:
            trend_signal = "bearish"
        else:
            trend_signal = "neutral"

        if rsi_14 >= 70:
            momentum_signal = "bearish"
            momentum_reason = "RSI14 is above 70, which suggests overbought momentum."
        elif rsi_14 <= 30:
            momentum_signal = "bullish"
            momentum_reason = "RSI14 is below 30, which suggests oversold conditions."
        else:
            momentum_signal = "neutral"
            momentum_reason = "RSI14 is between 30 and 70, so momentum is not extreme."

        if trend_signal == "bullish" and momentum_signal != "bearish":
            signal = "bullish"
        elif trend_signal == "bearish" and momentum_signal != "bullish":
            signal = "bearish"
        else:
            signal = "neutral"

        score = 50
        if trend_signal == "bullish":
            score += 30
        elif trend_signal == "bearish":
            score -= 30

        if momentum_signal == "bullish":
            score += 15
        elif momentum_signal == "bearish":
            score -= 15

        score = max(0, min(100, score))

        if trend_signal == "bullish":
            trend_reason = "Price is above the 20-day SMA."
        elif trend_signal == "bearish":
            trend_reason = "Price is below the 20-day SMA."
        else:
            trend_reason = "Price is sitting right on the 20-day SMA."

        reason = f"{trend_reason} {momentum_reason}"

        scan_results.append(
            {
                "symbol": symbol,
                "latest_close": latest_close,
                "sma_20": sma_20,
                "rsi_14": rsi_14,
                "trend_signal": trend_signal,
                "momentum_signal": momentum_signal,
                "signal": signal,
                "score": score,
                "reason": reason,
                "candles_analyzed": candles_analyzed,
            }
        )

    state["scan_results"] = scan_results
    return state


def summarize_watchlist(state: TechnicalWatchlistState) -> TechnicalWatchlistState:
    ranked_results = sorted(
        state["scan_results"],
        key=lambda item: (-item["score"], item["symbol"]),
    )
    state["scan_results"] = ranked_results
    state["top_candidates"] = [
        item["symbol"] for item in ranked_results if item["signal"] == "bullish"
    ][:3]
    return state


def build_technical_agent_result(scan_result: TechnicalScanResult) -> AgentResult:
    confidence = round(scan_result["score"] / 100, 2)
    warnings: list[str] = []

    if scan_result["momentum_signal"] == "bearish":
        warnings.append("Momentum is stretched on RSI14.")
    elif scan_result["momentum_signal"] == "bullish":
        warnings.append("RSI14 suggests oversold conditions.")

    return {
        "status": "completed"
        if scan_result["signal"] != "insufficient_data"
        else "failed",
        "signal": scan_result["signal"],
        "confidence": confidence,
        "summary": scan_result["reason"],
        "metrics": {
            "latest_close": scan_result["latest_close"],
            "sma_20": scan_result["sma_20"],
            "rsi_14": scan_result["rsi_14"],
            "score": scan_result["score"],
            "candles_analyzed": scan_result["candles_analyzed"],
        },
        "details": {
            "trend_signal": scan_result["trend_signal"],
            "momentum_signal": scan_result["momentum_signal"],
        },
        "warnings": warnings,
    }


def build_candidate_idea(scan_result: TechnicalScanResult) -> CandidateIdea:
    return {
        "symbol": scan_result["symbol"],
        "source_agents": ["technical_phase_4"],
        "why_selected": scan_result["reason"],
        "priority": round(scan_result["score"] / 100, 2),
    }


def build_symbol_analysis_map(scan_results: list[TechnicalScanResult]) -> dict[str, SymbolAnalysis]:
    symbol_analyses: dict[str, SymbolAnalysis] = {}

    for scan_result in scan_results:
        symbol_analyses[scan_result["symbol"]] = {
            "technical": build_technical_agent_result(scan_result)
        }

    return symbol_analyses


def build_graph():
    workflow = StateGraph(TechnicalWatchlistState)
    workflow.add_node("collect_price_data", collect_price_data)
    workflow.add_node("compute_sma_signal", compute_sma_signal)
    workflow.add_node("summarize_watchlist", summarize_watchlist)

    workflow.add_edge(START, "collect_price_data")
    workflow.add_edge("collect_price_data", "compute_sma_signal")
    workflow.add_edge("compute_sma_signal", "summarize_watchlist")
    workflow.add_edge("summarize_watchlist", END)

    return workflow.compile()


technical_watchlist_graph = build_graph()


def run_technical_watchlist_scan(symbols: list[str]) -> dict:
    normalized_symbols = [symbol.strip().upper() for symbol in symbols if symbol.strip()]
    result = technical_watchlist_graph.invoke(
        {
            "symbols": normalized_symbols,
            "raw_price_data": {},
            "scan_results": [],
            "top_candidates": [],
        }
    )

    return {
        "workflow": "technical_watchlist_sma_rsi_scan",
        "agent": "technical_phase_4",
        "indicators": ["sma_20", "rsi_14"],
        "top_candidates": result["top_candidates"],
        "candidate_symbols": result["top_candidates"],
        "candidate_ideas": [
            build_candidate_idea(item)
            for item in result["scan_results"]
            if item["symbol"] in result["top_candidates"]
        ],
        "symbol_analyses": build_symbol_analysis_map(result["scan_results"]),
        "results": result["scan_results"],
    }
