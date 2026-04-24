# Multi-Agent Communication Layer

> **Feature Branch:** `feature/multi-agent-comms`
> **Owner:** Orchestration / State-Matching
> **Status:** Core contracts + mock pipeline verified

---

## What This Is

This layer is the **"Brain"** of the multi-agent system — the shared state and coordination logic that allows agents to communicate and hand off data to each other without breaking.

**The Problem:** Each agent workflow (`sma_graph`, `trading_graph`, `truth_graph`) currently uses its own private `TypedDict` state. They cannot read each other's outputs, which means we cannot build multi-agent reasoning.

**The Solution:** A **blackboard architecture** with:
1. A shared state contract (`OrchestratorState`) — the "baton" that flows through the pipeline
2. Adapter functions that translate each agent's private output into a common format (`AgentResult`)
3. A handoff protocol that records every data exchange with timestamps and context snapshots
4. A signal fusion engine that combines all agents' outputs into a final recommendation

---

## Architecture Overview

```
                    +--------------------+
                    |   Orchestrator     |
                    | (core/orchestrator)|
                    +--------+-----------+
                             |
              +--------------+----------------+
              |              |                |
     +--------v---+  +------v------+  +------v------+
     | Technical   |  | Sentiment   |  | Risk        |
     | Agent       |  | Agent       |  | Agent       |
     | (SMA/       |  | (Truth/     |  | (Assessment |
     |  Trading)   |  |  Twitter)   |  |  & Scoring) |
     +------+------+  +------+------+  +------+------+
            |                |                |
            v                v                v
     +------+------+  +------+------+  +------+------+
     |  Adapter    |  |  Adapter    |  |  Adapter    |
     |  (adapters) |  |  (adapters) |  |  (adapters) |
     +------+------+  +------+------+  +------+------+
            |                |                |
            +--------+-------+--------+-------+
                     |                |
              +------v------+  +-----v--------+
              | AgentResult |  | AgentResult   |
              | (Shared     |  | (Shared       |
              |  Contract)  |  |  Contract)    |
              +------+------+  +------+--------+
                     |                |
                     +-------+--------+
                             |
                    +--------v---------+
                    | OrchestratorState |
                    | (The Baton)       |
                    +------------------+
```

### Pipeline Flow (State Machine)

```
START --> [Technical Agent] --handoff--> [Sentiment Agent] --handoff--> [Risk Agent] --handoff--> [Aggregate] --> END
              |                              |                              |
              v                              v                              v
         Write to                       Write to                       Write to
         state.technical                state.sentiment                 state.risk
              |                              |                              |
              v                              v                              v
         Log: AgentHandoff              Log: AgentHandoff              Log: AgentHandoff
         (context_snapshot              (context_snapshot               (context_snapshot
          = {})                          = {technical})                 = {technical, sentiment})
```

Each handoff:
1. Writes the agent's output to its designated slice
2. Appends an `AgentHandoff` entry to the log with a `context_snapshot`
3. The snapshot captures what the NEXT agent will see (all completed signals so far)

---

## File Map

All new code lives in `api/core/`. **No existing files were modified** except additive changes to `schemas.py` and `state.py`.

| File | Status | Purpose |
|------|--------|---------|
| `core/schemas.py` | MODIFIED (additive) | Added `PhaseValue`, `AgentHandoff` types |
| `core/state.py` | MODIFIED (additive) | Added `AgentStatus`, `OrchestratorState` |
| `core/adapters.py` | **NEW** | Translates SMA/Trading/Truth outputs to `AgentResult` |
| `core/orchestrator.py` | **NEW** (was empty placeholder) | Baton-passing logic, aggregation engine |
| `core/mock_runner.py` | **NEW** | Standalone test pipeline with synthetic data |

### Files NOT touched (teammate ownership)

| File | Owner | Why untouched |
|------|-------|---------------|
| `main.py` | Teammate A | FastAPI routes - no changes needed |
| `trading_graph.py` | Teammate A | LLM-based analysis workflow |
| `sma_graph.py` | Teammate A | SMA-20 technical signal |
| `truth_graph.py` | Teammate B | Truth/X social signal routing |
| `agents/*` | Team | Domain agent placeholders (future work) |

---

## Shared Contracts Reference

### AgentResult — The Universal Agent Output

Every agent, regardless of what it does internally, must produce an `AgentResult`:

```python
class AgentResult(TypedDict, total=False):
    status: StatusValue       # "pending" | "completed" | "failed" | "skipped"
    signal: SignalValue       # "bullish" | "bearish" | "neutral" | "mixed" | "insufficient_data"
    confidence: float         # 0.0 to 1.0 (normalized)
    summary: str              # human-readable explanation
    metrics: dict             # domain-specific numbers (e.g. SMA values, risk scores)
    details: dict             # full traceability (includes raw_output from source)
    warnings: list[str]       # any caveats (e.g. "free_text_output_not_classifiable")
```

**Why this matters for teammates:**
- Your agent can do whatever it wants internally (LLM calls, API fetches, math)
- At the end, wrap your output in an `AgentResult`
- The orchestrator only reads `AgentResult` — it doesn't care about your internals

### SignalValue — The Signal Vocabulary

All agents must use these exact signal values:

```python
SignalValue = Literal["bullish", "bearish", "neutral", "mixed", "insufficient_data"]
```

### Confidence Scale

- **Range:** `0.0` to `1.0` (float)
- `0.0` = no confidence / insufficient data
- `0.5` = neutral / uncertain
- `1.0` = maximum confidence
- **If your source uses 0-100** (like truth_graph's `confidence_score`), divide by 100

### AgentHandoff — The Message Envelope

Every baton-pass creates an `AgentHandoff`:

```python
class AgentHandoff(TypedDict, total=False):
    from_agent: str           # who sent it (e.g. "technical")
    to_agent: str             # who receives it (e.g. "sentiment")
    phase: PhaseValue         # "perception" | "context" | "scoring" | "decision" | "execution"
    timestamp: str            # ISO 8601
    payload: AgentResult      # the actual data
    context_snapshot: dict    # what the receiver will see (all completed agents' signals)
```

### OrchestratorState — The Master Baton

```python
class OrchestratorState(TypedDict, total=False):
    # Identity
    session_id: str
    ticker: str
    run_timestamp: str

    # Agent result slices (each agent writes to exactly one)
    technical: AgentResult
    sentiment: AgentResult
    fundamental: AgentResult
    risk: AgentResult

    # Runtime tracking
    agent_statuses: dict[str, AgentStatus]
    handoff_log: list[AgentHandoff]     # append-only audit trail

    # Context
    user_profile: UserProfile
    portfolio_context: PortfolioContext
    market_signals: list[MarketSignal]
    candidate_symbols: list[str]

    # Outputs
    final_recommendation: dict
    errors: list[AgentError]
    metadata: dict
```

**Design Rule:** Each agent **reads** the full state but **writes** only to its own slice.

---

## How To Use This (For Teammates)

### If you're building an agent workflow:

1. **Do your analysis however you want** (LLM, API, math — doesn't matter)
2. **At the end, return your output as a regular dict** (you already do this)
3. **We have adapters** that translate your output into `AgentResult` format
4. If you want to write a native adapter, just produce an `AgentResult` directly

### If you want to test the pipeline:

```bash
cd api
python -m core.mock_runner TSLA
```

This runs the full pipeline with synthetic data and validates all 9 integrity checks.

### If you're adding a new agent:

1. Add a new slice to `OrchestratorState` (e.g. `macro: AgentResult`)
2. Create an adapter in `core/adapters.py` for your output format
3. Add a handoff step in `core/orchestrator.py`
4. Update `aggregate_recommendation()` to include your agent's signal

---

## Signal Fusion (How The Final Recommendation Works)

The orchestrator uses **confidence-weighted ensemble averaging**:

```
For each completed agent:
  score = {"bullish": +1, "bearish": -1, "neutral": 0}[signal]
  weighted_contribution = score * confidence

composite = sum(weighted_contributions) / sum(confidences)

Final signal:
  composite > +0.2  -->  "bullish"
  composite < -0.2  -->  "bearish"
  otherwise         -->  "neutral"
```

**Example with 3 agents:**

| Agent | Signal | Confidence | Weight |
|-------|--------|------------|--------|
| Technical | bullish | 0.90 | +0.90 |
| Sentiment | bullish | 0.78 | +0.78 |
| Risk | bullish | 0.65 | +0.65 |

- Composite = (0.90 + 0.78 + 0.65) / (0.90 + 0.78 + 0.65) = **+1.00**
- Overall confidence = 2.33 / 3 = **0.777 (78%)**
- Final signal: **strong bullish**

---

## Validation Results (Mock Pipeline)

The mock runner passes all 9 integrity checks:

```
[PASS] technical_slice_populated
[PASS] sentiment_slice_populated
[PASS] risk_slice_populated
[PASS] handoff_log_has_3_entries
[PASS] handoff_order_correct
[PASS] context_accumulation
[PASS] final_recommendation_present
[PASS] no_errors
[PASS] session_metadata_intact
```

---

## What's Needed From Teammates

### From Teammate A (FastAPI / Technical Analysis):

1. **No code changes needed right now.** Your `sma_graph.py` and `trading_graph.py` outputs are already supported by the adapters.
2. **Future:** When you migrate logic into `agents/technical/`, have your graph return an `AgentResult` directly instead of a raw dict. This eliminates the adapter step.
3. **Question:** Does the `trading_graph` LLM prompt always include "Bias:" and "Confidence:" lines? The adapter parses those to extract structured signals. If the format varies, let us know.

### From Teammate B (Sentiment / Twitter):

1. **No code changes needed right now.** Your `truth_graph.py` output is already supported by the adapter.
2. **Future:** When you build `agents/sentiment/graph.py`, have it produce `AgentResult` natively.
3. **Alignment:** Your `confidence_score` (int 0-100) is normalized to float 0.0-1.0 in the shared state. Just be aware of this conversion.

### From Both:

- **Signal vocabulary:** Please stick to `"bullish"`, `"bearish"`, `"neutral"` in your outputs. These map directly to our `SignalValue` type.
- **New fields:** If you add new output fields, let us know so we can update the adapters.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Baton** | The `OrchestratorState` — the shared data object passed between agents |
| **Handoff** | The act of one agent completing its work and passing enriched state to the next |
| **Slice** | An agent's designated region in the state (e.g. `state.technical`) |
| **Adapter** | A pure function that translates domain-specific output into `AgentResult` |
| **Context Snapshot** | A summary of all completed agents' signals at a given handoff point |
| **Signal Fusion** | Confidence-weighted averaging of all agent signals into a final recommendation |
| **Blackboard Architecture** | A shared memory space where agents read/write to designated regions |
| **Mealy Machine** | A finite state machine where outputs depend on both current state AND input |
