## GDGOC Suffa — Multi-Agent AI Trading Simulator

FastAPI backend + Expo frontend for a real-time, agent-driven trading simulation system.

### Architecture

```
Data Ingestion (yfinance, 30s cache)
    → Signal Engine (SMA-20, RSI-14, Groq Sentiment)
        → Aggregator (weighted confidence merge)
            → Agent Decision Engine (ORION, ATLAS, SENTINEL)
                → Trade Simulator (fees + slippage)
                    → REST API → Expo Frontend
```

### Backend API

**Core Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check + scheduler status |
| GET | `/signals` | List recent signals (filter by asset) |
| POST | `/analyze/{symbol}` | Trigger full analysis pipeline |
| GET | `/agents` | List all agents |
| PUT | `/agents/{id}` | Update agent config |
| GET | `/portfolio` | Portfolio state with live P&L |
| GET | `/trades` | Trade history |
| GET | `/trades/active` | Open positions with unrealized P&L |
| POST | `/trades/{id}/close` | Close an open trade |
| GET | `/pending` | Pending approval trades |
| POST | `/pending/{id}/approve` | Approve pending trade |
| POST | `/pending/{id}/reject` | Reject pending trade |
| GET | `/activity` | Activity feed |
| GET/POST | `/summary/daily` | Daily trading summary |
| POST | `/settings/autonomous` | Toggle autonomous mode |
| POST | `/settings/risk` | Set risk level |

**Legacy Endpoints (backward compat):**
- `POST /truth/analyze` — Truth-layer signal analysis
- `POST /truth/summary/daily` — Legacy daily summary
- `POST /analysis/sma` — SMA-only analysis

### Frontend (Expo)

Five-tab mobile app: Home, Portfolio, Agents, Activity, Settings

- Polls backend every 8s for live data
- Agent management (toggle, capital, thresholds)
- Signal analysis via truth-layer input
- Pending trade approval/rejection
- P&L tracking and daily summaries

### Run

**Backend:**
```bash
pip install -r api/requirements.txt
python -m uvicorn main:app --reload --app-dir api
```

**Frontend:**
```bash
npm install --prefix expo-app
npm run dev:frontend
```

### Tech Stack

- **Backend:** FastAPI, LangGraph, Groq LLM, yfinance, SQLite (aiosqlite)
- **Frontend:** Expo/React Native, TypeScript
- **AI:** Groq (llama-3.1-8b-instant) for sentiment analysis
- **Indicators:** SMA-20, RSI-14, LLM Sentiment
