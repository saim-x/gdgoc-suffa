# GDGOC Suffa: Autonomous Multi-Agent Trading Simulator

**Built for Build With AI 2026 by GDG on Campus DHA Suffa University & impetus SYSTEMS.**

Most AI trading projects at hackathons just pipe a stock ticker into an LLM and buy whatever it says. We wanted to build something that actually mirrors how quantitative trading desks work. 

So we built a real-time, autonomous trading simulator where multiple AI agents evaluate social media sentiment, validate it against hard technical indicators, and execute simulated trades using a persistent SQLite backend and a React Native (Expo) control center.

## How It Solves the Core Problem (Usefulness & Creativity)

Retail traders lose money because they trade on emotion or chase social media hype. Institutional traders win because they have systems that validate that hype against market structure. 

We built an architecture that democratizes that process. When a breaking news event happens, our system doesn't just blindly buy. It runs a consensus model:
1. **The Technicals:** It pulls live pricing via `yfinance` and calculates SMA-20 (moving average) and RSI-14 (momentum).
2. **The Sentiment (AI Integration):** It passes the social context to Groq (running Llama-3.1-8b) to gauge market psychology. Forcing the LLM to output strict JSON decisions instead of conversational fluff.
3. **The Aggregator:** A weighted engine merges the technical momentum with the AI sentiment score.

## Deep AI Integration & Multi-Agent Execution

This isn't a wrapper around a single prompt. We built a true multi-agent decision engine. The aggregated signal is fed to three distinct agent personas:
- **ORION:** Event-driven trading.
- **ATLAS:** Technical momentum.
- **SENTINEL:** Contrarian reversal.

Each agent has its own assigned capital, performance tracking, and confidence thresholds. If a signal meets an agent's confidence threshold (e.g., >90%), it executes automatically. The simulator realistically deducts a 0.1% fee and 0.05% slippage on every trade.

## The Human-in-the-Loop Control Center (Execution)

We don't trust autonomous agents with our money without oversight. If an agent wants to make a trade but its confidence is in the "gray zone" (60%-89%), it pauses and generates a "pending approval" request.

We built a beautiful, 5-tab Expo React Native mobile app to manage this:
- **Real-time Telemetry:** The app polls the FastAPI backend every 8 seconds. 
- **Approval Workflow:** You get push-style UI alerts to accept or reject pending trades before they expire.
- **Live P&L & Charts:** Dynamic trend charts and active portfolio breakdowns showing restricted vs. active capital.
- **Agent Governance:** You can slide confidence thresholds, reallocate capital limits, or pause a rogue agent entirely from your phone.

We even built in UI foundations for biometric locks and dynamic risk scaling (Low/Medium/High).

## Technical Architecture

We moved away from a simple stateless script to a fully persistent polling engine.

```text
Data Ingestion (yfinance, 30s cache)
    → Signal Engine (SMA, RSI, Groq LLM)
        → MiroFish Swarm Layer (multi-agent consensus refinement)
        → Aggregator (Weighted Confidence)
            → Agent Engine (ORION, ATLAS, SENTINEL)
                → Trade Simulator (Fees + Slippage)
                    → SQLite Database (aiosqlite WAL mode)
                        → REST API
                            → Expo Mobile App
```

**Tech Stack:**
- **Backend:** Python, FastAPI, aiosqlite, LangGraph, Groq, yfinance.
- **Frontend:** React Native, Expo, TypeScript. 

*Note for the Judges:* We spent time getting the developer experience right so you can actually test this. The Expo app uses `expo-constants` to automatically detect the local backend IP on your network. You can just scan the QR code and it connects. No fiddling with hardcoded IPs required.

## Run It Locally

**Start the backend:**
```bash
pip install -r api/requirements.txt
python -m uvicorn main:app --reload --app-dir api --host 0.0.0.0 --port 8000
```

**Start the app:**
```bash
npm install --prefix expo-app
npm run dev:frontend
```
