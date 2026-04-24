"""Sentiment analysis utilities and signal generation."""

from __future__ import annotations

import yfinance as yf

from core.schemas import AgentResult


_RECOMMENDATION_KEY_SCORES = {
	"strong_buy": 2,
	"buy": 1,
	"hold": 0,
	"underperform": -1,
	"sell": -1,
	"strong_sell": -2,
}


def run_sentiment_analysis(symbol: str) -> AgentResult:
	info = yf.Ticker(symbol).info or {}

	recommendation_key = str(info.get("recommendationKey", "")).lower()
	recommendation_mean = info.get("recommendationMean")
	short_percent = info.get("shortPercentOfFloat")
	change_52w = info.get("52WeekChange")

	score = 0
	score += _RECOMMENDATION_KEY_SCORES.get(recommendation_key, 0)

	if isinstance(recommendation_mean, (int, float)):
		if recommendation_mean <= 2.0:
			score += 1
		elif recommendation_mean >= 3.5:
			score -= 1

	if isinstance(short_percent, (int, float)):
		if short_percent <= 0.05:
			score += 1
		elif short_percent >= 0.15:
			score -= 1

	if isinstance(change_52w, (int, float)):
		if change_52w >= 0.10:
			score += 1
		elif change_52w <= -0.10:
			score -= 1

	if score >= 2:
		signal = "bullish"
	elif score <= -2:
		signal = "bearish"
	else:
		signal = "neutral"

	confidence = min(0.85, 0.40 + 0.10 * abs(score))
	summary = (
		f"Street view={recommendation_key or 'unknown'}, "
		f"recommendationMean={recommendation_mean}, shortFloat={short_percent}, "
		f"52W change={change_52w}. Sentiment proxy indicates {signal} bias."
	)

	return {
		"status": "completed",
		"signal": signal,
		"confidence": round(confidence, 2),
		"summary": summary,
		"metrics": {
			"recommendation_key": recommendation_key or None,
			"recommendation_mean": recommendation_mean,
			"short_percent_of_float": short_percent,
			"change_52w": change_52w,
			"score": score,
		},
	}

