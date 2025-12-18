from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    ENV: str = Field(default="dev")  # dev|prod
    LOG_LEVEL: str = Field(default="INFO")  # INFO|DEBUG
    BASE_URL: str = Field(default="http://localhost:8000")

    # Dev-only
    ALLOW_DEBUG_ENDPOINTS: bool = Field(default=False)

    # Redis / Queue
    REDIS_URL: str = Field(default="redis://redis:6379/0")
    RQ_QUEUE_NAME: str = Field(default="default")

    # DRY_RUN (avoid writing to Zoho)
    DRY_RUN: bool = Field(default=True)

    # Zoho CRM
    ZOHO_DC: str = Field(default="au")  # au|us|eu|in
    ZOHO_CLIENT_ID: str = Field(default="")
    ZOHO_CLIENT_SECRET: str = Field(default="")
    ZOHO_REFRESH_TOKEN: str = Field(default="")
    # Only needed once to exchange a Self Client grant token into a refresh token.
    ZOHO_REDIRECT_URI: str = Field(default="")
    ZOHO_LEADS_MODULE: str = Field(default="Leads")
    ZOHO_OWNER_ID: str = Field(default="")
    ZOHO_LEAD_STATUS_FIELD: str = Field(default="Lead_Status")
    STATUS_DEMO_BOOKED: str = Field(default="Demo Booked")
    STATUS_DEMO_COMPLETE: str = Field(default="Demo Complete")
    STATUS_DEMO_CANCELED: str = Field(default="Demo Canceled")
    STATUS_DEMO_NO_SHOW: str = Field(default="Demo No-show")

    # Zoho Custom Field API Names (must be set by user)
    ZCF_DEMO_DATETIME: str = Field(default="")
    ZCF_DEMO_TIMEZONE: str = Field(default="")
    ZCF_CALENDLY_INVITEE_URI: str = Field(default="")
    ZCF_CALENDLY_EVENT_URI: str = Field(default="")
    ZCF_CALENDLY_QA: str = Field(default="")
    ZCF_LEAD_INTEL: str = Field(default="")
    
    # Calendly LLM-extracted fields (map to your Zoho custom field API names)
    ZCF_PAIN_POINTS: str = Field(default="")
    ZCF_TEAM_MEMBERS: str = Field(default="")
    ZCF_TOOLS_CURRENTLY_USED: str = Field(default="")
    ZCF_DEMO_OBJECTIVES: str = Field(default="")
    ZCF_DEMO_FOCUS_RECOMMENDATION: str = Field(default="")
    ZCF_DISCOVERY_QUESTIONS: str = Field(default="")
    ZCF_SALES_REP_CHEAT_SHEET: str = Field(default="")
    ZCF_COMPANY_TYPE: str = Field(default="")
    ZCF_COMPANY_DESCRIPTION: str = Field(default="")
    ZCF_QUALIFICATION_GAPS: str = Field(default="")
    ZCF_BANT_BUDGET: str = Field(default="")
    ZCF_BANT_AUTHORITY: str = Field(default="")
    ZCF_BANT_NEED: str = Field(default="")
    ZCF_BANT_TIMING: str = Field(default="")
    ZCF_REFERRED_BY: str = Field(default="")  # Custom field for "Referred by" if different from standard
    ZCF_MEDDIC_METRICS: str = Field(default="")
    ZCF_MEDDIC_ECONOMIC_BUYER: str = Field(default="")
    ZCF_MEDDIC_DECISION_CRITERIA: str = Field(default="")
    ZCF_MEDDIC_DECISION_PROCESS: str = Field(default="")
    ZCF_MEDDIC_IDENTIFIED_PAIN: str = Field(default="")
    ZCF_MEDDIC_CHAMPION: str = Field(default="")
    ZCF_MEDDIC_COMPETITION: str = Field(default="")
    ZCF_MEDDIC_CONFIDENCE: str = Field(default="")

    # Calendly
    CALENDLY_SIGNING_KEY: str = Field(default="")
    CALENDLY_EVENT_TYPE_URI: str = Field(default="")
    CALENDLY_API_TOKEN: str = Field(default="")

    # Read.ai
    READAI_SHARED_SECRET: str = Field(default="")
    READAI_CUSTOMER_DOMAINS: str = Field(default="govisually.com,clockworkstudio.com")
    READAI_MIN_DURATION_MINUTES: int = Field(default=10)

    # LLM (Gemini)
    LLM_PROVIDER: str = Field(default="gemini")
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro")

    # Slack
    SLACK_WEBHOOK_URL: str = Field(default="")

    # Optional
    CREATE_FOLLOWUP_TASK: bool = Field(default=False)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


