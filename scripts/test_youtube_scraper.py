#!/usr/bin/env python3
"""
Test YouTube transcript scraping endpoint.

Usage:
    python3 scripts/test_youtube_scraper.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    python3 scripts/test_youtube_scraper.py "https://youtu.be/dQw4w9WgXcQ" --env .env.production
"""

import argparse
import json
import sys
from pathlib import Path

import httpx


def load_env_file(env_path: str) -> dict[str, str]:
    """Load environment variables from .env file"""
    env_vars = {}
    env_file = Path(env_path)

    if not env_file.exists():
        print(f"❌ Environment file not found: {env_path}")
        sys.exit(1)

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            # Remove quotes if present
            value = value.strip('"').strip("'")
            env_vars[key] = value

    return env_vars


def test_youtube_scraper(video_url: str, base_url: str) -> None:
    """Test the YouTube transcript scraping endpoint"""
    url = f"{base_url}/scrape/youtube"
    
    print(f"📹 Testing YouTube transcript scraping")
    print(f"   Video URL: {video_url}")
    print(f"   Endpoint: {url}")
    print()
    
    payload = {"video_url": video_url}
    
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("ok"):
                print("✅ Successfully scraped YouTube transcript!")
                print()
                print(f"Video ID: {result.get('video_id')}")
                if result.get("video_title"):
                    print(f"Title: {result.get('video_title')}")
                print(f"Transcript Length: {result.get('transcript_length', 0)} characters")
                print(f"Lines: {result.get('transcript_lines', 0)}")
                print()
                print("=" * 60)
                print("TRANSCRIPT:")
                print("=" * 60)
                print(result.get("transcript", "")[:1000])  # First 1000 chars
                if result.get("transcript_length", 0) > 1000:
                    print(f"\n... (truncated, {result.get('transcript_length')} total characters)")
                print("=" * 60)
            else:
                print("❌ Failed to scrape transcript")
                print(f"   Error: {result.get('error', 'Unknown error')}")
                if result.get("video_id"):
                    print(f"   Video ID: {result.get('video_id')}")
                    
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error {e.response.status_code}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Test YouTube transcript scraping endpoint",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with full YouTube URL
  python3 scripts/test_youtube_scraper.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

  # Test with short URL
  python3 scripts/test_youtube_scraper.py "https://youtu.be/dQw4w9WgXcQ"

  # Test with production URL
  python3 scripts/test_youtube_scraper.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --env .env.production
        """,
    )
    parser.add_argument(
        "video_url",
        help="YouTube video URL (any format)",
    )
    parser.add_argument(
        "--env",
        default=".env",
        help="Environment file (default: .env)",
    )

    args = parser.parse_args()

    # Load environment
    env_vars = load_env_file(args.env)
    base_url = env_vars.get("BASE_URL", "http://localhost:8000")

    # Test the endpoint
    test_youtube_scraper(args.video_url, base_url)


if __name__ == "__main__":
    main()
