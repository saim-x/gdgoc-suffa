"""Technical analysis utilities and signal generation."""

from __future__ import annotations

import math

import pandas as pd
import yfinance as yf

from core.schemas import AgentResult


def _calculate_rsi(closes: pd.Series, window: int = 14) -> float:
	deltas = closes.diff()
	gains = deltas.clip(lower=0)
	losses = -deltas.clip(upper=0)
	avg_gain = gains.rolling(window=window).mean().iloc[-1]
	avg_loss = losses.rolling(window=window).mean().iloc[-1]

	if pd.isna(avg_gain) or pd.isna(avg_loss):
		return float("nan")
	if avg_loss == 0:
		return 100.0

	rs = avg_gain / avg_loss
	return float(100 - (100 / (1 + rs)))


def run_technical_analysis(symbol: str, timeframe: str = "swing") -> AgentResult:
	history = yf.Ticker(symbol).history(period="6mo", interval="1d")
	closes = history.get("Close", pd.Series(dtype=float)).dropna()

	if len(closes) < 60:
		return {
			"status": "failed",
			"signal": "insufficient_data",
			"confidence": 0.0,
			"summary": f"Not enough price candles for technical analysis on {symbol}.",
			"warnings": ["Need at least 60 daily candles for SMA20/SMA50 and RSI."],
			"metrics": {"candles": int(len(closes))},
		}

	latest_close = float(closes.iloc[-1])
	sma_20 = float(closes.tail(20).mean())
	sma_50 = float(closes.tail(50).mean())
	rsi_14 = _calculate_rsi(closes, window=14)

	score = 0
	score += 1 if latest_close > sma_20 else -1
	score += 1 if sma_20 > sma_50 else -1

	if not math.isnan(rsi_14):
		if rsi_14 > 60:
			score += 1
		elif rsi_14 < 40:
			score -= 1

	if score >= 2:
		signal = "bullish"
	elif score <= -2:
		signal = "bearish"
	else:
		signal = "neutral"

	confidence = min(0.9, 0.45 + 0.12 * abs(score))
	summary = (
		f"Price {latest_close:.2f}, SMA20 {sma_20:.2f}, SMA50 {sma_50:.2f}, RSI14 {rsi_14:.1f}. "
		f"Momentum and trend suggest a {signal} {timeframe} bias."
	)

	return {
		"status": "completed",
		"signal": signal,
		"confidence": round(confidence, 2),
		"summary": summary,
		"metrics": {
			"latest_close": round(latest_close, 2),
			"sma_20": round(sma_20, 2),
			"sma_50": round(sma_50, 2),
			"rsi_14": round(rsi_14, 2),
			"candles": int(len(closes)),
		},
	}

