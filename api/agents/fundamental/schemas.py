"""Fundamental analysis typed schemas."""

from typing import TypedDict


class FundamentalMetrics(TypedDict, total=False):
	trailing_pe: float | None
	forward_pe: float | None
	profit_margins: float | None
	earnings_growth: float | None
	return_on_equity: float | None
	debt_to_equity: float | None
	score: int

