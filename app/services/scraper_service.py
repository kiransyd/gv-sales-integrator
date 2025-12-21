from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse, parse_qs

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
    from app.services.llm_service import fetch_grounded_company_news, fetch_grounded_competitors

    # Try to extract company name from domain (best effort)
    company_name = domain.split(".")[0].replace("-", " ").title()

    logger.info("📰 Fetching recent news with grounded search for %s", company_name)
    grounded_news = fetch_grounded_company_news(company_name, domain)
    news_summary = grounded_news.get("news_summary", "")
    news_sources = grounded_news.get("sources", [])

    logger.info("Grounded news: %s (sources: %d)", "found" if news_summary else "none", len(news_sources))

    # Fetch competitors using grounded search (Gemini 2.5 Flash with Google Search)
    logger.info("🔍 Fetching competitors with grounded search for %s", company_name)
    grounded_competitors = fetch_grounded_competitors(company_name, domain)
    competitors_summary = grounded_competitors.get("competitors_summary", "")
    competitors_sources = grounded_competitors.get("sources", [])

    logger.info("Grounded competitors: %s (sources: %d)", "found" if competitors_summary else "none", len(competitors_sources))

    # Combine all page content for LLM analysis
    combined_text = ""
    for page_type, text in page_contents.items():
        # Truncate each page to avoid token limits
        truncated = text[:5000] if len(text) > 5000 else text
        combined_text += f"\n\n=== {page_type.upper()} PAGE ===\n{truncated}\n"

    # Add grounded news to LLM prompt if found
    if news_summary:
        combined_text += f"\n\n=== RECENT NEWS (from Google Search) ===\n{news_summary}\n"

    # Add grounded competitors to LLM prompt if found
    if competitors_summary:
        combined_text += f"\n\n=== COMPETITORS (from Google Search) ===\n{competitors_summary}\n"

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

        # Override competitors_mentioned with grounded search result if found
        if competitors_summary:
            intelligence.competitors_mentioned = competitors_summary

        logger.info("Website intelligence extracted for %s (news sources: %d, competitors: %s)", 
                   domain, len(news_sources), "found" if competitors_summary else "none")
        logger.debug("Intelligence fields populated: %s", {k: bool(v) for k, v in intelligence.model_dump().items()})
        return intelligence
    except Exception as e:
        logger.error("Failed to analyze website content with LLM: %s", e)
        return None


def _parse_subtitle_content(subtitle_content: str) -> list[str]:
    """
    Parse WebVTT, SRT, or YouTube JSON subtitle content and extract text lines.
    
    Args:
        subtitle_content: Raw subtitle content (WebVTT, SRT, or YouTube JSON format)
        
    Returns:
        List of transcript text lines
    """
    lines = []
    
    # Try parsing as JSON first (YouTube's internal format)
    try:
        import json
        data = json.loads(subtitle_content)
        
        # YouTube JSON format has "events" array with "segs" containing text
        if isinstance(data, dict) and 'events' in data:
            for event in data.get('events', []):
                if 'segs' in event:
                    text_parts = []
                    for seg in event.get('segs', []):
                        if 'utf8' in seg:
                            text_parts.append(seg['utf8'])
                    if text_parts:
                        combined_text = ''.join(text_parts).strip()
                        if combined_text:
                            lines.append(combined_text)
            
            if lines:
                logger.debug("Parsed YouTube JSON subtitle format (%d segments)", len(lines))
                return lines
    except (json.JSONDecodeError, KeyError, TypeError):
        # Not JSON format, continue with text parsing
        pass
    
    # Parse as WebVTT or SRT format
    subtitle_lines = subtitle_content.split('\n')
    
    for line in subtitle_lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip WebVTT header
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        
        # Skip SRT sequence numbers
        if line.isdigit():
            continue
        
        # Skip timestamp lines (WebVTT: 00:00:00.000 --> 00:00:05.000, SRT: same format)
        if re.match(r'^\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}', line):
            continue
        
        # Skip WebVTT cue settings (align, position, etc.)
        if line.startswith('align:') or line.startswith('position:') or line.startswith('line:'):
            continue
        
        # Skip HTML tags in subtitles
        line = re.sub(r'<[^>]+>', '', line)
        
        # Skip cue identifiers (WebVTT)
        if re.match(r'^[A-Za-z0-9_-]+$', line) and len(line) < 50:
            # Might be a cue identifier, but could also be actual text
            # Only skip if it looks like an identifier (short, alphanumeric)
            if len(line) < 20:
                continue
        
        # Add the text line
        if line and len(line) > 2:
            lines.append(line)
    
    return lines


def extract_youtube_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/watch?v=VIDEO_ID&t=123s
    
    Returns:
        Video ID if found, None otherwise
    """
    # Remove whitespace
    url = url.strip()
    
    # Pattern for standard YouTube URLs: youtube.com/watch?v=VIDEO_ID
    match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Try parsing as URL
    try:
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            # Check query params
            if parsed.query:
                params = parse_qs(parsed.query)
                if 'v' in params:
                    return params['v'][0]
            # Check path for youtu.be format
            if 'youtu.be' in parsed.netloc:
                video_id = parsed.path.lstrip('/')
                if len(video_id) == 11:
                    return video_id
    except Exception:
        pass
    
    return None


async def scrape_youtube_transcript(video_url: str) -> Optional[dict[str, Any]]:
    """
    Scrape YouTube video transcript using yt-dlp as primary extractor.
    
    Args:
        video_url: YouTube video URL (any format)
        
    Returns:
        Dict with transcript data, or None if failed
    """
    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        logger.error("Invalid YouTube URL: %s", video_url)
        return None
    
    logger.info("📹 Scraping YouTube transcript for video ID: %s", video_id)
    
    transcript_url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Primary method: Use yt-dlp (most reliable for YouTube transcripts)
    try:
        import yt_dlp
        
        logger.info("Using yt-dlp for transcript extraction")
        
        # Configure yt-dlp to get video info with subtitle URLs
        ydl_opts = {
            'skip_download': True,  # We only want the transcript, not the video
            'quiet': True,  # Suppress output
            'no_warnings': True,
            'listsubtitles': True,  # List available subtitles
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract video info (this will include subtitle information)
            info = ydl.extract_info(video_url, download=False)
            
            video_title = info.get('title', '')
            video_id_from_info = info.get('id', video_id)
            
            # Get available subtitles and automatic captions
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            transcript_text = None
            transcript_lines = []
            
            # Try manual subtitles first (higher quality)
            for lang_code in ['en', 'en-US', 'en-GB']:
                if lang_code in subtitles:
                    subtitle_list = subtitles[lang_code]
                    if subtitle_list:
                        # Get the first available subtitle format (usually vtt or srt)
                        subtitle_info = subtitle_list[0]
                        subtitle_url = subtitle_info.get('url')
                        if subtitle_url:
                            logger.info("Found manual subtitles in %s, fetching...", lang_code)
                            try:
                                async with httpx.AsyncClient(timeout=15.0) as client:
                                    resp = await client.get(subtitle_url)
                                    if resp.status_code == 200:
                                        subtitle_content = resp.text
                                        logger.debug("Fetched subtitle content (%d chars), parsing...", len(subtitle_content))
                                        transcript_lines = _parse_subtitle_content(subtitle_content)
                                        if transcript_lines:
                                            transcript_text = ' '.join(transcript_lines)
                                            logger.info("Parsed %d transcript lines from manual subtitles", len(transcript_lines))
                                            break
                                        else:
                                            logger.warning("Failed to parse subtitle content (first 200 chars: %s)", subtitle_content[:200])
                            except Exception as e:
                                logger.debug("Failed to fetch manual subtitles: %s", e)
                                continue
            
            # If no manual subtitles, try automatic captions
            if not transcript_text:
                for lang_code in ['en', 'en-US', 'en-GB']:
                    if lang_code in automatic_captions:
                        caption_list = automatic_captions[lang_code]
                        if caption_list:
                            caption_info = caption_list[0]
                            caption_url = caption_info.get('url')
                            if caption_url:
                                logger.info("Found automatic captions in %s, fetching...", lang_code)
                                try:
                                    async with httpx.AsyncClient(timeout=15.0) as client:
                                        resp = await client.get(caption_url)
                                        if resp.status_code == 200:
                                            subtitle_content = resp.text
                                            logger.debug("Fetched caption content (%d chars), parsing...", len(subtitle_content))
                                            transcript_lines = _parse_subtitle_content(subtitle_content)
                                            if transcript_lines:
                                                transcript_text = ' '.join(transcript_lines)
                                                logger.info("Parsed %d transcript lines from automatic captions", len(transcript_lines))
                                                break
                                            else:
                                                logger.warning("Failed to parse caption content (first 200 chars: %s)", subtitle_content[:200])
                                except Exception as e:
                                    logger.debug("Failed to fetch automatic captions: %s", e)
                                    continue
            
            if transcript_text:
                logger.info("✅ Extracted transcript via yt-dlp (%d segments, %d chars)", 
                           len(transcript_lines), len(transcript_text))
                
                return {
                    "ok": True,
                    "video_id": video_id_from_info,
                    "video_url": transcript_url,
                    "video_title": video_title,
                    "transcript": transcript_text,
                    "transcript_length": len(transcript_text),
                    "transcript_lines": len(transcript_lines),
                }
            else:
                logger.warning("yt-dlp found video but no transcript available")
                
    except ImportError:
        logger.debug("yt-dlp not installed, trying fallback methods")
    except Exception as ytdlp_error:
        logger.warning("yt-dlp failed: %s, trying fallback methods", ytdlp_error)
    
    # Fallback 1: Try youtube-transcript-api library
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript
        
        logger.info("Trying youtube-transcript-api library for transcript extraction")
        
        try:
            transcript_data = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB'],
            )
            
            transcript_lines = [item['text'] for item in transcript_data]
            transcript_text = ' '.join(transcript_lines)
            
            logger.info("✅ Extracted transcript via youtube-transcript-api (%d segments, %d chars)", 
                       len(transcript_lines), len(transcript_text))
            
            # Get video title
            from crawl4ai import AsyncWebCrawler
            async with AsyncWebCrawler(verbose=False) as crawler:
                page_result = await crawler.arun(
                    url=transcript_url,
                    bypass_cache=True,
                    wait_for_timeout=5000,
                )
                
                video_title = None
                if page_result.success and page_result.html:
                    soup = BeautifulSoup(page_result.html, 'html.parser')
                    title_tag = soup.find('title')
                    if title_tag:
                        video_title = title_tag.get_text(strip=True).replace(' - YouTube', '')
            
            return {
                "ok": True,
                "video_id": video_id,
                "video_url": transcript_url,
                "video_title": video_title,
                "transcript": transcript_text,
                "transcript_length": len(transcript_text),
                "transcript_lines": len(transcript_lines),
            }
        except (TranscriptsDisabled, NoTranscriptFound, CouldNotRetrieveTranscript) as e:
            logger.warning("YouTube transcript not available via API: %s", e)
    except ImportError:
        logger.debug("youtube-transcript-api not installed")
    except Exception as api_error:
        logger.warning("youtube-transcript-api failed: %s", api_error)
        
    # Fallback 2: Use Crawl4AI with generate_markdown=True
    try:
        from crawl4ai import AsyncWebCrawler
        
        async with AsyncWebCrawler(verbose=False) as crawler:
            logger.info("Using Crawl4AI with generate_markdown=True for YouTube transcript extraction")
            
            result = await crawler.arun(
                url=transcript_url,
                bypass_cache=True,
                # Enable markdown generation - Crawl4AI may auto-detect YouTube and extract transcript
                generate_markdown=True,
                # Wait longer for YouTube page and transcript to load
                wait_for_timeout=20000,  # 20 seconds max wait (transcripts need time to load)
                page_timeout=60000,  # 60 seconds total page load timeout
            )
            
            if not result.success:
                logger.warning("Crawl4AI failed to load YouTube page: %s", result.error_message if hasattr(result, 'error_message') else 'unknown error')
                return None
            
            # Extract transcript from Crawl4AI's markdown output
            # Crawl4AI automatically extracts YouTube transcripts when generate_markdown=True
            transcript_text = None
            
            if result.markdown:
                # Crawl4AI should have extracted the transcript into markdown
                # Look for transcript sections in the markdown
                lines = result.markdown.split('\n')
                transcript_lines = []
                in_transcript_section = False
                
                for line in lines:
                    # Look for transcript indicators
                    line_lower = line.lower()
                    if 'transcript' in line_lower or 'captions' in line_lower:
                        in_transcript_section = True
                        continue
                    
                    # Skip common YouTube page elements
                    if any(skip in line_lower for skip in [
                        'youtube home', 'about', 'press', 'copyright', 'contact us',
                        'creators', 'advertise', 'developers', 'terms', 'privacy',
                        'policy & safety', 'how youtube works', 'test new features',
                        'if playback doesn\'t begin', 'videos you watch may be added',
                        'an error occurred', 'sign in to youtube'
                    ]):
                        continue
                    
                    # Look for timestamp patterns: [00:00] or 0:00 or similar
                    if re.search(r'\[\d+:\d+[:\d+]*\]|^\d+:\d+[:\d+]*', line):
                        # Remove timestamp, keep text
                        text = re.sub(r'\[\d+:\d+[:\d+]*\]|^\d+:\d+[:\d+]*\s*', '', line).strip()
                        if text and len(text) > 5:
                            transcript_lines.append(text)
                            in_transcript_section = True
                    # Look for lines that seem like transcript content (longer lines, not headers)
                    elif in_transcript_section or (len(line.strip()) > 30 and not line.startswith('#') and not line.startswith('[')):
                        # Filter out obvious page metadata
                        if not any(meta in line_lower for meta in ['youtube.com', 'http', 'www.', 'click', 'button']):
                            transcript_lines.append(line.strip())
                
                if transcript_lines:
                    # Clean up: remove duplicates and empty lines
                    cleaned_lines = []
                    prev_line = ""
                    for line in transcript_lines:
                        line = line.strip()
                        if line and line != prev_line and len(line) > 3:
                            cleaned_lines.append(line)
                            prev_line = line
                    
                    if cleaned_lines:
                        transcript_text = '\n'.join(cleaned_lines)
                        logger.info("Extracted transcript from Crawl4AI markdown (%d lines)", len(cleaned_lines))
            
            # Fallback: Try to extract from HTML if markdown didn't work
            if not transcript_text and result.html:
                soup = BeautifulSoup(result.html, 'html.parser')
                
                # Look for transcript container
                transcript_container = soup.find('ytd-transcript-renderer') or soup.find(class_=re.compile('transcript', re.I))
                
                if transcript_container:
                    # Extract text from transcript segments
                    segments = transcript_container.find_all(['span', 'div'], class_=re.compile('segment|cue', re.I))
                    if segments:
                        transcript_lines = []
                        for segment in segments:
                            text = segment.get_text(strip=True)
                            if text and len(text) > 5:  # Filter out very short segments
                                transcript_lines.append(text)
                        if transcript_lines:
                            transcript_text = '\n'.join(transcript_lines)
                            logger.info("Extracted transcript from HTML (%d segments)", len(transcript_lines))
            
            if not transcript_text:
                logger.warning("Could not extract transcript from YouTube video %s", video_id)
                return {
                    "ok": False,
                    "error": "Transcript not found or not available for this video",
                    "video_id": video_id,
                    "video_url": transcript_url,
                }
            
            # Extract video metadata if available
            video_title = None
            if result.html:
                soup = BeautifulSoup(result.html, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    video_title = title_tag.get_text(strip=True).replace(' - YouTube', '')
            
            logger.info("✅ Successfully extracted YouTube transcript (%d chars)", len(transcript_text))
            
            return {
                "ok": True,
                "video_id": video_id,
                "video_url": transcript_url,
                "video_title": video_title,
                "transcript": transcript_text,
                "transcript_length": len(transcript_text),
                "transcript_lines": transcript_text.count('\n') + 1,
            }
            
    except Exception as e:  # noqa: BLE001
        logger.error("Error scraping YouTube transcript: %s", e)
        return {
            "ok": False,
            "error": str(e),
            "video_id": video_id,
        }
