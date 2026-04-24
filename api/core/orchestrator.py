"""Top-level orchestration entry points for agent coordination."""

from __future__ import annotations

from agents.fundamental.graph import run_fundamental_analysis
from agents.sentiment.graph import run_sentiment_analysis
from agents.technical.graph import run_technical_analysis

from .schemas import AgentError, AgentResult


_SIGNAL_TO_SCORE = {
	"bullish": 1.0,
	"neutral": 0.0,
	"mixed": 0.0,
	"bearish": -1.0,
	"insufficient_data": 0.0,
}


def _safe_run(agent_name: str, fn, *args, **kwargs) -> tuple[AgentResult, AgentError | None]:
	try:
		return fn(*args, **kwargs), None
	except Exception as exc:  # pragma: no cover - external API failures are non-deterministic
		return (
			{
				"status": "failed",
				"signal": "insufficient_data",
				"confidence": 0.0,
				"summary": f"{agent_name} failed.",
				"warnings": [str(exc)],
			},
			{
				"agent": agent_name,
				"scope": "analysis",
				"message": str(exc),
			},
		)


def _resolve_action(composite_score: float) -> str:
	if composite_score >= 0.35:
		return "buy"
	if composite_score <= -0.35:
		return "sell"
	return "hold"


def run_multiagent_workflow(
	symbol: str,
	timeframe: str = "swing",
	market_context: str = "No additional market context provided.",
	risk_level: str = "medium",
) -> dict:
	normalized_symbol = symbol.strip().upper()
	errors: list[AgentError] = []

	technical, technical_error = _safe_run(
		"technical",
		run_technical_analysis,
		normalized_symbol,
		timeframe,
	)
	fundamental, fundamental_error = _safe_run(
		"fundamental",
		run_fundamental_analysis,
		normalized_symbol,
	)
	sentiment, sentiment_error = _safe_run(
		"sentiment",
		run_sentiment_analysis,
		normalized_symbol,
	)

	for possible_error in (technical_error, fundamental_error, sentiment_error):
		if possible_error:
			errors.append(possible_error)

	weighted_inputs = [
		(technical, 0.45),
		(fundamental, 0.35),
		(sentiment, 0.20),
	]

	weighted_sum = 0.0
	confidence_sum = 0.0
	available_weight = 0.0

	for result, weight in weighted_inputs:
		if result.get("status") != "completed":
			continue
		signal_score = _SIGNAL_TO_SCORE.get(result.get("signal", "neutral"), 0.0)
		confidence = float(result.get("confidence", 0.0) or 0.0)
		weighted_sum += signal_score * weight * confidence
		confidence_sum += confidence
		available_weight += weight

	composite_score = 0.0
	if available_weight > 0:
		composite_score = weighted_sum / available_weight

	action = _resolve_action(composite_score)
	average_confidence = confidence_sum / 3

	risk_to_position_pct = {
		"low": 0.03,
		"medium": 0.05,
		"high": 0.08,
	}
	position_size_pct = risk_to_position_pct.get(risk_level.lower(), 0.05)

	if timeframe.lower() == "intraday":
		stop_loss_pct = 0.015
		take_profit_pct = 0.03
	else:
		stop_loss_pct = 0.03
		take_profit_pct = 0.06

	thesis_parts = [
		f"Technical: {technical.get('summary', 'n/a')}",
		f"Fundamental: {fundamental.get('summary', 'n/a')}",
		f"Sentiment: {sentiment.get('summary', 'n/a')}",
	]

	return {
		"workflow": "multiagent_v1",
		"symbol": normalized_symbol,
		"timeframe": timeframe,
		"market_context": market_context,
		"risk_level": risk_level,
		"agent_outputs": {
			"technical": technical,
			"fundamental": fundamental,
			"sentiment": sentiment,
		},
		"composite_score": round(composite_score, 4),
		"overall_confidence": round(average_confidence, 4),
		"recommended_action": action,
		"thesis": " ".join(thesis_parts),
		"risk_plan": {
			"position_size_pct": position_size_pct,
			"stop_loss_pct": stop_loss_pct,
			"take_profit_pct": take_profit_pct,
		},
		"errors": errors,
		"disclaimer": "Educational use only. Not financial advice.",
	}

