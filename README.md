## GDGOC Suffa

FastAPI backend + Expo frontend prototype for a multi-agent trading system.

### Backend API (current)

1. `POST /analysis/basic` - Multi-agent LLM analysis (technical + sentiment + lead signal)
2. `POST /analysis/sma` - SMA-20 directional signal for one ticker
3. `POST /truth/analyze` - Truth layer signal routing for X/Truth Social announcements with tiered execution logic
4. `POST /truth/summary/daily` - Daily rollup of truth-layer trade outcomes, rationale quality, and PnL

### Frontend (Expo app)

The Expo app lives in `expo-app` and includes a premium UI around the truth-layer workflow:

1. Bottom-tab product UI (`Home`, `Portfolio`, `Agents`, `Activity`, `Settings`)
2. Live truth-layer signal test (`POST /truth/analyze`)
3. Daily summary generation (`POST /truth/summary/daily`)
4. Agent management controls (status, allocation, confidence thresholds)

Run:

1. `npm install --prefix expo-app`
2. `npm run dev:frontend`
