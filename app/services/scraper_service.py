from __future__ import annotations

import asyncio
import logging
from typing import Optional
from urllib.parse import urljoin

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
    """Build ScraperAPI proxy URL (fallback method)"""
    settings = get_settings()
    return f"https://api.scraperapi.com?api_key={settings.SCRAPER_API_KEY}&url={target_url}"


def _extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML using BeautifulSoup (fallback method)"""
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


async def _scrape_with_crawl4ai(url: str) -> Optional[str]:
    """
    Scrape URL using Crawl4AI (free, LLM-friendly).
    Returns markdown content, or None if failed.
    """
    try:
        from crawl4ai import AsyncWebCrawler

        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(
                url=url,
                bypass_cache=True,
                word_count_threshold=10,  # Filter out short/noisy content
            )

            if result.success and result.markdown:
                logger.info("Crawl4AI scraped %s successfully (%d chars markdown)", url, len(result.markdown))
                return result.markdown
            else:
                logger.warning("Crawl4AI failed to scrape %s: %s", url, result.error_message if hasattr(result, 'error_message') else 'unknown error')
                return None

    except Exception as e:  # noqa: BLE001
        logger.warning("Crawl4AI error for %s: %s", url, e)
        return None


async def _scrape_multi_page_crawl4ai(domain: str, max_pages: int = 5) -> dict[str, str]:
    """
    Scrape multiple pages from a domain using Crawl4AI.
    Returns dict of {page_type: markdown_content}
    """
    from crawl4ai import AsyncWebCrawler
    from bs4 import BeautifulSoup

    results = {}
    homepage_url = f"https://{domain}"

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            # 1. Scrape homepage
            home_result = await crawler.arun(
                url=homepage_url,
                bypass_cache=True,
                word_count_threshold=10,
            )

            if home_result.success and home_result.markdown:
                results["homepage"] = home_result.markdown
                logger.info("✓ Homepage scraped: %d chars", len(home_result.markdown))

                # 2. Discover key pages from homepage HTML
                key_pages = _discover_key_pages(domain, home_result.html or "")

                # 3. Scrape discovered pages (limit to max_pages - 1 for homepage)
                pages_to_scrape = list(key_pages.items())[:max_pages - 1]

                for page_type, page_url in pages_to_scrape:
                    try:
                        page_result = await crawler.arun(
                            url=page_url,
                            bypass_cache=True,
                            word_count_threshold=10,
                        )

                        if page_result.success and page_result.markdown:
                            results[page_type] = page_result.markdown
                            logger.info("✓ %s page scraped: %d chars", page_type.capitalize(), len(page_result.markdown))
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Failed to scrape %s page: %s", page_type, e)

        logger.info("Multi-page scrape complete for %s: %d pages scraped", domain, len(results))
        return results

    except Exception as e:  # noqa: BLE001
        logger.warning("Multi-page Crawl4AI failed for %s: %s", domain, e)
        return {}


def _scrape_with_scraperapi(url: str) -> Optional[str]:
    """
    Fallback: Scrape URL using ScraperAPI (paid, but handles bot detection).
    Returns text content, or None if failed.
    """
    settings = get_settings()

    if not settings.SCRAPER_API_KEY:
        logger.debug("SCRAPER_API_KEY not set, cannot use fallback scraper")
        return None

    try:
        scraper_url = _scraper_api_url(url)
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(scraper_url)
            resp.raise_for_status()
            html = resp.text

        text = _extract_text_from_html(html)
        logger.info("ScraperAPI (fallback) scraped %s successfully (%d chars)", url, len(text))
        return text

    except (httpx.TimeoutException, httpx.NetworkError) as e:
        raise ScraperTransientError(f"Timeout scraping {url}: {e}") from e
    except httpx.HTTPStatusError as e:
        code = e.response.status_code
        if code == 429 or 500 <= code <= 599:
            raise ScraperTransientError(f"ScraperAPI HTTP {code}") from e
        logger.warning("ScraperAPI failed to scrape %s: HTTP %d", url, code)
        return None


def _scrape_url(url: str) -> Optional[str]:
    """
    Scrape URL with Crawl4AI (free), fallback to ScraperAPI if needed.
    Returns markdown/text content.
    """
    # Try Crawl4AI first (free, better for LLMs)
    try:
        content = asyncio.run(_scrape_with_crawl4ai(url))
        if content:
            return content
    except Exception as e:  # noqa: BLE001
        logger.warning("Crawl4AI failed for %s, trying ScraperAPI fallback: %s", url, e)

    # Fallback to ScraperAPI (paid, but handles tough sites)
    return _scrape_with_scraperapi(url)


def scrape_website(domain: str) -> Optional[WebsiteIntelligence]:
    """
    Scrape company website and use LLM to extract sales intelligence.

    **Multi-page deep scraping:**
    - Scrapes homepage + key pages (about, products, pricing, careers, blog)
    - Extracts product catalogs, certifications, regulations
    - Industry-specific intelligence (CPG regulations, SaaS compliance, etc.)
    - Uses Crawl4AI (free) with ScraperAPI fallback
    """
    settings = get_settings()

    if not settings.ENABLE_WEBSITE_SCRAPING:
        logger.info("Website scraping disabled (ENABLE_WEBSITE_SCRAPING=false)")
        return None

    logger.info("🔍 Deep scraping website: %s (multi-page with Crawl4AI)", domain)

    # Multi-page scraping with Crawl4AI
    try:
        page_contents = asyncio.run(_scrape_multi_page_crawl4ai(domain, max_pages=5))

        if not page_contents:
            logger.warning("Multi-page scraping failed, trying single page fallback")
            # Fallback to single page
            homepage_url = f"https://{domain}"
            homepage_content = _scrape_url(homepage_url)
            if not homepage_content:
                logger.warning("Failed to scrape %s", domain)
                return None
            page_contents = {"homepage": homepage_content}

    except Exception as e:  # noqa: BLE001
        logger.warning("Multi-page scraping error: %s, trying single page fallback", e)
        homepage_url = f"https://{domain}"
        homepage_content = _scrape_url(homepage_url)
        if not homepage_content:
            logger.warning("Failed to scrape %s", domain)
            return None
        page_contents = {"homepage": homepage_content}

    logger.info("📄 Scraped %d pages for %s", len(page_contents), domain)

    # Fetch recent news using grounded search (Gemini 2.5 Flash with Google Search)
    from app.services.llm_service import fetch_grounded_company_news

    # Try to extract company name from domain (best effort)
    company_name = domain.split(".")[0].replace("-", " ").title()

    logger.info("📰 Fetching recent news with grounded search for %s", company_name)
    grounded_news = fetch_grounded_company_news(company_name, domain)
    news_summary = grounded_news.get("news_summary", "")
    news_sources = grounded_news.get("sources", [])

    logger.info("Grounded news: %s (sources: %d)", "found" if news_summary else "none", len(news_sources))

    # Combine all page content for LLM analysis
    combined_text = ""
    for page_type, text in page_contents.items():
        # Truncate each page to avoid token limits
        truncated = text[:5000] if len(text) > 5000 else text
        combined_text += f"\n\n=== {page_type.upper()} PAGE ===\n{truncated}\n"

    # Add grounded news to LLM prompt if found
    if news_summary:
        combined_text += f"\n\n=== RECENT NEWS (from Google Search) ===\n{news_summary}\n"

    # Analyze with LLM
    logger.info("Analyzing website content with LLM (%d chars)", len(combined_text))

    system_prompt = (
        "You are a friendly, sharp B2B sales rep at GoVisually who just spent 10 minutes researching this company's website. "
        "You're sharing your findings with your teammate who's about to hop on a demo call with them. "
        "Write like you're talking to a colleague - casual, conversational, actionable. "
        "Focus on what matters for the demo: their business, their likely pain points, and how GoVisually can help."
    )

    user_prompt = f"""I just deep-dived this company's website across multiple pages. Here's what I found:

{combined_text}

Write me comprehensive intel notes in JSON format. Keep it real and conversational - like you're briefing a teammate before they hop on a call.

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
  "sales_insights": "3-4 bullet points on how to approach this demo. What should we focus on? What will resonate? Return as a SINGLE STRING with newlines between bullets, NOT an array. (Examples: '• They're in packaging/CPG - lead with our proofing workflow\\n• Remote team across 3 offices - emphasize async collaboration\\n• Using Adobe/Figma - show our integrations')",

  "product_catalog": "List their specific products/services if found on product pages (e.g., 'Product A: Does X, Product B: Does Y'). If they're CPG, list actual products. If SaaS, list features/tiers. (if found)",
  "certifications": "Any certifications, compliance standards, credentials mentioned? (ISO 27001, SOC2, HIPAA, FDA approval, USDA Organic, Fair Trade, B-Corp, etc.) (if found)",
  "regulations": "What regulatory environment do they operate in? Any compliance mentions? (Prop 65, GDPR, EPA standards, food safety, FDA regulations, OSHA, industry-specific rules) (if found)",
  "team_size_signals": "Office locations, team size mentions, hiring activity from careers/about pages (e.g., '3 offices - NYC, London, SF. Hiring 10+ roles in engineering')",
  "tech_stack_signals": "Technologies, platforms, integrations they mention using or offer (Salesforce, AWS, Stripe, Shopify, Adobe, etc.) (if found)",
  "customer_segments": "Different customer types or industries they serve (e.g., 'Serve both B2B and B2C. Industries: Healthcare, Finance, Retail')",
  "use_cases": "Specific use cases or problem scenarios they solve (e.g., 'Remote team collaboration, Product launches, Marketing campaigns')",
  "content_depth": "How content-rich is the site? Active blog? Resources? Thought leadership? Or just basic marketing pages? (e.g., 'Super content-rich - 100+ blog posts, case studies, whitepapers' or 'Pretty basic marketing site, not much depth')"
}}

Keep it short, punchy, and useful. If you don't find something, just use empty string "".

Output JSON only, no markdown or explanation."""

    try:
        intelligence = generate_strict_json(
            model=WebsiteIntelligence,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Override recent_news with grounded search result if found
        if news_summary:
            intelligence.recent_news = news_summary

        # Add news sources from grounded search
        intelligence.news_sources = news_sources

        logger.info("Website intelligence extracted for %s (news sources: %d)", domain, len(news_sources))
        logger.debug("Intelligence fields populated: %s", {k: bool(v) for k, v in intelligence.model_dump().items()})
        return intelligence
    except Exception as e:
        logger.error("Failed to analyze website content with LLM: %s", e)
        return None
