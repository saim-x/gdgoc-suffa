"""Sentiment analysis typed schemas."""

from typing import TypedDict


class SentimentMetrics(TypedDict, total=False):
	recommendation_key: str | None
	recommendation_mean: float | None
	short_percent_of_float: float | None
	change_52w: float | None
	score: int
