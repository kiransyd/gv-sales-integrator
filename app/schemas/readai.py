from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReadAIMeetingCompleted(BaseModel):
    meeting_id: str = Field(default="")
    title: str = Field(default="")
    datetime: str = Field(default="")
    duration_minutes: int = Field(default=0)
    attendees: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = Field(default="")
    transcript: str = Field(default="")
    recording_url: str = Field(default="")



