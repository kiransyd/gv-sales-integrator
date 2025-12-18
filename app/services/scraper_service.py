from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.schemas.apollo import WebsiteIntelligence
from app.services.llm_service import generate_strict_json
from app.settings import get_settings

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


class ScraperTransientError(ScraperError):
    """Transient scraper errors (rate limits, timeouts) that should be retried."""


def _scraper_api_url(target_url: str) -> str:
    """Build ScraperAPI proxy URL"""
    settings = get_settings()
    return f"https://api.scraperapi.com?api_key={settings.SCRAPER_API_KEY}&url={target_url}"


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup"""
    soup = BeautifulSoup(html, "html.parser")

    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()

    # Get text
    text = soup.get_text()

    # Break into lines and remove leading/trailing space
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = "\n".join(chunk for chunk in chunks if chunk)

    return text


def _discover_key_pages(domain: str, homepage_html: str) -> dict[str, str]:
    """
    Discover key pages (about, pricing, careers, etc.) from homepage.
    Returns dict of page_type -> URL
    """
    soup = BeautifulSoup(homepage_html, "html.parser")
    discovered = {}

    # Common URL patterns to look for
    patterns = {
        "about": ["about", "about-us", "company", "who-we-are"],
        "products": ["products", "services", "solutions", "features"],
        "pricing": ["pricing", "plans", "cost"],
        "careers": ["careers", "jobs", "join-us", "hiring", "work-with-us"],
        "blog": ["blog", "news", "insights", "resources"],
    }

    # Find all links
    for link in soup.find_all("a", href=True):
        href = link["href"].lower()
        full_url = urljoin(f"https://{domain}", href)

        # Check if link matches any pattern
        for page_type, keywords in patterns.items():
            if page_type not in discovered:
                for keyword in keywords:
                    if keyword in href:
                        discovered[page_type] = full_url
                        break

    logger.info("Discovered %d key pages for %s: %s", len(discovered), domain, list(discovered.keys()))
    return discovered


def scrape_website(domain: str) -> Optional[WebsiteIntelligence]:
    """
    Scrape company website and use LLM to extract sales intelligence.

    Scrapes homepage + key pages (about, pricing, careers, etc.)
    and analyzes content with Gemini LLM.
    """
    settings = get_settings()

    if not settings.SCRAPER_API_KEY:
        logger.warning("SCRAPER_API_KEY not set, skipping website scraping")
        return None

    if not settings.ENABLE_WEBSITE_SCRAPING:
        logger.info("Website scraping disabled (ENABLE_WEBSITE_SCRAPING=false)")
        return None

    homepage_url = f"https://{domain}"
    logger.info("Scraping website: %s", homepage_url)

    # Scrape homepage
    try:
        scraper_url = _scraper_api_url(homepage_url)
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(scraper_url)
            resp.raise_for_status()
            homepage_html = resp.text
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        raise ScraperTransientError(f"Timeout scraping {homepage_url}: {e}") from e
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429 or 500 <= code <= 599:
            raise ScraperTransientError(f"ScraperAPI HTTP {code}") from e
        logger.warning("Failed to scrape %s: HTTP %d", homepage_url, code)
        return None

    homepage_text = _extract_text_from_html(homepage_html)
    logger.info("Scraped homepage: %s (%d chars)", homepage_url, len(homepage_text))

    # Discover and scrape key pages
    key_pages = _discover_key_pages(domain, homepage_html)
    page_contents = {"homepage": homepage_text}

    # Limit number of pages to scrape
    max_pages = min(settings.SCRAPER_MAX_PAGES - 1, len(key_pages))  # -1 for homepage
    scraped_count = 0

    for page_type, page_url in list(key_pages.items())[:max_pages]:
        try:
            scraper_url = _scraper_api_url(page_url)
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(scraper_url)
                resp.raise_for_status()
                page_html = resp.text
            page_text = _extract_text_from_html(page_html)
            page_contents[page_type] = page_text
            scraped_count += 1
            logger.info("Scraped %s page: %s (%d chars)", page_type, page_url, len(page_text))
        except Exception as e:  # noqa: BLE001
            logger.warning("Failed to scrape %s page (%s): %s", page_type, page_url, e)

    logger.info("Scraped %d total pages for %s", scraped_count + 1, domain)

    # Combine all page content for LLM analysis
    combined_text = ""
    for page_type, text in page_contents.items():
        # Truncate each page to avoid token limits
        truncated = text[:5000] if len(text) > 5000 else text
        combined_text += f"\n\n=== {page_type.upper()} PAGE ===\n{truncated}\n"

    # Analyze with LLM
    logger.info("Analyzing website content with LLM (%d chars)", len(combined_text))

    system_prompt = (
        "You are a B2B sales intelligence analyst. Your task is to analyze a company's website "
        "and extract key sales insights to help a sales rep prepare for a demo call. "
        "Be concise, factual, and focus on actionable intelligence."
    )

    user_prompt = f"""Analyze this company website content and extract sales intelligence:

{combined_text}

Extract the following information in JSON format. If information is not available, use empty string "".

Return ONLY valid JSON with these exact keys:
{{
  "value_proposition": "What is their main value proposition? (1-2 sentences)",
  "target_market": "Who are their target customers? (e.g., 'Mid-market B2B SaaS companies')",
  "products_services": "What products/services do they offer? (brief list)",
  "pricing_model": "What is their pricing model if mentioned? (e.g., 'Tiered SaaS $99-$499/mo')",
  "recent_news": "Any recent news, product launches, or announcements? (if found)",
  "growth_signals": "Any hiring, funding, or expansion signals? (e.g., 'Hiring 5 engineers')",
  "key_pain_points": "What pain points do they mention solving for their customers?",
  "competitors_mentioned": "Any competitors they mention or compare against?",
  "sales_insights": "Top 3 insights for a sales rep (e.g., 'Focus on enterprise features', 'Emphasize ROI tracking')"
}}

Output JSON only, no markdown or explanation."""

    try:
        intelligence = generate_strict_json(
            model=WebsiteIntelligence,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        logger.info("Website intelligence extracted for %s", domain)
        return intelligence
    except Exception as e:
        logger.error("Failed to analyze website content with LLM: %s", e)
        return None
