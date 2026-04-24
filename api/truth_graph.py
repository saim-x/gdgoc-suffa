import re
from datetime import datetime, timezone
from statistics import mean
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


SOURCE_WEIGHTS = {
    "x": 14,
    "truth_social": 12,
    "other": 8,
}

AUTHOR_WEIGHTS = {
    "donald trump": 30,
    "realdonaldtrump": 30,
    "federal reserve": 34,
    "white house": 30,
    "sec": 28,
    "treasury": 28,
    "elon musk": 26,
    "nvidia": 22,
    "apple": 20,
    "tesla": 20,
}

BULLISH_TERMS = (
    "beat estimates",
    "approved",
    "deal reached",
    "guidance raised",
    "stimulus",
    "buyback",
    "partnership",
    "rate cut",
    "surplus",
)

BEARISH_TERMS = (
    "tariff",
    "investigation",
    "lawsuit",
    "recall",
    "guidance cut",
    "downgrade",
    "default",
    "bankruptcy",
    "rate hike",
    "sanction",
)

MACRO_TERMS = (
    "fed",
    "inflation",
    "interest rate",
    "treasury",
    "oil",
    "gdp",
    "cpi",
    "jobs report",
    "unemployment",
)

URGENCY_TERMS = (
    "breaking",
    "effective immediately",
    "emergency",
    "just announced",
    "live now",
)


class TruthState(TypedDict):
    source: str
    author: str
    content: str
    symbol: str
    agent_id: str
    total_capital: float
    allocated_capital: float
    used_capital: float
    autonomous_mode: bool
    autonomous_min_confidence: int
    max_position_fraction: float
    direction: str
    confidence_score: int
    action: str
    notification_required: bool
    suggested_position_size: float
    remaining_allocated_capital: float
    source_weight: int
    author_weight: int
    bullish_hits: list[str]
    bearish_hits: list[str]
    macro_hits: list[str]
    urgency_hits: list[str]
    symbol_mentioned: bool
    decision_rationale: str


def _normalize_source(source: str) -> str:
    normalized = source.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in {"truth", "truthsocial", "truth_social"}:
        return "truth_social"
    if normalized in {"twitter", "x"}:
        return "x"
    if normalized not in SOURCE_WEIGHTS:
        return "other"
    return normalized


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _author_weight(author: str) -> int:
    normalized = author.strip().lower()
    for key, weight in AUTHOR_WEIGHTS.items():
        if key in normalized:
            return weight
    return 10


def _hits(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in text]


def validate_truth_inputs(state: TruthState) -> TruthState:
    state["source"] = _normalize_source(state["source"])
    state["symbol"] = state["symbol"].strip().upper()
    state["agent_id"] = state["agent_id"].strip()
    state["author"] = state["author"].strip()
    state["content"] = state["content"].strip()

    if not state["symbol"]:
        raise ValueError("symbol is required for truth analysis.")
    if not state["author"]:
        raise ValueError("author is required for truth analysis.")
    if not state["content"]:
        raise ValueError("content is required for truth analysis.")
    if not state["agent_id"]:
        raise ValueError("agent_id is required for truth analysis.")

    if state["allocated_capital"] > state["total_capital"]:
        raise ValueError("allocated_capital cannot exceed total_capital.")
    if state["used_capital"] > state["allocated_capital"]:
        raise ValueError("used_capital cannot exceed allocated_capital.")

    return state


def extract_signal_features(state: TruthState) -> TruthState:
    text = state["content"].lower()
    symbol = state["symbol"]
    symbol_pattern = re.compile(rf"(?<![A-Za-z0-9])\$?{re.escape(symbol)}(?![A-Za-z0-9])", re.I)

    state["source_weight"] = SOURCE_WEIGHTS[state["source"]]
    state["author_weight"] = _author_weight(state["author"])
    state["bullish_hits"] = _hits(text, BULLISH_TERMS)
    state["bearish_hits"] = _hits(text, BEARISH_TERMS)
    state["macro_hits"] = _hits(text, MACRO_TERMS)
    state["urgency_hits"] = _hits(text, URGENCY_TERMS)
    state["symbol_mentioned"] = bool(symbol_pattern.search(state["content"]))

    if len(state["bullish_hits"]) > len(state["bearish_hits"]):
        state["direction"] = "bullish"
    elif len(state["bearish_hits"]) > len(state["bullish_hits"]):
        state["direction"] = "bearish"
    else:
        state["direction"] = "neutral"

    return state


def score_truth_confidence(state: TruthState) -> TruthState:
    directional_delta = abs(len(state["bullish_hits"]) - len(state["bearish_hits"]))
    directional_volume = len(state["bullish_hits"]) + len(state["bearish_hits"])

    score = (
        18
        + state["source_weight"]
        + state["author_weight"]
        + min(directional_volume * 8, 32)
        + min(directional_delta * 6, 18)
        + min(len(state["macro_hits"]) * 5, 15)
        + min(len(state["urgency_hits"]) * 7, 14)
        + (10 if state["symbol_mentioned"] else 0)
    )

    if state["direction"] == "neutral" and directional_volume == 0:
        score -= 14
    if len(state["content"].split()) < 8:
        score -= 10

    state["confidence_score"] = int(_clamp(score, 0, 100))
    return state


def route_execution(state: TruthState) -> TruthState:
    confidence = state["confidence_score"]
    remaining = round(state["allocated_capital"] - state["used_capital"], 2)
    suggested_fraction = min(
        state["max_position_fraction"],
        0.05 + (confidence / 220),
    )
    suggested_position_size = round(state["allocated_capital"] * suggested_fraction, 2)

    action = "no_action"
    notification_required = False

    if confidence >= 90:
        action = "execute"
    elif 60 <= confidence < 90:
        if state["autonomous_mode"] and confidence >= state["autonomous_min_confidence"]:
            action = "execute"
        else:
            action = "request_approval"
            notification_required = True
    else:
        suggested_position_size = 0.0

    if action == "execute" and suggested_position_size > remaining:
        action = "blocked"
        notification_required = True

    state["action"] = action
    state["notification_required"] = notification_required
    state["remaining_allocated_capital"] = remaining
    state["suggested_position_size"] = suggested_position_size
    return state


def build_truth_rationale(state: TruthState) -> TruthState:
    reasons: list[str] = []

    reasons.append(
        f"Source={state['source']} (weight {state['source_weight']}) and author influence score={state['author_weight']}."
    )
    reasons.append(
        f"Directional read is {state['direction']} with confidence {state['confidence_score']}%."
    )

    if state["bullish_hits"] or state["bearish_hits"]:
        directional_terms = state["bullish_hits"] + state["bearish_hits"]
        reasons.append("Signal keywords: " + ", ".join(directional_terms[:4]) + ".")
    if state["urgency_hits"]:
        reasons.append("Urgency indicators: " + ", ".join(state["urgency_hits"][:3]) + ".")
    if state["macro_hits"]:
        reasons.append("Macro context: " + ", ".join(state["macro_hits"][:3]) + ".")
    if state["symbol_mentioned"]:
        reasons.append(f"Direct mention of {state['symbol']} detected in the post.")

    if state["action"] == "execute":
        reasons.append("Execution approved within configured autonomy and confidence thresholds.")
    elif state["action"] == "request_approval":
        reasons.append("Confidence is medium-tier, so user approval is required.")
    elif state["action"] == "blocked":
        reasons.append("Execution blocked because suggested position exceeds remaining agent allocation.")
    else:
        reasons.append("Confidence is below execution threshold, so no trade is placed.")

    state["decision_rationale"] = " ".join(reasons)
    return state


def build_truth_graph():
    workflow = StateGraph(TruthState)
    workflow.add_node("validate_truth_inputs", validate_truth_inputs)
    workflow.add_node("extract_signal_features", extract_signal_features)
    workflow.add_node("score_truth_confidence", score_truth_confidence)
    workflow.add_node("route_execution", route_execution)
    workflow.add_node("build_truth_rationale", build_truth_rationale)

    workflow.add_edge(START, "validate_truth_inputs")
    workflow.add_edge("validate_truth_inputs", "extract_signal_features")
    workflow.add_edge("extract_signal_features", "score_truth_confidence")
    workflow.add_edge("score_truth_confidence", "route_execution")
    workflow.add_edge("route_execution", "build_truth_rationale")
    workflow.add_edge("build_truth_rationale", END)

    return workflow.compile()


truth_graph = build_truth_graph()


def run_truth_workflow(
    source: str,
    author: str,
    content: str,
    symbol: str,
    agent_id: str,
    total_capital: float,
    allocated_capital: float,
    used_capital: float,
    autonomous_mode: bool,
    autonomous_min_confidence: int,
    max_position_fraction: float,
) -> dict:
    result = truth_graph.invoke(
        {
            "source": source,
            "author": author,
            "content": content,
            "symbol": symbol,
            "agent_id": agent_id,
            "total_capital": total_capital,
            "allocated_capital": allocated_capital,
            "used_capital": used_capital,
            "autonomous_mode": autonomous_mode,
            "autonomous_min_confidence": autonomous_min_confidence,
            "max_position_fraction": max_position_fraction,
            "direction": "neutral",
            "confidence_score": 0,
            "action": "no_action",
            "notification_required": False,
            "suggested_position_size": 0.0,
            "remaining_allocated_capital": 0.0,
            "source_weight": 0,
            "author_weight": 0,
            "bullish_hits": [],
            "bearish_hits": [],
            "macro_hits": [],
            "urgency_hits": [],
            "symbol_mentioned": False,
            "decision_rationale": "",
        }
    )

    return {
        "workflow": "truth_signal_router",
        "agent_id": result["agent_id"],
        "source": result["source"],
        "author": result["author"],
        "symbol": result["symbol"],
        "direction": result["direction"],
        "confidence_score": result["confidence_score"],
        "action": result["action"],
        "notification_required": result["notification_required"],
        "suggested_position_size": result["suggested_position_size"],
        "remaining_allocated_capital": result["remaining_allocated_capital"],
        "decision_rationale": result["decision_rationale"],
    }


def run_daily_truth_summary(records: list[dict], summary_date: str | None = None) -> dict:
    effective_date = summary_date or datetime.now(timezone.utc).date().isoformat()
    executed = [record for record in records if record.get("action") == "execute"]

    total_pnl = round(sum(float(record.get("pnl", 0.0)) for record in executed), 2)
    winners = [record for record in executed if float(record.get("pnl", 0.0)) > 0]
    avg_confidence = (
        round(mean(float(record.get("confidence_score", 0)) for record in records), 2)
        if records
        else 0.0
    )
    win_rate = round((len(winners) / len(executed)) * 100, 2) if executed else 0.0

    by_agent: dict[str, dict] = {}
    for record in executed:
        agent_id = str(record.get("agent_id", "unknown"))
        agent_entry = by_agent.setdefault(
            agent_id,
            {
                "trades_executed": 0,
                "total_pnl": 0.0,
                "avg_confidence": [],
            },
        )
        agent_entry["trades_executed"] += 1
        agent_entry["total_pnl"] += float(record.get("pnl", 0.0))
        agent_entry["avg_confidence"].append(float(record.get("confidence_score", 0)))

    formatted_agents = {}
    for agent_id, data in by_agent.items():
        formatted_agents[agent_id] = {
            "trades_executed": data["trades_executed"],
            "total_pnl": round(data["total_pnl"], 2),
            "avg_confidence": round(mean(data["avg_confidence"]), 2)
            if data["avg_confidence"]
            else 0.0,
        }

    return {
        "date": effective_date,
        "records_analyzed": len(records),
        "trades_executed": len(executed),
        "approval_requests": sum(1 for record in records if record.get("action") == "request_approval"),
        "no_action_count": sum(1 for record in records if record.get("action") == "no_action"),
        "blocked_count": sum(1 for record in records if record.get("action") == "blocked"),
        "average_confidence": avg_confidence,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "by_agent": formatted_agents,
    }
