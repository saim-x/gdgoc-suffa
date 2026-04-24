import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import END, START, StateGraph


load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))


class TradingState(TypedDict):
    symbol: str
    timeframe: str
    market_context: str
    technical_view: str
    sentiment_view: str
    final_signal: str


def get_llm() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is missing. Add it to api/.env before running analysis.")

    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        api_key=api_key,
        temperature=0.2,
    )


def technical_analyst(state: TradingState) -> TradingState:
    llm = get_llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a technical analyst for a trading desk. "
                    "Give a concise chart-focused view with trend, momentum, "
                    "risk level, and a directional bias."
                )
            ),
            HumanMessage(
                content=(
                    f"Symbol: {state['symbol']}\n"
                    f"Timeframe: {state['timeframe']}\n"
                    f"Market context: {state['market_context']}"
                )
            ),
        ]
    )
    state["technical_view"] = response.content
    return state


def sentiment_analyst(state: TradingState) -> TradingState:
    llm = get_llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are a market sentiment analyst. "
                    "Assess trader psychology, news tone, and crowd positioning. "
                    "Respond briefly and clearly."
                )
            ),
            HumanMessage(
                content=(
                    f"Symbol: {state['symbol']}\n"
                    f"Timeframe: {state['timeframe']}\n"
                    f"Market context: {state['market_context']}"
                )
            ),
        ]
    )
    state["sentiment_view"] = response.content
    return state


def lead_analyst(state: TradingState) -> TradingState:
    llm = get_llm()
    response = llm.invoke(
        [
            SystemMessage(
                content=(
                    "You are the lead trading analyst in a multi-agent system. "
                    "Combine the specialists' views into a single trading signal. "
                    "Return four labeled lines only: Bias, Confidence, Setup, Risk."
                )
            ),
            HumanMessage(
                content=(
                    f"Symbol: {state['symbol']}\n"
                    f"Timeframe: {state['timeframe']}\n"
                    f"Market context: {state['market_context']}\n\n"
                    f"Technical analyst view:\n{state['technical_view']}\n\n"
                    f"Sentiment analyst view:\n{state['sentiment_view']}"
                )
            ),
        ]
    )
    state["final_signal"] = response.content
    return state


def build_graph():
    workflow = StateGraph(TradingState)
    workflow.add_node("technical_analyst", technical_analyst)
    workflow.add_node("sentiment_analyst", sentiment_analyst)
    workflow.add_node("lead_analyst", lead_analyst)

    workflow.add_edge(START, "technical_analyst")
    workflow.add_edge("technical_analyst", "sentiment_analyst")
    workflow.add_edge("sentiment_analyst", "lead_analyst")
    workflow.add_edge("lead_analyst", END)

    return workflow.compile()


trading_graph = build_graph()


def run_trading_workflow(symbol: str, timeframe: str, market_context: str) -> dict:
    result = trading_graph.invoke(
        {
            "symbol": symbol,
            "timeframe": timeframe,
            "market_context": market_context,
            "technical_view": "",
            "sentiment_view": "",
            "final_signal": "",
        }
    )
    return {
        "symbol": result["symbol"],
        "timeframe": result["timeframe"],
        "market_context": result["market_context"],
        "technical_view": result["technical_view"],
        "sentiment_view": result["sentiment_view"],
        "final_signal": result["final_signal"],
    }

