# Multi-Agent Communication Layer

> **Feature Branch:** `feature/multi-agent-comms`
> **Owner:** Orchestration / State-Matching
> **Location:** `api/orchestration/` (fully isolated -- zero modifications to `api/core/`)
> **Status:** Core contracts + mock pipeline verified (9/9 checks passed)

---

## Why This Directory Exists

This package is **completely self-contained** to avoid merge conflicts with
teammates working on `api/core/`, `api/agents/`, and the graph files.

**What we DO:** Import base types from `core/schemas.py` (read-only).
**What we DON'T:** Modify any file outside `api/orchestration/`.

At merge time, the team can decide whether to promote these types into
`api/core/` or keep them here.

---

## What This Is

This layer is the **"Brain"** of the multi-agent system -- the shared state
and coordination logic that allows agents to communicate and hand off data
to each other without breaking.

**The Problem:** Each agent workflow (`sma_graph`, `trading_graph`, `truth_graph`)
currently uses its own private `TypedDict` state. They cannot read each other's
outputs, which means we cannot build multi-agent reasoning.

**The Solution:** A **blackboard architecture** with:
1. A shared state contract (`OrchestratorState`) -- the "baton" that flows through the pipeline
2. Adapter functions that translate each agent's private output into a common format (`AgentResult`)
3. A handoff protocol that records every data exchange with timestamps and context snapshots
4. A signal fusion engine that combines all agents' outputs into a final recommendation

---

## File Map

```
api/orchestration/
|-- __init__.py         Package init
|-- contracts.py        All orchestration-specific types (PhaseValue, AgentHandoff,
|                       AgentStatus, OrchestratorState). Imports base types from
|                       core/schemas.py READ-ONLY.
|-- adapters.py         Translates SMA/Trading/Truth outputs -> AgentResult
|-- engine.py           Baton-passing logic, error recording, signal fusion
|-- mock_runner.py      Standalone test pipeline with synthetic data
|-- MULTI_AGENT_COMMS.md   This file
```

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

## Architecture Overview

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

## Shared Contracts Reference

### AgentResult -- The Universal Agent Output

Every agent, regardless of what it does internally, must produce an `AgentResult`
(defined in `core/schemas.py` -- the team's shared contract):

```python
class AgentResult(TypedDict, total=False):
    status: StatusValue       # "pending" | "completed" | "failed" | "skipped"
    signal: SignalValue       # "bullish" | "bearish" | "neutral" | "mixed" | "insufficient_data"
    confidence: float         # 0.0 to 1.0 (normalized)
    summary: str              # human-readable explanation
    metrics: dict             # domain-specific numbers
    details: dict             # full traceability (includes raw_output)
    warnings: list[str]       # any caveats
```

### Orchestration-Specific Types (defined in contracts.py)

```python
# Cognitive pipeline phases
PhaseValue = Literal["perception", "context", "scoring", "decision", "execution"]

# Message envelope for baton-passing
class AgentHandoff(TypedDict, total=False):
    from_agent: str           # who sent it
    to_agent: str             # who receives it
    phase: PhaseValue         # pipeline stage
    timestamp: str            # ISO 8601
    payload: AgentResult      # the actual data
    context_snapshot: dict    # what the receiver will see

# The master baton
class OrchestratorState(TypedDict, total=False):
    session_id: str
    ticker: str
    run_timestamp: str
    technical: AgentResult    # each agent writes to exactly one slice
    sentiment: AgentResult
    fundamental: AgentResult
    risk: AgentResult
    agent_statuses: dict[str, AgentStatus]
    handoff_log: list[AgentHandoff]  # append-only audit trail
    final_recommendation: dict
    errors: list[AgentError]
    ...
```

### Confidence Scale

- **Range:** `0.0` to `1.0` (float)
- **If your source uses 0-100** (like truth_graph's `confidence_score`), divide by 100

### Signal Vocabulary

All agents must use: `"bullish"`, `"bearish"`, `"neutral"`, `"mixed"`, `"insufficient_data"`

---

## How To Use This (For Teammates)

### If you're building an agent workflow:

1. **Do your analysis however you want** (LLM, API, math)
2. **Return your output as a regular dict** (you already do this)
3. **We have adapters** in `orchestration/adapters.py` that translate your output into `AgentResult`
4. If you want to skip the adapter, just return an `AgentResult` directly

### If you want to test the pipeline:

```bash
cd api
python -m orchestration.mock_runner TSLA
```

### If you're adding a new agent:

1. Add a new slice to `OrchestratorState` in `orchestration/contracts.py`
2. Create an adapter in `orchestration/adapters.py`
3. Add a handoff step in `orchestration/engine.py`

---

## Signal Fusion (How The Final Recommendation Works)

Confidence-weighted ensemble averaging:

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

---

## What's Needed From Teammates

### From Teammate A (FastAPI / Technical Analysis):
1. **No code changes needed right now.**
2. **Question:** Does the `trading_graph` LLM always output "Bias:" and "Confidence:" lines? The adapter parses those.

### From Teammate B (Sentiment / Twitter):
1. **No code changes needed right now.**
2. **FYI:** Your `confidence_score` (int 0-100) is normalized to float 0.0-1.0 by the adapter.

### From Both:
- Stick to `"bullish"`, `"bearish"`, `"neutral"` signal strings
- Let us know if you add new output fields so we can update adapters

---

## Validation Results

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

## Glossary

| Term | Definition |
|------|-----------|
| **Baton** | The `OrchestratorState` -- the shared data object passed between agents |
| **Handoff** | The act of one agent completing its work and passing enriched state to the next |
| **Slice** | An agent's designated region in the state (e.g. `state.technical`) |
| **Adapter** | A pure function that translates domain-specific output into `AgentResult` |
| **Context Snapshot** | A summary of all completed agents' signals at a given handoff point |
| **Signal Fusion** | Confidence-weighted averaging of all agent signals into a final recommendation |
| **Blackboard Architecture** | A shared memory space where agents read/write to designated regions |
