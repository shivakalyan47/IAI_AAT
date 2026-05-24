"""
backend/fallback.py — Fallback response system for when Gemini fails or returns
low-quality responses.

Strategy (in order of preference):
  1. Keyword/token overlap similarity matching against stored sample Q&A.
  2. Safe, generic in-character reply that never breaks persona.

Deliberately lightweight — no external ML libraries required.
"""

import re
import logging
from shared.models import Character

logger = logging.getLogger(__name__)

# Minimum token overlap ratio to consider a Q&A match usable.
_SIMILARITY_THRESHOLD = 0.25

# Generic fallback templates per character id (optional — falls back to the
# universal template if not present).
_GENERIC_TEMPLATES: dict[str, str] = {
    "tesla": (
        "Hm. You touch upon a matter that requires careful contemplation. "
        "The forces at work here are subtle — like the interplay of resonance "
        "and frequency that governs all nature. Let me reflect further before "
        "I speak with the precision this question deserves."
    ),
    "curie": (
        "That is a question worth examining carefully. In my laboratory I learned "
        "that jumping to conclusions before the evidence is complete leads only to "
        "wasted effort. Let us approach this methodically — what do we actually know, "
        "and what remains to be demonstrated?"
    ),
    "turing": (
        "Interesting. Let me reduce the problem to its essentials, as one must with "
        "any question worth answering. I suspect there is a logical structure beneath "
        "what you are asking that, once identified, will make the answer quite clear. "
        "Give me a moment to think it through properly."
    ),
    "darwin": (
        "I confess I must observe more carefully before I venture an opinion. "
        "The naturalist's first duty is to resist hasty conclusions. "
        "Nature has a way of surprising those who assume they already understand her. "
        "What evidence do we have before us?"
    ),
    "lovelace": (
        "That is a question I find myself turning over with great interest. "
        "There is a structure to it — perhaps mathematical, perhaps philosophical — "
        "that I have not yet fully discerned. I would rather give you a considered "
        "answer than a hasty one. The Analytical Engine, after all, requires precise "
        "instructions, and so does careful thought."
    ),
}

_UNIVERSAL_FALLBACK = (
    "You raise a matter that gives me pause. I find myself needing to reflect "
    "carefully before I can do justice to your question. My experience and "
    "knowledge lead me to believe there is much here worth examining — "
    "but I would rather think it through than speak carelessly."
)


def _tokenize(text: str) -> set[str]:
    """
    Convert text to a set of lowercase alphabetic tokens (3+ chars).
    Simple but effective for keyword overlap without external dependencies.
    """
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return set(tokens)


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union


def _find_best_qa_match(
    user_message: str,
    character: Character,
) -> tuple[str | None, float]:
    """
    Find the best matching sample Q&A for the user message.

    Returns:
        Tuple of (answer_string | None, similarity_score).
        Returns (None, 0.0) if no match meets the threshold.
    """
    user_tokens = _tokenize(user_message)
    best_answer: str | None = None
    best_score: float = 0.0

    for qa in character.sample_qa:
        question_tokens = _tokenize(qa.question)
        score = _jaccard_similarity(user_tokens, question_tokens)
        logger.debug(
            "Fallback similarity: %.3f for Q: '%s'", score, qa.question[:60]
        )
        if score > best_score:
            best_score = score
            best_answer = qa.answer

    if best_score >= _SIMILARITY_THRESHOLD:
        return best_answer, best_score

    return None, best_score


def _is_low_quality(response: str) -> bool:
    """
    Heuristic checks for a low-quality or broken Gemini response.

    Flags responses that:
    - Are very short (< 20 chars).
    - Contain AI self-identification phrases.
    - Contain refusal boilerplate.
    """
    if not response or len(response.strip()) < 20:
        return True

    ai_phrases = [
        "i am an ai",
        "i'm an ai",
        "as an ai",
        "language model",
        "i cannot",
        "i'm unable",
        "i am unable",
        "i don't have the ability",
        "as a large language",
        "i am gemini",
        "i am claude",
    ]
    lower = response.lower()
    for phrase in ai_phrases:
        if phrase in lower:
            logger.warning("Low-quality response detected: AI phrase '%s' found.", phrase)
            return True

    return False


def get_fallback_response(
    user_message: str,
    character: Character,
    reason: str = "unknown",
) -> tuple[str, str]:
    """
    Generate a fallback response when Gemini is unavailable or low-quality.

    Args:
        user_message: The user's original message.
        character: The selected Character object.
        reason: Why we fell back (for logging/metadata).

    Returns:
        Tuple of (response_text, source_label).
        source_label is "fallback_qa" or "fallback_generic".
    """
    logger.info(
        "Fallback triggered for character '%s'. Reason: %s", character.id, reason
    )

    # Try Q&A similarity match first.
    answer, score = _find_best_qa_match(user_message, character)
    if answer:
        logger.info("Fallback Q&A match found (score=%.3f).", score)
        return answer, "fallback_qa"

    # Use character-specific generic template if available.
    generic = _GENERIC_TEMPLATES.get(character.id, _UNIVERSAL_FALLBACK)
    logger.info("No Q&A match found. Using generic fallback.")
    return generic, "fallback_generic"
