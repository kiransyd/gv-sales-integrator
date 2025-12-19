from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class IntercomWebhook(BaseModel):
    """Top-level Intercom webhook payload"""
    type: str = Field(default="")
    topic: str = Field(default="")
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: int = Field(default=0)


class IntercomCompany(BaseModel):
    """Intercom company data"""
    type: str = Field(default="company")
    id: str = Field(default="")
    name: str = Field(default="")
    website: str = Field(default="")
    company_id: str = Field(default="")
    size: int | None = Field(default=None)
    industry: str = Field(default="")


class IntercomContact(BaseModel):
    """Intercom contact/user data"""
    type: str = Field(default="contact")
    id: str = Field(default="")
    external_id: str = Field(default="")
    email: str = Field(default="")
    name: str = Field(default="")
    phone: str = Field(default="")
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    companies: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)


class IntercomTag(BaseModel):
    """Intercom tag data"""
    type: str = Field(default="tag")
    id: str = Field(default="")
    name: str = Field(default="")
