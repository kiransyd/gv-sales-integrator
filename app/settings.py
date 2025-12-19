from __future__ import annotations

import logging
import sys
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


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
    READAI_MIN_DURATION_MINUTES: int = Field(default=5)

    # LLM (Gemini)
    LLM_PROVIDER: str = Field(default="gemini")
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro")

    # Slack
    SLACK_WEBHOOK_URL: str = Field(default="")
    SLACK_FORMAT_MODE: str = Field(
        default="text",
        description="Slack message format: 'text' (markdown, default, most compatible), 'blocks' (Block Kit), or 'attachments' (legacy). Note: All notifications now use markdown format regardless of this setting."
    )

    # Optional
    CREATE_FOLLOWUP_TASK: bool = Field(default=False)

    # Redis TTL configuration (in seconds)
    EVENT_TTL_SECONDS: int = Field(default=30 * 24 * 60 * 60)  # 30 days
    IDEMPOTENCY_TTL_SECONDS: int = Field(default=90 * 24 * 60 * 60)  # 90 days

    # Apollo.io
    APOLLO_API_KEY: str = Field(default="")
    APOLLO_CACHE_TTL_DAYS: int = Field(default=30)

    # ScraperAPI
    SCRAPER_API_KEY: str = Field(default="")
    SCRAPER_MAX_PAGES: int = Field(default=5)

    # BrandFetch API (for company logos)
    BRAND_FETCH_API: str = Field(default="")
    BRAND_FETCH_CLIENT_ID: str = Field(default="")

    # Enrichment Settings
    ENABLE_AUTO_ENRICH_CALENDLY: bool = Field(default=False)
    ENABLE_WEBSITE_SCRAPING: bool = Field(default=True)
    ENRICH_SECRET_KEY: str = Field(default="")

    # Apollo Zoho Field Mappings
    ZCF_APOLLO_JOB_TITLE: str = Field(default="")
    ZCF_APOLLO_SENIORITY: str = Field(default="")
    ZCF_APOLLO_DEPARTMENT: str = Field(default="")
    ZCF_APOLLO_LINKEDIN_URL: str = Field(default="")
    ZCF_APOLLO_PHONE: str = Field(default="")
    ZCF_APOLLO_COMPANY_SIZE: str = Field(default="")
    ZCF_APOLLO_COMPANY_REVENUE: str = Field(default="")
    ZCF_APOLLO_COMPANY_INDUSTRY: str = Field(default="")
    ZCF_APOLLO_COMPANY_FOUNDED_YEAR: str = Field(default="")
    ZCF_APOLLO_COMPANY_FUNDING_STAGE: str = Field(default="")
    ZCF_APOLLO_COMPANY_FUNDING_TOTAL: str = Field(default="")
    ZCF_APOLLO_TECH_STACK: str = Field(default="")

    def validate_configuration(self) -> list[str]:
        """
        Validates settings and returns list of warnings/errors.
        Critical errors should prevent startup.
        Returns list of warning/error messages.
        """
        errors = []
        warnings = []

        # Critical: Redis
        if not self.REDIS_URL:
            errors.append("REDIS_URL is required")

        # Critical: LLM (if not in DRY_RUN, we need Gemini)
        if not self.DRY_RUN and not self.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY is required when DRY_RUN=false")

        # Critical: Zoho (if not in DRY_RUN)
        if not self.DRY_RUN:
            if not self.ZOHO_CLIENT_ID:
                errors.append("ZOHO_CLIENT_ID is required when DRY_RUN=false")
            if not self.ZOHO_CLIENT_SECRET:
                errors.append("ZOHO_CLIENT_SECRET is required when DRY_RUN=false")
            if not self.ZOHO_REFRESH_TOKEN:
                errors.append("ZOHO_REFRESH_TOKEN is required when DRY_RUN=false")
            if self.ZOHO_DC not in ["us", "au", "eu", "in"]:
                errors.append(f"ZOHO_DC must be one of: us, au, eu, in (got: {self.ZOHO_DC})")

        # Warning: Webhook authentication
        if not self.CALENDLY_SIGNING_KEY:
            warnings.append("CALENDLY_SIGNING_KEY not set - Calendly webhooks will not be authenticated")
        if not self.READAI_SHARED_SECRET:
            warnings.append("READAI_SHARED_SECRET not set - Read.ai webhooks will not be authenticated")

        # Warning: Slack alerts
        if not self.SLACK_WEBHOOK_URL:
            warnings.append("SLACK_WEBHOOK_URL not set - failure alerts will not be sent")

        # Warning: Zoho custom fields (only check a few critical ones)
        if not self.DRY_RUN:
            zcf_fields_missing = []
            if not self.ZCF_DEMO_DATETIME:
                zcf_fields_missing.append("ZCF_DEMO_DATETIME")
            if not self.ZCF_LEAD_INTEL:
                zcf_fields_missing.append("ZCF_LEAD_INTEL")
            if not self.ZCF_MEDDIC_METRICS:
                zcf_fields_missing.append("ZCF_MEDDIC_METRICS")

            if zcf_fields_missing:
                warnings.append(
                    f"Critical Zoho custom fields not configured: {', '.join(zcf_fields_missing)}. "
                    "LLM-extracted data will not be saved to these fields."
                )

        # Combine errors and warnings
        all_messages = []
        if errors:
            all_messages.extend([f"ERROR: {e}" for e in errors])
        if warnings:
            all_messages.extend([f"WARNING: {w}" for w in warnings])

        return all_messages

    def validate_and_fail_fast(self) -> None:
        """
        Validates configuration and exits if critical errors found.
        Logs warnings but continues.
        """
        messages = self.validate_configuration()

        errors = [msg for msg in messages if msg.startswith("ERROR:")]
        warnings = [msg for msg in messages if msg.startswith("WARNING:")]

        if warnings:
            logger.warning("Configuration warnings detected:")
            for warning in warnings:
                logger.warning("  %s", warning)

        if errors:
            logger.error("Critical configuration errors detected:")
            for error in errors:
                logger.error("  %s", error)
            logger.error("Application cannot start. Please fix configuration errors above.")
            sys.exit(1)

        logger.info("Configuration validation passed")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


