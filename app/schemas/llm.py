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


class YouTubeTranscriptSummary(BaseModel):
    """Structured summary of a YouTube video transcript"""

    # Core insights
    key_quotes: str = Field(
        default="",
        description="Notable quotes from the video (numbered list with line breaks)"
    )
    main_actions: str = Field(
        default="",
        description="Key actions, steps, or recommendations mentioned (numbered list with line breaks)"
    )
    lessons_learned: str = Field(
        default="",
        description="Lessons, insights, or takeaways from the video (numbered list with line breaks)"
    )
    key_topics: str = Field(
        default="",
        description="Main topics or themes discussed (numbered list with line breaks)"
    )
    summary: str = Field(
        default="",
        description="Brief overall summary of the video content (2-3 sentences)"
    )

    # Extended insights (optional, can be empty)
    people_and_companies_mentioned: str = Field(
        default="",
        description="Names, companies, brands referenced in the video (numbered list with line breaks)"
    )
    statistics_and_data_points: str = Field(
        default="",
        description="Numbers, metrics, research findings cited (numbered list with line breaks)"
    )
    tools_and_products_mentioned: str = Field(
        default="",
        description="Software, services, platforms discussed (numbered list with line breaks)"
    )
    resources_mentioned: str = Field(
        default="",
        description="Books, articles, websites, courses referenced (numbered list with line breaks)"
    )
    frameworks_and_models: str = Field(
        default="",
        description="Mental models, methodologies, frameworks explained (numbered list with line breaks)"
    )
    success_stories: str = Field(
        default="",
        description="Case studies, examples, success stories shared (numbered list with line breaks)"
    )
    common_mistakes: str = Field(
        default="",
        description="Pitfalls, mistakes to avoid, anti-patterns (numbered list with line breaks)"
    )
    content_type: str = Field(
        default="",
        description="Type of content (e.g., 'Tutorial', 'Interview', 'Case Study', 'Motivational')"
    )
    target_audience: str = Field(
        default="",
        description="Who this content is for (e.g., 'SaaS founders', 'Marketing professionals')"
    )
    sentiment_tone: str = Field(
        default="",
        description="Overall tone (e.g., 'Educational and practical', 'Inspirational', 'Critical analysis')"
    )



