"""MiroFish-inspired swarm consensus processing for trading signals.

This layer adapts the action-and-round pattern used in MiroFish's
simulation runner to build a lightweight consensus signal from existing
indicator outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import pstdev
from typing import Any


_DIRECTION_MAP = {"buy": 1, "sell": -1, "hold": 0}
_DEFAULT_SOURCE_WEIGHTS = {
    "sma": 1.0,
    "rsi": 1.0,
    "sentiment": 1.25,
}


def _clamp_score(value: float) -> int:
    return int(max(0, min(100, round(value))))


@dataclass
class SwarmAction:
    """Single indicator action modeled after MiroFish agent actions."""

    round_num: int
    timestamp: str
    source_agent: str
    action_type: str
    confidence_score: int
    reasoning: str
    action_args: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "timestamp": self.timestamp,
            "source_agent": self.source_agent,
            "action_type": self.action_type,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "action_args": self.action_args,
        }


@dataclass
class SwarmRoundSummary:
    """Single-round swarm summary modeled after MiroFish round summaries."""

    round_num: int
    start_time: str
    end_time: str | None = None
    actions: list[SwarmAction] = field(default_factory=list)

    def add_action(self, action: SwarmAction) -> None:
        self.actions.append(action)

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_num": self.round_num,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "actions_count": len(self.actions),
            "actions": [a.to_dict() for a in self.actions],
        }


def _compute_recent_volatility_penalty(closes: list[float]) -> float:
    """Convert short-term volatility into a confidence penalty."""
    if len(closes) < 12:
        return 0.0

    recent = closes[-12:]
    returns = []
    for previous, current in zip(recent[:-1], recent[1:]):
        if previous <= 0:
            continue
        returns.append((current - previous) / previous)

    if len(returns) < 3:
        return 0.0

    volatility = pstdev(returns)
    return min(volatility * 2200, 14.0)


def _build_swarm_actions(indicator_results: list[dict], timestamp: str) -> list[SwarmAction]:
    actions: list[SwarmAction] = []

    for result in indicator_results:
        signal = str(result.get("signal", "hold")).lower()
        if signal not in _DIRECTION_MAP:
            signal = "hold"

        confidence = _clamp_score(float(result.get("confidence_score", 0)))
        source_agent = str(result.get("indicator", "unknown")).lower()

        actions.append(
            SwarmAction(
                round_num=1,
                timestamp=timestamp,
                source_agent=source_agent,
                action_type=signal,
                confidence_score=confidence,
                reasoning=str(result.get("reasoning", "")),
                action_args={"raw": result},
            )
        )

    return actions


def run_mirofish_processing_layer(
    asset: str,
    indicator_results: list[dict],
    closes: list[float],
    context: str = "",
) -> dict:
    """
    Build a MiroFish-style swarm consensus signal from base indicator outputs.

    Returns normalized signal shape:
      {asset, signal, confidence_score, reasoning, timestamp}
    """
    now = datetime.now(timezone.utc).isoformat()
    asset = asset.strip().upper()

    if not indicator_results:
        return {
            "asset": asset,
            "signal": "hold",
            "confidence_score": 0,
            "reasoning": "MiroFish layer received no upstream indicator actions.",
            "timestamp": now,
        }

    round_summary = SwarmRoundSummary(round_num=1, start_time=now)
    swarm_actions = _build_swarm_actions(indicator_results, now)
    for action in swarm_actions:
        round_summary.add_action(action)
    round_summary.end_time = datetime.now(timezone.utc).isoformat()

    weighted_direction = 0.0
    weighted_confidence = 0.0
    total_weight = 0.0
    non_hold_actions = 0
    vote_weights = {"buy": 0.0, "sell": 0.0, "hold": 0.0}

    for action in round_summary.actions:
        source_weight = _DEFAULT_SOURCE_WEIGHTS.get(action.source_agent, 0.9)
        confidence_factor = action.confidence_score / 100
        weight = source_weight * max(confidence_factor, 0.05)

        vote_weights[action.action_type] += weight
        weighted_direction += _DIRECTION_MAP[action.action_type] * weight
        weighted_confidence += action.confidence_score * source_weight
        total_weight += source_weight

        if action.action_type != "hold":
            non_hold_actions += 1

    if total_weight <= 0:
        total_weight = 1.0

    direction_strength = weighted_direction / max(sum(vote_weights.values()), 1e-9)
    dominant_weight = max(vote_weights.values()) if vote_weights else 0.0
    total_vote_weight = sum(vote_weights.values()) or 1.0
    consensus_ratio = dominant_weight / total_vote_weight
    participation_ratio = non_hold_actions / max(len(round_summary.actions), 1)
    avg_confidence = weighted_confidence / total_weight
    volatility_penalty = _compute_recent_volatility_penalty(closes)

    if direction_strength >= 0.18:
        signal = "buy"
    elif direction_strength <= -0.18:
        signal = "sell"
    else:
        signal = "hold"

    context_bonus = 3.0 if context.strip() else 0.0
    confidence_score = _clamp_score(
        avg_confidence * 0.58
        + consensus_ratio * 27
        + participation_ratio * 12
        + context_bonus
        - volatility_penalty
    )

    if signal == "hold":
        confidence_score = min(confidence_score, 72)

    vote_summary = (
        f"buy={vote_weights['buy']:.2f}, "
        f"sell={vote_weights['sell']:.2f}, "
        f"hold={vote_weights['hold']:.2f}"
    )
    reasoning = (
        "MiroFish swarm layer synthesized indicator actions into a one-round consensus; "
        f"direction_strength={direction_strength:.2f}, consensus={consensus_ratio:.2f}, "
        f"participation={participation_ratio:.2f}, volatility_penalty={volatility_penalty:.2f}. "
        f"Weighted votes: {vote_summary}."
    )

    return {
        "asset": asset,
        "signal": signal,
        "confidence_score": confidence_score,
        "reasoning": reasoning,
        "timestamp": now,
        "swarm_round": round_summary.to_dict(),
    }

