from typing import TypedDict

import yfinance as yf
from langgraph.graph import END, START, StateGraph


class SmaState(TypedDict):
    symbol: str
    latest_close: float
    sma_20: float
    signal: str
    reason: str
    candles_analyzed: int


def data_collector(state: SmaState) -> SmaState:
    history = yf.Ticker(state["symbol"]).history(period="3mo", interval="1d")
    if history.empty:
        raise ValueError(f"No market data found for symbol '{state['symbol']}'.")

    closes = history["Close"].dropna()
    if len(closes) < 20:
        raise ValueError(
            f"Not enough candle data for symbol '{state['symbol']}'. Need at least 20 daily closes."
        )

    state["latest_close"] = round(float(closes.iloc[-1]), 2)
    state["candles_analyzed"] = int(len(closes))
    state["sma_20"] = round(float(closes.tail(20).mean()), 2)
    return state


def sma_analyst(state: SmaState) -> SmaState:
    latest_close = state["latest_close"]
    sma_20 = state["sma_20"]

    if latest_close > sma_20:
        signal = "bullish"
    elif latest_close < sma_20:
        signal = "bearish"
    else:
        signal = "neutral"

    state["signal"] = signal
    return state


def signal_summarizer(state: SmaState) -> SmaState:
    latest_close = state["latest_close"]
    sma_20 = state["sma_20"]
    difference = round(latest_close - sma_20, 2)

    if state["signal"] == "bullish":
        state["reason"] = (
            f"Price is {difference} above the 20-day SMA, which suggests short-term upward momentum."
        )
    elif state["signal"] == "bearish":
        state["reason"] = (
            f"Price is {abs(difference)} below the 20-day SMA, which suggests short-term weakness."
        )
    else:
        state["reason"] = (
            "Price is sitting right on the 20-day SMA, so short-term direction is unclear."
        )

    return state


def build_graph():
    workflow = StateGraph(SmaState)
    workflow.add_node("data_collector", data_collector)
    workflow.add_node("sma_analyst", sma_analyst)
    workflow.add_node("signal_summarizer", signal_summarizer)

    workflow.add_edge(START, "data_collector")
    workflow.add_edge("data_collector", "sma_analyst")
    workflow.add_edge("sma_analyst", "signal_summarizer")
    workflow.add_edge("signal_summarizer", END)

    return workflow.compile()


sma_graph = build_graph()


def run_sma_workflow(symbol: str) -> dict:
    normalized_symbol = symbol.strip().upper()
    result = sma_graph.invoke(
        {
            "symbol": normalized_symbol,
            "latest_close": 0.0,
            "sma_20": 0.0,
            "signal": "",
            "reason": "",
            "candles_analyzed": 0,
        }
    )

    return {
        "workflow": "sma_20_single_stock",
        "agents": [
            "data_collector",
            "sma_analyst",
            "signal_summarizer",
        ],
        "symbol": result["symbol"],
        "candles_analyzed": result["candles_analyzed"],
        "latest_close": result["latest_close"],
        "sma_20": result["sma_20"],
        "signal": result["signal"],
        "reason": result["reason"],
    }
