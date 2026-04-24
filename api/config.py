"""Centralized configuration for the trading backend."""

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

# ── API Keys ──────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ── Database ──────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_PATH: str = str(DATA_DIR / "trading.db")

# ── Market Data ───────────────────────────────────────────────────────
YFINANCE_CACHE_TTL_SECONDS: int = 30
DEFAULT_WATCHLIST: list[str] = [
    "AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "BTC-USD", "ETH-USD",
]

# ── Trade Simulation ──────────────────────────────────────────────────
TRADE_FEE_RATE: float = 0.001        # 0.1% flat fee per trade
SLIPPAGE_RATE: float = 0.0005        # 0.05% simulated slippage
DEFAULT_TOTAL_CAPITAL: float = 500_000.0

# ── Agent Defaults ────────────────────────────────────────────────────
DEFAULT_AGENTS = [
    {
        "id": "agent-orion",
        "name": "ORION",
        "strategy": "Event-driven signal trading",
        "assigned_capital": 200_000.0,
        "confidence_threshold": 85,
        "status": "active",
    },
    {
        "id": "agent-atlas",
        "name": "ATLAS",
        "strategy": "Technical momentum",
        "assigned_capital": 150_000.0,
        "confidence_threshold": 78,
        "status": "active",
    },
    {
        "id": "agent-sentinel",
        "name": "SENTINEL",
        "strategy": "Contrarian reversal",
        "assigned_capital": 150_000.0,
        "confidence_threshold": 92,
        "status": "active",
    },
]

# ── Scheduler ─────────────────────────────────────────────────────────
SIGNAL_POLL_INTERVAL_SECONDS: int = 60
PENDING_EXPIRY_SECONDS: int = 120

# ── Indicator Weights (must sum to 1.0) ───────────────────────────────
INDICATOR_WEIGHTS = {
    "sma": 0.30,
    "rsi": 0.30,
    "sentiment": 0.40,
}
