from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CalendlyWebhook(BaseModel):
    event: str = Field(default="")
    payload: dict[str, Any] = Field(default_factory=dict)


class CalendlyInvitee(BaseModel):
    email: str = Field(default="")
    name: str = Field(default="")
    uri: str = Field(default="")
    uuid: str = Field(default="")


class CalendlyEvent(BaseModel):
    uri: str = Field(default="")
    uuid: str = Field(default="")
    start_time: str = Field(default="")
    timezone: str = Field(default="")


