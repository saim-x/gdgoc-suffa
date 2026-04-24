# GDGOC Suffa - Multi-Agent Stock Analyzer

This project is a FastAPI backend for a multi-agent stock analysis system.

## What It Does

- Runs separate specialist agents for:
	- Technical analysis (trend + momentum)
	- Fundamental analysis (quality + valuation proxies)
	- Sentiment analysis (analyst and positioning proxies)
- Aggregates agent outputs into a composite score and trade action.
- Exposes simple HTTP APIs for frontend/mobile integration.

## Current Workflows

- `POST /analysis/sma`
	- Single-agent SMA-20 directional signal.
- `POST /analysis/basic`
	- LLM-based technical + sentiment + lead analyst synthesis.
	- Requires `GROQ_API_KEY` in `api/.env`.
- `POST /analysis/multiagent`
	- Deterministic multi-agent orchestration:
		- technical
		- fundamental
		- sentiment
	- Returns:
		- per-agent signals
		- composite score
		- recommended action (`buy|sell|hold`)
		- risk plan

## Backend Run (Windows PowerShell)

From project root:

```powershell
cd "api"
python -m venv .venv
. .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Or from root using npm script:

```powershell
npm run dev:backend
```

## API Quick Test

```bash
curl http://127.0.0.1:8000/health

curl -X POST -H "Content-Type: application/json" \
	-d '{"symbol":"AAPL","timeframe":"swing","risk_level":"medium"}' \
	http://127.0.0.1:8000/analysis/multiagent
```

## Suggested End-to-End Product Workflow

1. User selects risk profile, market, and timeframe.
2. Theme scanner finds candidate symbols (macro/news/sectors).
3. Per-symbol multi-agent pass (technical + fundamental + sentiment).
4. Rank opportunities with confidence gating.
5. Build allocation plan with position-size and stop-loss constraints.
6. Push trade suggestions to mobile app with explainable thesis.
7. Track outcomes and continuously recalibrate scoring weights.

## What To Build Next

- Add portfolio-aware risk engine (max drawdown, correlation caps).
- Add watchlist scanner endpoint for top-N opportunities.
- Add execution simulator (paper trading + PnL attribution).
- Add persistent storage (signals, recommendations, outcomes).
- Add tests for agent scoring and orchestration edge cases.
- Build Expo UI in `expo-app` for analysis + trade ticket flow.

## Disclaimer

For educational purposes only. This is not financial advice.
