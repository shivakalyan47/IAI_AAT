"""
backend/schemas.py — Re-exports shared models and defines any backend-only schemas.
Keeps the import surface clean and allows backend-specific additions later.
"""

from shared.models import (  # noqa: F401  (re-export)
    Character,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    SampleQA,
)
