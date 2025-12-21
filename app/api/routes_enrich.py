from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.services.event_store_service import new_event_id, set_event_status, store_incoming_event
from app.services.llm_service import analyze_youtube_transcript
from app.services.rq_service import default_retry, get_queue
from app.services.scraper_service import scrape_website, scrape_youtube_transcript
from app.settings import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class EnrichLeadRequest(BaseModel):
    """Request to enrich a lead"""
    lead_id: str = Field(default="", description="Zoho Lead ID (optional if email provided)")
    email: str = Field(description="Lead email address (required)")


class ScrapeWebsiteRequest(BaseModel):
    """Request to scrape a website"""
    domain: str = Field(description="Domain to scrape (e.g., 'nike.com', 'deputy.com')")


class ScrapeYouTubeRequest(BaseModel):
    """Request to scrape a YouTube video transcript"""
    video_url: str = Field(description="YouTube video URL (any format: youtube.com/watch?v=..., youtu.be/..., etc.)")


@router.post("/enrich/lead")
async def enrich_lead(
    request: EnrichLeadRequest,
    x_enrich_secret: str = Header(None, alias="X-Enrich-Secret"),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Manual lead enrichment endpoint.

    Called by Zoho button click or API integrations.
    Enriches lead with Apollo + Website intelligence.
    """
    # Verify secret key
    if settings.ENRICH_SECRET_KEY and x_enrich_secret != settings.ENRICH_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid enrichment secret key")

    if not request.email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Create event for tracking
    event_id = new_event_id()
    idempotency_key = f"enrich:{request.email.lower()}"

    payload = {
        "email": request.email,
        "lead_id": request.lead_id,
    }

    store_incoming_event(
        event_id=event_id,
        source="manual_enrich",
        event_type="enrich_lead",
        external_id=request.email,
        idempotency_key=idempotency_key,
        payload=payload,
    )

    # Enqueue enrichment job
    try:
        q = get_queue()
        q.enqueue(
            "app.jobs.enrich_jobs.process_manual_enrich_job",
            event_id,
            job_id=f"{idempotency_key}:{event_id}",  # Unique job ID
            retry=default_retry(),
        )
        set_event_status(event_id, "queued")
    except Exception as e:  # noqa: BLE001
        set_event_status(event_id, "failed", last_error=f"enqueue_failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to enqueue enrichment job") from e

    logger.info("Enrichment queued for: %s (event_id: %s)", request.email, event_id)

    return {
        "ok": True,
        "queued": True,
        "event_id": event_id,
        "message": f"Lead enrichment queued for {request.email}. Check back in 30-60 seconds.",
    }


@router.post("/scrape/website")
async def scrape_website_endpoint(
    request: ScrapeWebsiteRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Scrape a website and return sales intelligence.

    Uses Crawl4AI (free) with ScraperAPI fallback.
    Returns immediately with website intelligence analysis.

    Public endpoint - no authentication required.

    Example:
        POST /scrape/website
        {
            "domain": "deputy.com"
        }
    """
    # No authentication required for website scraping

    if not request.domain:
        raise HTTPException(status_code=400, detail="Domain is required")

    # Clean domain
    domain = request.domain.strip().lower()
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.replace("www.", "")
    domain = domain.rstrip("/")

    logger.info("Scraping website via API: %s", domain)

    # Scrape website
    try:
        intelligence = scrape_website(domain)

        if not intelligence:
            return {
                "ok": False,
                "error": "Failed to scrape website",
                "domain": domain,
            }

        # Return the intelligence as a dict (include all fields, even defaults)
        return {
            "ok": True,
            "domain": domain,
            "intelligence": intelligence.model_dump(exclude_unset=False, exclude_defaults=False, exclude_none=False),
        }

    except Exception as e:  # noqa: BLE001
        logger.error("Website scraping failed for %s: %s", domain, e)
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}") from e


@router.post("/scrape/youtube")
async def scrape_youtube_endpoint(
    request: ScrapeYouTubeRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Scrape a YouTube video transcript.
    
    Uses Crawl4AI to extract transcript from YouTube videos.
    Returns the transcript text along with video metadata.
    
    Public endpoint - no authentication required.
    
    Example:
        POST /scrape/youtube
        {
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
        
    Or:
        POST /scrape/youtube
        {
            "video_url": "https://youtu.be/dQw4w9WgXcQ"
        }
    """
    if not request.video_url:
        raise HTTPException(status_code=400, detail="video_url is required")
    
    logger.info("Scraping YouTube transcript via API: %s", request.video_url)
    
    try:
        result = await scrape_youtube_transcript(request.video_url)
        
        if not result:
            return {
                "ok": False,
                "error": "Failed to scrape YouTube transcript",
                "video_url": request.video_url,
            }
        
        # If transcript was successfully extracted, analyze it with Gemini
        if result.get("ok") and result.get("transcript"):
            try:
                logger.info("Analyzing transcript with Gemini Flash 2.5...")
                summary = analyze_youtube_transcript(
                    video_title=result.get("video_title", ""),
                    transcript=result.get("transcript", "")
                )
                
                # Add summary to result
                result["summary"] = summary.model_dump()
                logger.info("✅ Transcript analysis completed")
            except Exception as analysis_error:  # noqa: BLE001
                # Don't fail the whole request if analysis fails
                logger.warning("Transcript analysis failed (continuing without summary): %s", analysis_error)
                result["summary"] = None
                result["analysis_error"] = str(analysis_error)
        
        return result
        
    except Exception as e:  # noqa: BLE001
        logger.error("YouTube transcript scraping failed for %s: %s", request.video_url, e)
        raise HTTPException(status_code=500, detail=f"YouTube scraping failed: {str(e)}") from e


@router.post("/yt")
async def scrape_youtube_short_endpoint(
    request: ScrapeYouTubeRequest,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """
    Short alias for /scrape/youtube endpoint.
    
    Same functionality as /scrape/youtube, just a shorter URL.
    
    Example:
        POST /yt
        {
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        }
    """
    return await scrape_youtube_endpoint(request, settings)
