"""Schemas for the technical analysis agent."""

from pydantic import BaseModel, Field


class TechnicalWatchlistRequest(BaseModel):
    symbols: list[str] = Field(
        default_factory=lambda: ["AAPL", "MSFT", "NVDA", "TSLA"],
        examples=[["AAPL", "MSFT", "NVDA", "TSLA"]],
    )
