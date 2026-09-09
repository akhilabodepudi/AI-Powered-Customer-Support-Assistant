from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)


class Citation(BaseModel):
    source: str
    section: str
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    confidence: Literal["high", "medium", "low"]
    citations: list[Citation]
    escalated: bool
    message_id: str


class FeedbackRequest(BaseModel):
    message_id: str
    helpful: bool
    comment: str | None = Field(default=None, max_length=500)


class EscalationRequest(BaseModel):
    conversation_id: str
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    summary: str = Field(min_length=5, max_length=1000)


class DocumentSummary(BaseModel):
    id: str
    title: str
    source: str
    chunk_count: int
    created_at: datetime


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

