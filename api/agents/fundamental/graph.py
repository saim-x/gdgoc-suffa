"""Fundamental analysis utilities and signal generation."""

from __future__ import annotations

import yfinance as yf

from core.schemas import AgentResult


def run_fundamental_analysis(symbol: str) -> AgentResult:
	info = yf.Ticker(symbol).info or {}

	trailing_pe = info.get("trailingPE")
	forward_pe = info.get("forwardPE")
	profit_margins = info.get("profitMargins")
	earnings_growth = info.get("earningsQuarterlyGrowth")
	roe = info.get("returnOnEquity")
	debt_to_equity = info.get("debtToEquity")

	score = 0

	if isinstance(profit_margins, (int, float)):
		if profit_margins >= 0.10:
			score += 1
		elif profit_margins < 0:
			score -= 1

	if isinstance(earnings_growth, (int, float)):
		if earnings_growth >= 0.05:
			score += 1
		elif earnings_growth < 0:
			score -= 1

	if isinstance(roe, (int, float)):
		if roe >= 0.12:
			score += 1
		elif roe <= 0.05:
			score -= 1

	if isinstance(debt_to_equity, (int, float)):
		if debt_to_equity <= 100:
			score += 1
		elif debt_to_equity >= 250:
			score -= 1

	selected_pe = trailing_pe if isinstance(trailing_pe, (int, float)) else forward_pe
	if isinstance(selected_pe, (int, float)):
		if 5 <= selected_pe <= 35:
			score += 1
		elif selected_pe > 60:
			score -= 1

	if score >= 2:
		signal = "bullish"
	elif score <= -2:
		signal = "bearish"
	else:
		signal = "neutral"

	confidence = min(0.85, 0.42 + 0.09 * abs(score))
	summary = (
		f"Margins={profit_margins}, earningsGrowth={earnings_growth}, ROE={roe}, "
		f"D/E={debt_to_equity}, PE={selected_pe}. Fundamentals indicate {signal} bias."
	)

	return {
		"status": "completed",
		"signal": signal,
		"confidence": round(confidence, 2),
		"summary": summary,
		"metrics": {
			"trailing_pe": trailing_pe,
			"forward_pe": forward_pe,
			"profit_margins": profit_margins,
			"earnings_growth": earnings_growth,
			"return_on_equity": roe,
			"debt_to_equity": debt_to_equity,
			"score": score,
		},
	}

