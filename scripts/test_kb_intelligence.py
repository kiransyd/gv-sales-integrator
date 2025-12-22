#!/usr/bin/env python3
"""
Test script: Test the new KB intelligence extraction with LLM synthesis.
Creates a unique session to avoid duplicates.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx

# Local development configuration
BASE_URL = "http://localhost:8000"
READAI_SHARED_SECRET = ""  # Empty in local dev

# Meeting details
MEETING_TIME = datetime.now(timezone.utc) - timedelta(hours=1)
MEETING_START_TIME = MEETING_TIME.isoformat()
MEETING_END_TIME = (MEETING_TIME + timedelta(minutes=35)).isoformat()

# Unique session ID to avoid duplicates
UNIQUE_SESSION_ID = f"TEST-KB-INTEL-{uuid.uuid4().hex[:8]}"


def create_pharma_demo_payload():
    """Create realistic pharma company demo focused on FDA compliance"""
    return {
        "session_id": UNIQUE_SESSION_ID,
        "trigger": "meeting_end",
        "title": "GoVisually Demo - MedLife Pharma FDA Compliance",
        "start_time": MEETING_START_TIME,
        "end_time": MEETING_END_TIME,
        "participants": [
            {
                "name": "Sarah Martinez",
                "email": "sarah.martinez@medlifepharma.com"
            },
            {
                "name": "Dr. James Wilson",
                "email": "james.wilson@medlifepharma.com"
            },
            {
                "name": "GoVisually Sales Rep",
                "email": "demo@govisually.com"
            }
        ],
        "owner": {
            "name": "Sarah Martinez",
            "email": "sarah.martinez@medlifepharma.com"
        },
        "summary": """Sarah Martinez (Regulatory Affairs Director) from MedLife Pharma met with GoVisually to discuss their FDA label compliance challenges. Dr. James Wilson (Chief Medical Officer) also joined. They're currently using manual processes for FDA label reviews which takes 2-3 weeks per product and creates significant risk of allergen disclosure errors and 21 CFR Part 11 compliance violations. Sarah emphasized the critical need for audit trails and version control. James highlighted the time pressure to get products to market while maintaining FDA compliance. The team is very interested in a trial focused on their upcoming product launches.""",
        "action_items": [
            {
                "text": "GoVisually to send trial access for MedLife Pharma team"
            },
            {
                "text": "Sarah to schedule internal review with regulatory team"
            }
        ],
        "key_questions": [
            {
                "text": "Does GoVisually support 21 CFR Part 11 compliance requirements?"
            },
            {
                "text": "Can we get audit trails for all reviewer actions?"
            },
            {
                "text": "What's the typical time savings for FDA label reviews?"
            }
        ],
        "topics": [
            {
                "text": "FDA compliance and 21 CFR Part 11"
            },
            {
                "text": "Allergen disclosure accuracy"
            },
            {
                "text": "Version control and audit trails"
            },
            {
                "text": "Time-to-market acceleration"
            }
        ],
        "report_url": f"https://app.read.ai/analytics/meetings/{UNIQUE_SESSION_ID}",
        "transcript": {
            "speakers": [
                {"name": "Sarah Martinez"},
                {"name": "Dr. James Wilson"},
                {"name": "GoVisually Sales Rep"}
            ],
            "speaker_blocks": [
                {
                    "start_time": "1734700000000",
                    "end_time": "1734700030000",
                    "speaker": {"name": "Sarah Martinez"},
                    "words": "Thanks for taking the time today. We're a pharmaceutical company and we're really struggling with our FDA label compliance process. Right now everything is manual - emails, PDFs, redlined documents - and it's taking us 2 to 3 weeks per product label. That's just too slow and too risky."
                },
                {
                    "start_time": "1734700030000",
                    "end_time": "1734700050000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "I completely understand. FDA compliance is one of our core use cases. Let me show you how our platform can help streamline your review process while maintaining full compliance."
                },
                {
                    "start_time": "1734700050000",
                    "end_time": "1734700090000",
                    "speaker": {"name": "Dr. James Wilson"},
                    "words": "Hi, I'm James Wilson, Chief Medical Officer. My biggest concern is allergen disclosure errors. If we miss an allergen on a label, that's not just a compliance issue - it's a patient safety issue. We need bulletproof version control and we need to know exactly who reviewed what and when."
                },
                {
                    "start_time": "1734700090000",
                    "end_time": "1734700120000",
                    "speaker": {"name": "Sarah Martinez"},
                    "words": "Exactly. And we need to comply with 21 CFR Part 11. We need electronic signatures, audit trails, timestamps on every action. Our current process just doesn't cut it."
                },
                {
                    "start_time": "1734700120000",
                    "end_time": "1734700160000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Perfect - this is exactly what we built the FDA Regulatory Agent for. It's specifically trained on 21 CFR Parts 201, 211, 312, and 314. Every reviewer action is automatically logged with timestamps and user information for your audit trail."
                },
                {
                    "start_time": "1734700160000",
                    "end_time": "1734700190000",
                    "speaker": {"name": "Dr. James Wilson"},
                    "words": "That's impressive. What about the actual review time? You mentioned this can help with our 2-3 week timeline?"
                },
                {
                    "start_time": "1734700190000",
                    "end_time": "1734700230000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Yes - our pharma customers typically see 85 to 90 percent time savings on their compliance review cycles. So your 2-3 week process could become 2-3 days. The FDA Regulatory Agent can automatically flag potential compliance issues, including allergen disclosures."
                },
                {
                    "start_time": "1734700230000",
                    "end_time": "1734700260000",
                    "speaker": {"name": "Sarah Martinez"},
                    "words": "Wow, that would be transformative for us. What about version history? We need to be able to go back and see exactly what changed between version 3 and version 7 of a label."
                },
                {
                    "start_time": "1734700260000",
                    "end_time": "1734700290000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Built-in version control is core to the platform. You can compare any two versions side-by-side, and every change is tracked with who made it and when. Perfect for FDA audits."
                },
                {
                    "start_time": "1734700290000",
                    "end_time": "1734700330000",
                    "speaker": {"name": "Dr. James Wilson"},
                    "words": "This sounds like exactly what we need. Our product pipeline has 12 new launches this quarter and the regulatory bottleneck is killing our time-to-market. If we can compress those 2-3 weeks down to days, that's huge for us."
                },
                {
                    "start_time": "1734700330000",
                    "end_time": "1734700360000",
                    "speaker": {"name": "Sarah Martinez"},
                    "words": "I'm ready to move forward. Can we get a trial set up? I'd like to test it on our next product launch - the allergen disclosure requirements are particularly complex on that one."
                },
                {
                    "start_time": "1734700360000",
                    "end_time": "1734700390000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Absolutely. I'll get you trial access today. Let me also send you some case studies from other pharma companies - one saw full ROI payback in under 3 months just from the time savings alone."
                },
                {
                    "start_time": "1734700390000",
                    "end_time": "1734700420000",
                    "speaker": {"name": "Dr. James Wilson"},
                    "words": "That's a compelling business case. And frankly, the risk reduction on the compliance side is worth it on its own. One allergen disclosure error could cost us millions."
                },
                {
                    "start_time": "1734700420000",
                    "end_time": "1734700450000",
                    "speaker": {"name": "Sarah Martinez"},
                    "words": "Agreed. Let's get this trial started. Thanks for the demo - this is exactly what we've been looking for."
                }
            ]
        }
    }


def send_webhook():
    """Send webhook to production"""
    print("\n" + "="*80)
    print("Testing NEW KB Intelligence Extraction (LLM Synthesis)")
    print("="*80)

    payload = create_pharma_demo_payload()

    print(f"\nPayload preview:")
    print(f"  Session ID: {payload['session_id']}")
    print(f"  Title: {payload['title']}")
    print(f"  Meeting Owner: {payload['owner']['name']} <{payload['owner']['email']}>")
    print(f"  Attendees:")
    for p in payload['participants']:
        print(f"    - {p['name']} <{p['email']}>")
    print(f"\nKey Topics:")
    print(f"  - FDA compliance (21 CFR Part 11)")
    print(f"  - Allergen disclosure errors")
    print(f"  - 2-3 week manual process → 85-90% time savings")
    print(f"  - Audit trails and version control")

    headers = {
        "Content-Type": "application/json"
    }

    if READAI_SHARED_SECRET:
        headers["X-ReadAI-Secret"] = READAI_SHARED_SECRET

    url = f"{BASE_URL}/webhooks/readai"
    print(f"\nSending to: {url}")

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print(f"\n🎉 SUCCESS! Webhook queued for processing")
                print(f"Event ID: {data.get('event_id')}")
                return True, data.get('event_id')
            elif data.get("duplicate"):
                print(f"\n⚠️  DUPLICATE: Event already processed")
                return True, None
        else:
            print(f"\n❌ FAILED: {response.text}")
            return False, None

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False, None


def main():
    print("\n" + "🧪"*40)
    print("KB INTELLIGENCE TEST: LLM Synthesis vs Old Keyword Matching")
    print("🧪"*40)
    print("\nThis test demonstrates the NEW KB intelligence approach:")
    print("  ✅ Uses LLM to synthesize KB chunks into actionable talking points")
    print("  ✅ Connects prospect pain → GoVisually features → specific outcomes")
    print("  ✅ Conversational tone (like a helpful teammate)")
    print("  ✅ Section titled 'Key Talking Points for Follow-up'")
    print("\nOLD approach (being replaced):")
    print("  ❌ Primitive keyword matching")
    print("  ❌ Fragmented sentences")
    print("  ❌ No pain-to-feature mapping")
    print("\nTarget environment: LOCAL DEVELOPMENT")
    print(f"Base URL: {BASE_URL}")
    print("="*80)

    success, event_id = send_webhook()

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Webhook: {'✅ SUCCESS' if success else '❌ FAILED'}")

    if success and event_id:
        print(f"\n📊 Monitor worker logs for event: {event_id}")
        print("\n📝 Expected KB intelligence output should look like:")
        print("   ✅ 'Highlight the FDA Regulatory Agent trained on 21 CFR Parts 201, 211, 312, 314")
        print("      because it directly addresses their allergen disclosure compliance concerns")
        print("      - emphasize this can reduce their 2-3 week manual process to 2-3 days (85-90% time savings)'")
        print("\n   ✅ 'Lead with the automated audit trail and version control features")
        print("      because they specifically mentioned lacking proper version control")
        print("      - this solves their 21 CFR Part 11 compliance requirements'")
        print("\nInstead of the old fragmented output like:")
        print("   ❌ 'Our US FDA Regulatory Agent knows 21 CFR Parts 201, 211, 312, 314.'")
        print("   ❌ 'for all activities Export compliance reports Value: Reduces FDA...'")

        print("\n🔍 Check Zoho CRM for:")
        print(f"   Email: sarah.martinez@medlifepharma.com")
        print(f"   Look for note section: 'Key Talking Points for Follow-up'")

    print("="*80)


if __name__ == "__main__":
    main()
