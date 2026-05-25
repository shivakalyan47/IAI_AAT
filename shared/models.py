"""
shared/models.py — Shared data models used by both backend and (optionally) frontend.
"""

from pydantic import BaseModel
from typing import Optional


class SampleQA(BaseModel):
    question: str
    answer: str


class Character(BaseModel):
    id: str
    name: str
    era: str
    domain: str
    bio: str
    speaking_style: str
    knowledge_limits: str
    avatar_emoji: str
    sample_qa: list[SampleQA]


class ChatMessage(BaseModel):
    role: str          # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    character_id: str
    message: str
    history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    source: str        # "gemini" | "fallback_qa" | "fallback_generic"
    character_id: str
    error: Optional[str] = None
