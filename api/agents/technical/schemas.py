"""Technical analysis typed schemas."""

from typing import TypedDict


class TechnicalMetrics(TypedDict, total=False):
	latest_close: float
	sma_20: float
	sma_50: float
	rsi_14: float
	candles: int

