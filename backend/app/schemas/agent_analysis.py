from datetime import datetime

from pydantic import BaseModel


class AgentAnalysisRead(BaseModel):
    """One Gemini agent's narrative research opinion (Phase 12) -- a
    research opinion, never a BUY/SELL instruction, same principle as
    RecommendationRead itself. `details` is a small set of short, labeled
    fields specific to that role (see AgentResearchService's per-role
    schemas for the exact keys) -- not a free-text paragraph."""

    role: str
    call: str
    confidence: int
    details: dict[str, str]
    model: str
    created_at: datetime
