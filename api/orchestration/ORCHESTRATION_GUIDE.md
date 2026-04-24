# Orchestration Layer — Developer Guide

> **Branch:** `feature/multi-agent-comms`
> **Location:** `api/orchestration/` (fully isolated — zero modifications to `api/core/`)
> **Last Updated:** 2026-04-25
> **Validation:** 9/9 integrity checks passing

---

## Table of Contents

1. [What Is This?](#1-what-is-this)
2. [Why a Separate Directory?](#2-why-a-separate-directory)
3. [File Reference](#3-file-reference)
4. [Architecture](#4-architecture)
5. [Shared Contracts](#5-shared-contracts)
6. [Adapters — How Your Output Gets Normalized](#6-adapters--how-your-output-gets-normalized)
7. [Signal Fusion — How the Final Recommendation Works](#7-signal-fusion--how-the-final-recommendation-works)
8. [Demo Server — Try It Live](#8-demo-server--try-it-live)
9. [Quick Start for Teammates](#9-quick-start-for-teammates)
10. [Adding a New Agent](#10-adding-a-new-agent)
11. [What We Need From You](#11-what-we-need-from-you)
12. [Validation & Testing](#12-validation--testing)
13. [Integration Roadmap](#13-integration-roadmap)
14. [Glossary](#14-glossary)

---

## 1. What Is This?

This is the **orchestration layer** — the "Brain" that connects all agent
workflows (`sma_graph`, `trading_graph`, `truth_graph`) into a unified
decision pipeline.

**The Problem:** Each agent workflow uses its own private `TypedDict` state.
They produce outputs in different shapes. There is no way for one agent to
read another agent's conclusions, which blocks multi-agent reasoning.

**The Solution:** A shared-state architecture with four components:

| Component | What It Does | File |
|-----------|-------------|------|
| **Contracts** | Defines the shared state shape (the "baton") | `contracts.py` |
| **Adapters** | Translates each agent's raw output into a common format | `adapters.py` |
| **Engine** | Manages baton-passing between agents and fuses signals | `engine.py` |
| **Demo** | Interactive visual demo for testing and presentations | `demo.py` + `demo_ui.html` |

---

## 2. Why a Separate Directory?

To **avoid merge conflicts**. Since teammates are actively updating files
in `api/core/` and the graph files on `main`, we keep all orchestration
code in its own `api/orchestration/` package.

**Rules:**
- We **import** from `core/schemas.py` (read-only — for `AgentResult`, `SignalValue`, etc.)
- We **never modify** any file outside `api/orchestration/`
- At merge time, the team can decide whether to promote types into `core/`

### Files NOT touched (teammate ownership)

| File | Owner | Status |
|------|-------|--------|
| `core/schemas.py` | Shared team | **UNTOUCHED** (read-only import) |
| `core/state.py` | Shared team | **UNTOUCHED** |
| `core/orchestrator.py` | Shared team | **UNTOUCHED** |
| `main.py` | Teammate A | **UNTOUCHED** |
| `trading_graph.py` | Teammate A | **UNTOUCHED** |
| `sma_graph.py` | Teammate A | **UNTOUCHED** |
| `truth_graph.py` | Teammate B | **UNTOUCHED** |
| `agents/*` | Team | **UNTOUCHED** |

---

## 3. File Reference

```
api/orchestration/
├── __init__.py              Package init (10 lines)
├── contracts.py             Shared types: OrchestratorState, AgentHandoff,
│                            AgentStatus, PhaseValue (201 lines)
├── adapters.py              SMA/Trading/Truth → AgentResult translators (240 lines)
├── engine.py                Baton-passing, error recording, signal fusion,
│                            pipeline runner (409 lines)
├── mock_runner.py           Standalone test with synthetic data (373 lines)
├── demo.py                  FastAPI demo server on port 8100 (210 lines)
├── demo_ui.html             Dark-theme interactive pipeline visualization (325 lines)
└── ORCHESTRATION_GUIDE.md   This file
```

**Total: 8 source files, ~2,000 lines of code**

---

## 4. Architecture

### How the Baton Flows

```
START
  │
  ▼
┌─────────────────┐
│  Technical Agent │  ← reads market data (SMA, price action)
│  (Perception)    │
└────────┬────────┘
         │  handoff: writes to state.technical
         │  logs: AgentHandoff(context_snapshot = {})
         ▼
┌─────────────────┐
│  Sentiment Agent │  ← reads social signals (Twitter/X, Truth Social)
│  (Context)       │
└────────┬────────┘
         │  handoff: writes to state.sentiment
         │  logs: AgentHandoff(context_snapshot = {technical: ...})
         ▼
┌─────────────────┐
│  Risk Agent      │  ← risk assessment and position sizing
│  (Decision)      │
└────────┬────────┘
         │  handoff: writes to state.risk
         │  logs: AgentHandoff(context_snapshot = {technical: ..., sentiment: ...})
         ▼
┌─────────────────┐
│  Signal Fusion   │  ← confidence-weighted ensemble averaging
│  (Aggregation)   │
└────────┬────────┘
         │
         ▼
  FINAL RECOMMENDATION
  (signal + composite_score + overall_confidence)
```

### Key Design Principles

1. **Blackboard Architecture:** Agents read the full state but write only to their own slice
2. **Append-Only Audit Trail:** Every handoff is logged with a timestamp and context snapshot
3. **Deterministic Transitions:** Same inputs always produce the same outputs (testable, debuggable)
4. **Adapter Pattern:** Agents keep their own output format; adapters handle translation

### State Machine Formalism

This is a **Mealy Machine** where:
- `S` = current `OrchestratorState` (all agent slices + handoff log)
- `I` = a new agent's output (an `AgentResult`)
- `δ(S, I)` = transition function (update the relevant slice, append handoff)
- `λ(S, I)` = output function (check completion → emit final recommendation)

---

## 5. Shared Contracts

### AgentResult — The Universal Agent Output

Every agent, regardless of internal implementation, must ultimately produce an
`AgentResult`. This is defined in `core/schemas.py` (the team's shared contract):

```python
class AgentResult(TypedDict, total=False):
    status: StatusValue       # "pending" | "completed" | "failed" | "skipped"
    signal: SignalValue       # "bullish" | "bearish" | "neutral" | "mixed" | "insufficient_data"
    confidence: float         # 0.0 to 1.0 (normalized)
    summary: str              # human-readable explanation
    metrics: dict             # domain-specific numbers (e.g. SMA values, risk scores)
    details: dict             # full traceability (raw_output from source)
    warnings: list[str]       # caveats (e.g. "free_text_output_not_classifiable")
```

### Signal Vocabulary

All agents must use these exact values:

| Value | Meaning |
|-------|---------|
| `"bullish"` | Positive directional bias |
| `"bearish"` | Negative directional bias |
| `"neutral"` | No clear direction |
| `"mixed"` | Conflicting signals |
| `"insufficient_data"` | Cannot determine (default/fallback) |

### Confidence Scale

| Range | Meaning |
|-------|---------|
| `0.0` | No confidence / insufficient data |
| `0.5` | Neutral / uncertain |
| `1.0` | Maximum confidence |

**Important:** If your source uses 0–100 (like `truth_graph`'s `confidence_score`), the adapter automatically divides by 100. You don't need to change your output.

### Orchestration-Specific Types (defined in `contracts.py`)

```python
# Cognitive pipeline phases
PhaseValue = Literal["perception", "context", "scoring", "decision", "execution"]

# Message envelope for baton-passing
class AgentHandoff(TypedDict, total=False):
    from_agent: str             # e.g. "technical"
    to_agent: str               # e.g. "sentiment"
    phase: PhaseValue           # which pipeline stage
    timestamp: str              # ISO 8601
    payload: AgentResult        # the actual data being handed off
    context_snapshot: dict      # what the receiver will see (all completed agents)

# Runtime status of a single agent
class AgentStatus(TypedDict, total=False):
    agent_id: str               # e.g. "technical"
    phase: PhaseValue
    status: StatusValue         # "pending" | "completed" | "failed" | "skipped"
    last_updated: str           # ISO 8601
    result: AgentResult
    error: AgentError

# The master baton — single source of truth
class OrchestratorState(TypedDict, total=False):
    session_id: str
    ticker: str
    run_timestamp: str
    technical: AgentResult      # each agent writes to exactly one slice
    sentiment: AgentResult
    fundamental: AgentResult
    risk: AgentResult
    agent_statuses: dict[str, AgentStatus]
    handoff_log: list[AgentHandoff]   # append-only audit trail
    user_profile: UserProfile
    portfolio_context: PortfolioContext
    market_signals: list[MarketSignal]
    candidate_symbols: list[str]
    final_recommendation: dict
    errors: list[AgentError]
    metadata: dict
```

---

## 6. Adapters — How Your Output Gets Normalized

Adapters are **pure functions** in `adapters.py` that translate domain-specific
outputs into the shared `AgentResult` format. They never modify the original data.

### Currently Implemented Adapters

| Adapter | Input Source | Signal Extraction | Confidence Logic |
|---------|------------|-------------------|-----------------|
| `adapt_sma_to_agent_result()` | `sma_graph.py` output | Reads `signal` field directly | Price-vs-SMA deviation: 5%+ above = 0.9 confidence |
| `adapt_trading_to_agent_result()` | `trading_graph.py` output | Parses "Bias:" line from LLM free-text | Parses "Confidence: high/medium/low" → 0.85/0.6/0.35 |
| `adapt_truth_to_agent_result()` | `truth_graph.py` output | Reads `direction` field directly | `confidence_score / 100` (int 0-100 → float 0.0-1.0) |

### How an adapter works (example):

```python
# truth_graph returns: {"direction": "bullish", "confidence_score": 78, ...}
# The adapter produces:
AgentResult(
    status="completed",
    signal="bullish",         # mapped from "direction"
    confidence=0.78,          # 78 / 100
    summary="...",            # from "decision_rationale"
    metrics={...},            # confidence_score_raw, action, position_size, etc.
    details={"raw_output": original_dict},  # full traceability
)
```

---

## 7. Signal Fusion — How the Final Recommendation Works

The `aggregate_recommendation()` function in `engine.py` combines all
completed agents' signals using **confidence-weighted ensemble averaging**:

```
For each completed agent:
  score = {"bullish": +1, "bearish": -1, "neutral": 0}[signal]
  weighted_contribution = score × confidence

composite_score = Σ(weighted_contributions) / Σ(confidences)
overall_confidence = Σ(confidences) / number_of_agents

Final signal:
  composite > +0.2   →  "bullish"
  composite < -0.2   →  "bearish"
  otherwise          →  "neutral"
```

### Example with 3 agents:

| Agent | Signal | Confidence | Score × Confidence |
|-------|--------|------------|-------------------|
| Technical | bullish | 0.90 | +0.90 |
| Sentiment | bullish | 0.78 | +0.78 |
| Risk | bullish | 0.65 | +0.65 |

- **Composite** = (0.90 + 0.78 + 0.65) / (0.90 + 0.78 + 0.65) = **+1.00**
- **Confidence** = 2.33 / 3 = **0.777 (78%)**
- **Final signal:** strong bullish

### When agents disagree:

| Agent | Signal | Confidence | Score × Confidence |
|-------|--------|------------|-------------------|
| Technical | bullish | 0.90 | +0.90 |
| Sentiment | bearish | 0.85 | −0.85 |
| Risk | neutral | 0.50 | 0.00 |

- **Composite** = (0.90 − 0.85 + 0.00) / (0.90 + 0.85 + 0.50) = **+0.022**
- **Final signal:** neutral (the disagreement cancels out)

---

## 8. Demo Server — Try It Live

A standalone FastAPI app that visualizes the pipeline. Does **not** modify `main.py`.

### How to run:

```bash
cd api
python -m orchestration.demo
# Open http://localhost:8100
```

### What you'll see:

- **Pipeline visualization** — 4 agent cards animate in sequence as the pipeline runs
- **"Run Pipeline"** — runs the mock data pipeline with synthetic TSLA data
- **"Custom Signals"** — manually set each agent's signal and confidence, then see how the fusion engine responds
- **"View Contracts"** — shows the `AgentResult` schema shape

### API endpoints (for programmatic access):

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Visual demo UI (HTML page) |
| `POST` | `/api/run-pipeline` | Run mock pipeline, returns full state JSON |
| `POST` | `/api/run-custom` | Run with custom signals (pass signal + confidence per agent) |
| `GET` | `/api/contracts` | Show the shared contract shapes |

### Example `run-custom` request:

```json
{
  "ticker": "TSLA",
  "technical": {"signal": "bullish", "confidence": 0.85, "summary": "SMA crossover"},
  "sentiment": {"signal": "bearish", "confidence": 0.70, "summary": "Negative tweets"},
  "risk": {"signal": "neutral", "confidence": 0.50, "summary": "Moderate risk"}
}
```

---

## 9. Quick Start for Teammates

### "I just want to see it work"

```bash
cd api
python -m orchestration.mock_runner TSLA
```

This runs the full pipeline with synthetic data and prints every step.

### "I want to see the visual demo"

```bash
cd api
python -m orchestration.demo
# Open http://localhost:8100 in your browser
```

### "I don't want to change anything in my code"

**You don't have to.** The adapters already know how to read your output format:

- `sma_graph` output → handled by `adapt_sma_to_agent_result()`
- `trading_graph` output → handled by `adapt_trading_to_agent_result()`
- `truth_graph` output → handled by `adapt_truth_to_agent_result()`

Your code stays exactly as-is. The orchestrator calls your workflow, runs the
output through the adapter, and writes the normalized result to the shared state.

### "I want to skip the adapter and return AgentResult directly"

Just return a dict matching the `AgentResult` shape from your workflow. The
orchestrator will use it as-is without an adapter.

---

## 10. Adding a New Agent

If you're building a new agent (e.g. fundamental analysis), here's the checklist:

### Step 1: Add a state slice

In `orchestration/contracts.py`, add a field to `OrchestratorState`:

```python
class OrchestratorState(TypedDict, total=False):
    # ... existing slices ...
    fundamental: AgentResult    # ← add your new slice here
```

### Step 2: Write an adapter (optional)

In `orchestration/adapters.py`:

```python
def adapt_fundamental_to_agent_result(raw_output: dict) -> AgentResult:
    return AgentResult(
        status="completed",
        signal=_normalize_signal(raw_output.get("signal", "")),
        confidence=raw_output.get("confidence", 0.5),
        summary=raw_output.get("summary", ""),
        metrics={...},
        details={"source_workflow": "fundamental", "raw_output": raw_output},
        warnings=[],
    )
```

### Step 3: Add a handoff step

In `orchestration/engine.py`, update the pipeline in `run_orchestration()`:

```python
pipeline = [
    ("technical", "sentiment", "perception"),
    ("sentiment", "fundamental", "context"),    # ← insert your agent
    ("fundamental", "risk", "scoring"),         # ← update downstream
    ("risk", "orchestrator", "decision"),
]
```

### Step 4: Test

```bash
cd api
python -m orchestration.mock_runner TSLA
```

---

## 11. What We Need From You

### From Teammate A (FastAPI / Technical Analysis)

| Item | Priority | Details |
|------|----------|---------|
| No code changes needed | — | Adapters already handle your output format |
| Confirm LLM output format | Medium | Does `trading_graph` LLM always output "Bias:" and "Confidence:" lines? The adapter parses those keywords to extract structured signals. If the format varies, let us know so we can adjust the parser. |

### From Teammate B (Sentiment / Twitter)

| Item | Priority | Details |
|------|----------|---------|
| No code changes needed | — | Adapter already normalizes `confidence_score` (int 0-100 → float 0.0-1.0) |
| Signal vocabulary | Low | Confirm you always use `"bullish"`, `"bearish"`, `"neutral"` for `direction`. Any new values need to be added to our `_normalize_signal()` mapper. |

### From Both

- **Don't worry about the orchestrator** — it's completely self-contained
- **Signal strings:** stick to `"bullish"`, `"bearish"`, `"neutral"`
- **New output fields:** if you add new keys to your workflow output, let us know so we can update the adapters
- **Testing:** run `python -m orchestration.mock_runner TSLA` anytime to verify the pipeline

---

## 12. Validation & Testing

### Mock Runner (9 automated checks)

```bash
cd api
python -m orchestration.mock_runner TSLA
```

Current results:

```
[PASS] technical_slice_populated      — Technical agent wrote to its slice
[PASS] sentiment_slice_populated      — Sentiment agent wrote to its slice
[PASS] risk_slice_populated           — Risk agent wrote to its slice
[PASS] handoff_log_has_3_entries      — All 3 handoffs were recorded
[PASS] handoff_order_correct          — Handoffs happened in the right order
[PASS] context_accumulation           — Each handoff sees previous agents' results
[PASS] final_recommendation_present   — Signal fusion produced a recommendation
[PASS] no_errors                      — No agent errors recorded
[PASS] session_metadata_intact        — Session ID, ticker, and timestamp present
```

### What each check verifies

| Check | What breaks if it fails |
|-------|------------------------|
| `*_slice_populated` | An agent didn't produce an `AgentResult` with `status: "completed"` |
| `handoff_log_has_3_entries` | A handoff was skipped or duplicated |
| `handoff_order_correct` | Agents ran out of sequence |
| `context_accumulation` | Downstream agents can't see upstream agents' results |
| `final_recommendation_present` | Signal fusion failed or produced empty output |
| `no_errors` | An agent raised an exception during processing |
| `session_metadata_intact` | State initialization failed |

---

## 13. Integration Roadmap

### Done ✅

- [x] Shared type contracts (`OrchestratorState`, `AgentHandoff`, etc.)
- [x] Adapters for all 3 existing workflows (SMA, Trading, Truth)
- [x] Baton-passing engine with deterministic state transitions
- [x] Signal fusion (confidence-weighted ensemble)
- [x] Mock runner with 9 automated validation checks
- [x] Interactive demo server with visual pipeline UI
- [x] Full developer documentation (this file)

### Next Steps (post-hackathon or when ready)

- [ ] **Wire to main.py:** Add a `POST /orchestrate/{ticker}` route that calls the real workflows and runs them through the orchestrator
- [ ] **Async execution:** Run agents in parallel using LangGraph's parallel branch support
- [ ] **Dynamic weighting:** Weight agents by historical accuracy instead of static confidence
- [ ] **Fundamental agent:** Fill the `fundamental` slice with earnings/revenue data
- [ ] **WebSocket updates:** Push pipeline progress to the mobile app in real-time

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| **Baton** | The `OrchestratorState` — the shared data object passed between agents |
| **Handoff** | The act of one agent completing its work and passing enriched state to the next |
| **Slice** | An agent's designated write region in the state (e.g. `state.technical`) |
| **Adapter** | A pure function that translates domain-specific output into `AgentResult` |
| **Context Snapshot** | A summary of all completed agents' signals at a given handoff point, embedded in each `AgentHandoff`. Enables downstream agents to assess what came before them. |
| **Signal Fusion** | Confidence-weighted ensemble averaging of all agent signals into one recommendation |
| **Blackboard Architecture** | A shared memory space where agents read globally but write to designated regions |
| **Mealy Machine** | A finite state machine where outputs depend on both current state AND input |
| **Composite Score** | The weighted average of all agent scores, ranging from -1.0 (strong bearish) to +1.0 (strong bullish) |
| **PhaseValue** | The cognitive stage of the pipeline: perception → context → scoring → decision → execution |
