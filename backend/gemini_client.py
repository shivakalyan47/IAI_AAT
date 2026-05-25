"""
backend/gemini_client.py — Thin async wrapper around the Gemini REST API.

Uses httpx for async HTTP — no Gemini SDK required, keeping dependencies minimal.
Handles timeouts, HTTP errors, and empty responses gracefully.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Gemini model to use. gemini-2.0-flash is fast and capable.
GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
REQUEST_TIMEOUT_SECONDS = 20.0


class GeminiError(Exception):
    """Raised when the Gemini API call fails for any reason."""
    pass


async def generate_response(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
    api_key: Optional[str] = None,
) -> str:
    """
    Call the Gemini generateContent endpoint and return the text response.

    Args:
        system_prompt: The persona/instruction system prompt.
        conversation_history: Prior turns in Gemini format (role/parts).
        user_message: The latest user message.
        api_key: Gemini API key. Falls back to GEMINI_API_KEY env var.

    Returns:
        The generated text string.

    Raises:
        GeminiError: On network failure, timeout, API error, or empty response.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise GeminiError(
            "GEMINI_API_KEY is not set. Add it to your .env file or environment."
        )

    url = f"{GEMINI_BASE_URL}/models/{GEMINI_MODEL}:generateContent?key={key}"

    # Build the messages array: history + current user message.
    messages = list(conversation_history)
    messages.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": messages,
        "generationConfig": {
            "temperature": 0.85,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        },
        "safetySettings": [
            # Relax safety thresholds slightly for historical/educational content.
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH",
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)

        if resp.status_code != 200:
            print("Gemini API error details:")
            print(resp.text)
            logger.error(
                "Gemini API returned HTTP %d: %s", resp.status_code, resp.text[:400]
            )
            raise GeminiError(f"Gemini API HTTP {resp.status_code}")
        


        data = resp.json()
        text = _extract_text(data)

        if not text:
            raise GeminiError("Gemini returned an empty response body.")

        return text

    except httpx.TimeoutException as exc:
        raise GeminiError(f"Gemini request timed out: {exc}") from exc
    except httpx.RequestError as exc:
        raise GeminiError(f"Network error calling Gemini: {exc}") from exc


def _extract_text(data: dict) -> str:
    """
    Safely navigate the Gemini response JSON to extract the text content.

    Gemini's response structure:
    {
      "candidates": [{
        "content": {
          "parts": [{"text": "..."}],
          "role": "model"
        },
        "finishReason": "STOP"
      }]
    }
    """
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if "text" in p]
        return " ".join(texts).strip()
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Failed to parse Gemini response structure: %s", exc)
        return ""
