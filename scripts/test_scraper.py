#!/usr/bin/env python3
"""Test website scraping + LLM analysis"""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.scraper_service import scrape_website


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/test_scraper.py <domain>")
        print("\nExamples:")
        print("  python scripts/test_scraper.py govisually.com")
        print("  python scripts/test_scraper.py deputy.com")
        return 1

    domain = sys.argv[1]

    print(f"🌐 Scraping and analyzing website: {domain}")
    print(f"   This may take 30-60 seconds...\n")

    try:
        intelligence = scrape_website(domain)

        if not intelligence:
            print(f"❌ No website intelligence found for: {domain}")
            print(f"    This could be because:")
            print(f"    - Website couldn't be accessed")
            print(f"    - ScraperAPI key invalid")
            print(f"    - LLM analysis failed")
            return 1

        print(f"✅ Website Intelligence Found:\n")
        print(f"📊 Value Proposition:")
        print(f"   {intelligence.value_proposition or 'N/A'}\n")

        print(f"🎯 Target Market:")
        print(f"   {intelligence.target_market or 'N/A'}\n")

        print(f"📦 Products/Services:")
        print(f"   {intelligence.products_services or 'N/A'}\n")

        print(f"💰 Pricing Model:")
        print(f"   {intelligence.pricing_model or 'N/A'}\n")

        if intelligence.recent_news:
            print(f"📰 Recent News:")
            print(f"   {intelligence.recent_news}\n")

        if intelligence.growth_signals:
            print(f"📈 Growth Signals:")
            print(f"   {intelligence.growth_signals}\n")

        if intelligence.key_pain_points:
            print(f"🎯 Key Pain Points:")
            print(f"   {intelligence.key_pain_points}\n")

        if intelligence.competitors_mentioned:
            print(f"🏆 Competitors Mentioned:")
            print(f"   {intelligence.competitors_mentioned}\n")

        if intelligence.sales_insights:
            print(f"💡 Sales Insights:")
            print(f"   {intelligence.sales_insights}\n")

        print(f"\n📄 Full JSON:")
        print(json.dumps(intelligence.model_dump(), indent=2))

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
