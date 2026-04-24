"""Groq LLM sentiment indicator with hard JSON validation and fallback."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config import GROQ_API_KEY, GROQ_MODEL

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a financial sentiment analyzer. Given a stock/crypto ticker symbol, \
provide your current market sentiment assessment.

You MUST respond with ONLY a valid JSON object in this exact format:
{"signal": "buy" or "sell" or "hold", "confidence": 0-100, "reasoning": "one sentence"}

Rules:
- signal must be exactly one of: "buy", "sell", "hold"
- confidence must be an integer from 0 to 100
- reasoning must be a single concise sentence
- Do NOT include any text before or after the JSON object
- Do NOT use markdown formatting
"""

_FALLBACK_SIGNAL = {
    "signal": "hold",
    "confidence": 50,
    "reasoning": "Sentiment analysis unavailable; defaulting to neutral hold.",
}


def _parse_llm_response(text: str) -> dict | None:
    """Try to extract valid JSON from LLM response. Returns None on failure."""
    # Try direct parse first
    text = text.strip()
    try:
        parsed = json.loads(text)
        if _validate_signal(parsed):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Try to find JSON in the response
    json_match = re.search(r'\{[^{}]*\}', text)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if _validate_signal(parsed):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    return None


def _validate_signal(data: dict) -> bool:
    """Validate that parsed JSON matches our schema exactly."""
    if not isinstance(data, dict):
        return False
    if data.get("signal") not in ("buy", "sell", "hold"):
        return False
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 100):
        return False
    if not isinstance(data.get("reasoning"), str) or not data["reasoning"].strip():
        return False
    return True


def run_sentiment_indicator(asset: str, context: str = "") -> dict:
    """
    Run Groq LLM sentiment analysis for the given asset.
    Hard-validates output. Falls back to hold/50 on ANY failure.

    Returns:
        {asset, signal, confidence_score, reasoning, timestamp}
    """
    now = datetime.now(timezone.utc).isoformat()

    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set — returning fallback signal for %s", asset)
        return {
            "asset": asset,
            "signal": _FALLBACK_SIGNAL["signal"],
            "confidence_score": _FALLBACK_SIGNAL["confidence"],
            "reasoning": "Groq API key not configured. " + _FALLBACK_SIGNAL["reasoning"],
            "timestamp": now,
        }

    try:
        llm = ChatGroq(
            model=GROQ_MODEL,
            api_key=GROQ_API_KEY,
            temperature=0.1,
            max_tokens=200,
            timeout=10,
        )

        user_message = f"Analyze the current market sentiment for {asset}."
        if context:
            user_message += f" Additional context: {context}"

        response = llm.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ])

        parsed = _parse_llm_response(response.content)
        if parsed is None:
            logger.warning(
                "LLM output failed schema validation for %s. Raw: %s",
                asset, response.content[:200],
            )
            return {
                "asset": asset,
                "signal": _FALLBACK_SIGNAL["signal"],
                "confidence_score": _FALLBACK_SIGNAL["confidence"],
                "reasoning": f"LLM response did not match required schema. {_FALLBACK_SIGNAL['reasoning']}",
                "timestamp": now,
            }

        return {
            "asset": asset,
            "signal": parsed["signal"],
            "confidence_score": int(parsed["confidence"]),
            "reasoning": parsed["reasoning"],
            "timestamp": now,
        }

    except Exception as exc:
        logger.error("Sentiment analysis failed for %s: %s", asset, exc, exc_info=True)
        return {
            "asset": asset,
            "signal": _FALLBACK_SIGNAL["signal"],
            "confidence_score": _FALLBACK_SIGNAL["confidence"],
            "reasoning": f"Analysis error: {type(exc).__name__}. {_FALLBACK_SIGNAL['reasoning']}",
            "timestamp": now,
        }
