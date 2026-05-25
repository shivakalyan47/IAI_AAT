"""
backend/main.py — FastAPI application entry point.

Endpoints:
  GET  /characters        → List all available historical characters.
  POST /chat              → Send a message and receive an in-character reply.
  GET  /health            → Simple health check.
"""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Path bootstrap — allow running from project root OR backend/ directory.
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

load_dotenv(dotenv_path=_project_root / ".env")

from backend.fallback import get_fallback_response, _is_low_quality  # noqa: E402
from backend.gemini_client import GeminiError, generate_response  # noqa: E402
from backend.prompt_builder import build_conversation_history, build_system_prompt  # noqa: E402
from shared.models import Character, ChatRequest, ChatResponse  # noqa: E402

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Era-Bound Historical Figure Chatbot API",
    description="Chat with historical figures from science and technology.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict in production.
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Load character data at startup — fail fast if the file is missing/invalid.
# ---------------------------------------------------------------------------
_CHARACTERS_FILE = Path(__file__).parent / "characters.json"


def _load_characters() -> dict[str, Character]:
    if not _CHARACTERS_FILE.exists():
        logger.critical("characters.json not found at %s", _CHARACTERS_FILE)
        raise RuntimeError(f"characters.json not found at {_CHARACTERS_FILE}")

    with open(_CHARACTERS_FILE, "r", encoding="utf-8") as f:
        raw: list[dict] = json.load(f)

    return {item["id"]: Character(**item) for item in raw}


CHARACTERS: dict[str, Character] = _load_characters()
logger.info("Loaded %d characters: %s", len(CHARACTERS), list(CHARACTERS.keys()))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"])
async def health_check() -> dict:
    """Simple liveness probe."""
    return {"status": "ok", "characters_loaded": len(CHARACTERS)}


@app.get("/characters", tags=["characters"])
async def list_characters() -> list[dict]:
    """
    Return the list of available historical figures.
    Returns a simplified view (no sample_qa) suitable for the landing page.
    """
    return [
        {
            "id": c.id,
            "name": c.name,
            "era": c.era,
            "domain": c.domain,
            "bio": c.bio,
            "avatar_emoji": c.avatar_emoji,
        }
        for c in CHARACTERS.values()
    ]


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a user message and return an in-character historical figure response.

    Flow:
      1. Validate character exists.
      2. Build system prompt from character metadata.
      3. Call Gemini with full conversation history.
      4. If Gemini fails or returns low-quality response → fallback.
      5. Return response with source metadata.
    """
    character = CHARACTERS.get(request.character_id)
    if not character:
        raise HTTPException(
            status_code=404,
            detail=f"Character '{request.character_id}' not found. "
                   f"Available: {list(CHARACTERS.keys())}",
        )

    system_prompt = build_system_prompt(character)
    history_for_gemini = build_conversation_history(
        [msg.model_dump() for msg in request.history]
    )

    # --- Try Gemini ---
    error_message = None
    try:
        raw_reply = await generate_response(
            system_prompt=system_prompt,
            conversation_history=history_for_gemini,
            user_message=request.message,
        )

        if _is_low_quality(raw_reply):
            logger.warning(
                "Gemini returned low-quality response for '%s'. Triggering fallback.",
                character.id,
            )

            reply, source = get_fallback_response(
                request.message,
                character,
                reason="low_quality",
            )
        else:
            reply, source = raw_reply, "gemini"

    except GeminiError as exc:
        logger.error("Gemini error for '%s': %s", character.id, exc)

        error_message = str(exc)

        reply, source = get_fallback_response(
            request.message,
            character,
            reason=error_message,
        )

    return ChatResponse(
        reply=reply,
        source=source,
        character_id=character.id,
        error=error_message,
    )
