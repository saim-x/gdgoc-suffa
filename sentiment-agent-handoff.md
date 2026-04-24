# Sentiment Agent Handoff

You are working on the backend of `gdgoc-suffa`, a multi-agent investment advisor system with an Expo frontend and FastAPI backend.

## Context

- The repo already has a basic backend MVP and a lightweight multi-agent folder structure.
- Current backend structure includes:
  - `api/core/`
    - `state.py`
    - `schemas.py`
    - `orchestrator.py`
  - `api/agents/technical/`
  - `api/agents/fundamental/`
  - `api/agents/sentiment/`
- There is already a simple technical MVP elsewhere in the backend, but the project is being reorganized toward domain-based agents.
- We want to avoid merge conflicts and design drift.

## Important Architecture Intent

- This is not just a single-symbol analyzer.
- Long term, the system should support:
  - market-level agents
  - symbol-level agents
  - candidate generation
  - ranking/allocation
- For now, we are keeping logic light and focusing on clean structure and contracts.

## Your Ownership

- You are responsible for the sentiment/Twitter side only.
- Work primarily inside:
  - `api/agents/sentiment/`
- Avoid editing technical files unless absolutely necessary.
- Avoid changing shared contracts in `api/core/` unless required and keep such changes minimal.

## How The Team Is Dividing Work

- Technical person owns technical analysis logic
- You own sentiment / Twitter / market-social signal logic
- Shared coordination will happen later through shared state + orchestrator

## Key Design Rule

- We want one shared top-level app state, but each domain should write only to its own slice.
- Do not invent a separate isolated app state for sentiment.
- Your code should be able to plug into a shared orchestrator later.

## State Philosophy

- Shared app state should eventually support concepts like:
  - user profile / balance
  - market signals
  - themes
  - candidate symbols
  - symbol analyses
  - ranked opportunities
- Your sentiment agent should mainly contribute to market-level context, for example:
  - sentiment signals
  - themes
  - possibly candidate symbols
  - optionally symbol-level sentiment later

## Your Task

- Create a basic sentiment agent structure only.
- Keep it simple and merge-friendly.
- Do not build deep production logic yet.
- Prefer placeholders, interfaces, and small starter code over a huge implementation.

## What To Build

1. In `api/agents/sentiment/`, create or flesh out:
   - `graph.py`
   - `schemas.py`
   - any tiny helper file only if truly needed
2. Define a minimal sentiment workflow shape:
   - a few node functions
   - a small graph builder
   - clear output contract
3. Make the code easy to merge later with technical and fundamental agents.
4. If you need shared types, prefer adding minimal shared definitions in `api/core/` rather than coupling to technical code.

## Constraints

- Do not refactor the whole backend.
- Do not move unrelated files.
- Do not overwrite technical-agent work.
- Do not create breaking changes to the current MVP routes unless necessary.
- Keep names and contracts stable and boring rather than clever.

## Preferred Sentiment Workflow Shape

- A graph with simple nodes such as:
  - `collect_social_context`
  - `extract_sentiment_signal`
  - `summarize_sentiment_output`
- The graph can be placeholder or mocked for now if live Twitter integration is too early.
- It should still reflect the intended architecture.

## Preferred Output Style

- Return structured data, not just free text.
- Outer shape should be stable and extensible, for example fields like:
  - `status`
  - `signal`
  - `confidence`
  - `summary`
  - `metrics`
  - `warnings`
  - optionally `affected_symbols` / `affected_sectors`

## Merge-Safety Rules

- Only write to sentiment-owned files unless necessary.
- Keep shared schema changes minimal and additive.
- Do not remove or rename public/shared keys casually.
- Favor nested extensible fields like `details` or `metrics` instead of reshaping everything.

## What Good Work Looks Like

- Clean starter structure
- Small, readable node functions
- Stable schema/output contract
- Minimal assumptions
- Easy for another orchestrator to call later

## Final Summary Expectations

At the end, summarize:

- what files you changed
- what sentiment graph shape you introduced
- what state/output contract you assumed
- any shared-contract decisions that the team should explicitly confirm before more coding
