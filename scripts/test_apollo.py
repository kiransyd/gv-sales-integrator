#!/usr/bin/env python3
"""Quick test of Apollo person/company enrichment"""
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.apollo_service import enrich_person, enrich_company
from app.util.text_format import extract_domain_from_email


def test_person(email: str):
    """Test Apollo person enrichment"""
    print(f"🔍 Fetching Apollo person data for: {email}\n")

    try:
        person = enrich_person(email, use_cache=False)  # Skip cache for testing

        if not person:
            print(f"❌ No person data found for: {email}")
            return 1

        print(f"✅ Person Data Found:\n")
        print(f"   Name: {person.first_name} {person.last_name}")
        print(f"   Email: {person.email}")
        print(f"   Title: {person.title or 'N/A'}")
        print(f"   Seniority: {person.seniority or 'N/A'}")
        print(f"   Department: {person.department or 'N/A'}")
        print(f"   LinkedIn: {person.linkedin_url or 'N/A'}")

        if person.phone_numbers:
            print(f"   Phone: {', '.join(person.phone_numbers)}")
        else:
            print(f"   Phone: N/A")

        if person.employment_history:
            print(f"\n   Employment History:")
            for i, job in enumerate(person.employment_history[:3], 1):
                company = job.get('organization_name', 'N/A')
                title = job.get('title', 'N/A')
                print(f"     {i}. {title} at {company}")

        print(f"\n📄 Full JSON:")
        print(json.dumps(person.model_dump(), indent=2))

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def test_company(domain: str):
    """Test Apollo company enrichment"""
    print(f"🔍 Fetching Apollo company data for: {domain}\n")

    try:
        company = enrich_company(domain, use_cache=False)  # Skip cache for testing

        if not company:
            print(f"⚠️  No company data found for: {domain}")
            print(f"    This may be because:")
            print(f"    - Apollo API tier doesn't include company enrichment (403 error)")
            print(f"    - Domain not found in Apollo database")
            print(f"\n💡 Enrichment will still work with person data + website scraping")
            return 0  # Not an error, just not available

        print(f"✅ Company Data Found:\n")
        print(f"   Name: {company.name}")
        print(f"   Domain: {company.domain}")
        print(f"   Industry: {company.industry or 'N/A'}")
        print(f"   Employees: {company.employee_count or 'N/A'}")
        print(f"   Revenue: {company.revenue or 'N/A'}")
        print(f"   Founded: {company.founded_year or 'N/A'}")
        print(f"   Funding Stage: {company.funding_stage or 'N/A'}")
        print(f"   Total Funding: {company.funding_total or 'N/A'}")
        print(f"   Location: {company.city or 'N/A'}, {company.state or 'N/A'}, {company.country or 'N/A'}")

        if company.technologies:
            print(f"\n   Tech Stack ({len(company.technologies)}):")
            for tech in company.technologies[:10]:
                print(f"     • {tech}")
            if len(company.technologies) > 10:
                print(f"     ... and {len(company.technologies) - 10} more")

        print(f"\n📄 Full JSON:")
        print(json.dumps(company.model_dump(), indent=2))

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/test_apollo.py <email>           # Test person enrichment")
        print("  python scripts/test_apollo.py --company <domain>  # Test company enrichment")
        print("\nExamples:")
        print("  python scripts/test_apollo.py kiran@govisually.com")
        print("  python scripts/test_apollo.py --company govisually.com")
        return 1

    if sys.argv[1] == "--company":
        if len(sys.argv) < 3:
            print("❌ Domain required after --company flag")
            return 1
        domain = sys.argv[2]
        return test_company(domain)

    email = sys.argv[1]

    # Test person enrichment
    result = test_person(email)

    # Also test company enrichment for the domain
    domain = extract_domain_from_email(email)
    if domain and result == 0:
        print("\n" + "="*70 + "\n")
        result = test_company(domain)

    return result


if __name__ == "__main__":
    sys.exit(main())
