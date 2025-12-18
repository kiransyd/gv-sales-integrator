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
        "You are a friendly, sharp B2B sales rep at GoVisually who just spent 10 minutes researching this company's website. "
        "You're sharing your findings with your teammate who's about to hop on a demo call with them. "
        "Write like you're talking to a colleague - casual, conversational, actionable. "
        "Focus on what matters for the demo: their business, their likely pain points, and how GoVisually can help."
    )

    user_prompt = f"""I just researched this company's website. Here's what I found:

{combined_text}

Write me some quick intel notes in JSON format. Keep it real and conversational - like you're briefing a teammate, not writing a report.

Return ONLY valid JSON with these exact keys:
{{
  "value_proposition": "What's their main thing? What do they do? (1-2 casual sentences)",
  "target_market": "Who do they sell to? (conversational, e.g., 'Looks like they work with mid-market tech companies')",
  "products_services": "What are they selling? (brief, human-readable)",
  "pricing_model": "Any pricing info on the site? (if found, otherwise empty)",
  "recent_news": "Anything new happening? Product launches, partnerships, etc.? (if found, keep it brief)",
  "growth_signals": "Are they hiring? Expanding? Growing fast? (e.g., 'Hiring a bunch of engineers - looks like they're scaling')",
  "key_pain_points": "What problems are they solving for THEIR customers? (helps us understand their world)",
  "competitors_mentioned": "Do they call out any competitors? (if found)",
  "sales_insights": "3-4 bullet points on how to approach this demo. What should we focus on? What will resonate? (Be specific and actionable. Examples: 'They're in packaging/CPG - lead with our proofing workflow', 'Remote team across 3 offices - emphasize async collaboration', 'Using Adobe/Figma - show our integrations')"
}}

Keep it short, punchy, and useful. If you don't find something, just use empty string "".

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
