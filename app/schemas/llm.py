from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CalendlyLeadIntel(BaseModel):
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    company_name: str = Field(default="")
    company_website: str = Field(default="")
    company_type: str = Field(default="")
    company_description: str = Field(default="")
    industry: str = Field(default="")  # Extract from Q&A or infer from company type
    team_size: str = Field(default="")
    country: str = Field(default="")
    state_or_region: str = Field(default="")
    city: str = Field(default="")
    phone: str = Field(default="")  # Extract phone from Q&A if mentioned
    referred_by: str = Field(default="")  # Extract from Q&A "How did they hear about us?"
    tools_in_use: str = Field(default="")
    stated_pain_points: str = Field(default="")
    stated_demo_objectives: str = Field(default="")
    additional_notes: str = Field(default="")
    demo_datetime_utc: str = Field(default="")
    demo_datetime_local: str = Field(default="")
    bant_budget_signal: str = Field(default="")
    bant_authority_signal: str = Field(default="")
    bant_need_signal: str = Field(default="")
    bant_timing_signal: str = Field(default="")
    qualification_gaps: str = Field(default="")
    recommended_discovery_questions: str = Field(default="")
    demo_focus_recommendations: str = Field(default="")
    sales_rep_cheat_sheet: str = Field(default="")


class MeddicOutput(BaseModel):
    metrics: str = Field(default="")
    economic_buyer: str = Field(default="")
    decision_criteria: str = Field(default="")
    decision_process: str = Field(default="")
    identified_pain: str = Field(default="")
    champion: str = Field(default="")
    competition: str = Field(default="")
    next_steps: str = Field(default="")
    risks: str = Field(default="")
    confidence: Literal["Cold", "Warm", "Hot", "Super-hot"] = Field(default="Cold")



