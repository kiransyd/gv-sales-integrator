from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ApolloPersonData(BaseModel):
    """Person enrichment data from Apollo.io"""
    email: str = Field(default="")
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    title: str = Field(default="")
    seniority: str = Field(default="")  # Entry, Manager, Director, VP, C-Level
    department: str = Field(default="")  # Sales, Engineering, Marketing, etc.
    linkedin_url: str = Field(default="")
    phone_numbers: list[str] = Field(default_factory=list)
    employment_history: list[dict] = Field(default_factory=list)


class ApolloCompanyData(BaseModel):
    """Company enrichment data from Apollo.io"""
    name: str = Field(default="")
    domain: str = Field(default="")
    employee_count: str = Field(default="")  # e.g., "51-200", "201-500"
    revenue: str = Field(default="")  # e.g., "$10M-$50M"
    industry: str = Field(default="")
    founded_year: str = Field(default="")
    funding_stage: str = Field(default="")  # Seed, Series A/B/C, etc.
    funding_total: str = Field(default="")  # e.g., "$12.5M"
    technologies: list[str] = Field(default_factory=list)  # Tech stack
    linkedin_url: str = Field(default="")
    twitter_url: str = Field(default="")
    facebook_url: str = Field(default="")
    city: str = Field(default="")
    state: str = Field(default="")
    country: str = Field(default="")


class WebsiteIntelligence(BaseModel):
    """LLM-analyzed website intelligence"""
    value_proposition: str = Field(default="")
    target_market: str = Field(default="")
    products_services: str = Field(default="")
    pricing_model: str = Field(default="")
    recent_news: str = Field(default="")
    growth_signals: str = Field(default="")
    key_pain_points: str = Field(default="")
    competitors_mentioned: str = Field(default="")
    sales_insights: str = Field(default="")


class EnrichmentResult(BaseModel):
    """Combined enrichment result"""
    person_data: Optional[ApolloPersonData] = None
    company_data: Optional[ApolloCompanyData] = None
    website_intelligence: Optional[WebsiteIntelligence] = None
    enrichment_timestamp: str = Field(default="")
    data_sources: list[str] = Field(default_factory=list)  # ["apollo_person", "apollo_company", "website"]
