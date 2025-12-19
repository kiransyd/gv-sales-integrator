#!/usr/bin/env python3
"""
Test script: Read.ai webhook for Mike Johnson's Allbirds demo.
This tests the attendee notes feature.
"""

import json
from datetime import datetime, timedelta, timezone

import httpx

# Production configuration
BASE_URL = "https://salesapi.apps.govisually.co"
READAI_SHARED_SECRET = ""  # Empty in production

# Meeting details
MEETING_TIME = datetime.now(timezone.utc) - timedelta(hours=1)  # 1 hour ago
MEETING_START_TIME = MEETING_TIME.isoformat()
MEETING_END_TIME = (MEETING_TIME + timedelta(minutes=40)).isoformat()


def create_readai_payload():
    """Create realistic Read.ai meeting_completed payload"""
    return {
        "session_id": "01MIKE-ALLBIRDS-DEMO-SESSION",
        "trigger": "meeting_end",
        "title": "GoVisually Demo - Allbirds Product Content Review",
        "start_time": MEETING_START_TIME,
        "end_time": MEETING_END_TIME,
        "participants": [
            {
                "name": "Mike Johnson",
                "email": "mike.johnson@allbirds.com"
            },
            {
                "name": "Jennifer Lee",
                "email": "jennifer.lee@allbirds.com"
            },
            {
                "name": "David Chen",
                "email": "david.chen@allbirds.com"
            },
            {
                "name": "GoVisually Sales Rep",
                "email": "demo@govisually.com"
            }
        ],
        "owner": {
            "name": "Mike Johnson",
            "email": "mike.johnson@allbirds.com"
        },
        "summary": """Mike Johnson (Head of Digital Content) from Allbirds met with GoVisually to discuss their product photography and video review challenges. Jennifer Lee (Design Manager) and David Chen (Product Manager) also joined. They're currently using email, Trello, and Google Drive which creates chaos in their feedback process. Mike emphasized the need for better annotation tools and version control for their extensive product photo shoots. Jennifer highlighted challenges coordinating with external photographers. David shared concerns about approval workflows for seasonal campaigns. The team is interested in a trial focused on their upcoming spring collection photoshoot.""",
        "action_items": [
            {
                "text": "GoVisually to send trial access for Allbirds team"
            },
            {
                "text": "Mike to schedule internal kickoff with design and product teams"
            },
            {
                "text": "Jennifer to select pilot project (spring collection)"
            }
        ],
        "key_questions": [
            {
                "text": "Can we integrate with our existing Trello boards?"
            },
            {
                "text": "What's the pricing for a 25-person team with external collaborators?"
            },
            {
                "text": "How does GoVisually handle high-res product photography files?"
            }
        ],
        "topics": [
            {
                "text": "Product photography review workflows"
            },
            {
                "text": "External photographer collaboration"
            },
            {
                "text": "Version control and approval processes"
            },
            {
                "text": "Trello integration possibilities"
            }
        ],
        "report_url": "https://app.read.ai/analytics/meetings/01MIKE-ALLBIRDS-DEMO-SESSION",
        "chapter_summaries": [
            {
                "title": "Introduction and Current Challenges",
                "description": "Team discussed current product content review pain points",
                "topics": [
                    {"text": "Email-based review chaos"},
                    {"text": "External photographer coordination"}
                ]
            },
            {
                "title": "GoVisually Platform Demo",
                "description": "Walkthrough of annotation, version control, and collaboration features",
                "topics": [
                    {"text": "Product photo annotation tools"},
                    {"text": "Version comparison features"}
                ]
            },
            {
                "title": "Next Steps",
                "description": "Trial setup and pilot project planning",
                "topics": [
                    {"text": "Spring collection pilot"},
                    {"text": "Team onboarding plan"}
                ]
            }
        ],
        "transcript": {
            "speakers": [
                {"name": "Mike Johnson"},
                {"name": "Jennifer Lee"},
                {"name": "David Chen"},
                {"name": "GoVisually Sales Rep"}
            ],
            "speaker_blocks": [
                {
                    "start_time": "1734700000000",
                    "end_time": "1734700020000",
                    "speaker": {"name": "Mike Johnson"},
                    "words": "Thanks for meeting with us today. As I mentioned in my booking, we're really struggling with our product photography review process. We shoot hundreds of product photos every month and the email feedback loop is killing our team's productivity."
                },
                {
                    "start_time": "1734700020000",
                    "end_time": "1734700035000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Absolutely, I hear you. Product photography is exactly where GoVisually shines. Let me show you how we can help streamline that process."
                },
                {
                    "start_time": "1734700035000",
                    "end_time": "1734700060000",
                    "speaker": {"name": "Jennifer Lee"},
                    "words": "Hi, I'm Jennifer, Design Manager. One of my biggest headaches is coordinating with our external photographers. We send feedback via email and often things get lost or misunderstood. We need something more visual."
                },
                {
                    "start_time": "1734700060000",
                    "end_time": "1734700085000",
                    "speaker": {"name": "David Chen"},
                    "words": "I'm David, Product Manager. From my side, the approval workflow is a mess. I need to sign off on photos before they go live, but I'm often looking at the wrong version because someone sent me v3 when we're already on v5."
                },
                {
                    "start_time": "1734700085000",
                    "end_time": "1734700115000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Those are exactly the problems we solve. Let me show you our annotation tools - you can click directly on any part of a photo and leave feedback. Photographers see exactly where the issue is, no confusion."
                },
                {
                    "start_time": "1734700115000",
                    "end_time": "1734700145000",
                    "speaker": {"name": "Mike Johnson"},
                    "words": "That looks perfect. And I can see the version history right there on the sidebar. That would save us hours of confusion every week. How does this work with external collaborators?"
                },
                {
                    "start_time": "1734700145000",
                    "end_time": "1734700175000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "External photographers get guest access with a simple link - they don't need to be on your paid plan. They upload new versions, leave notes, and you control all the permissions."
                },
                {
                    "start_time": "1734700175000",
                    "end_time": "1734700205000",
                    "speaker": {"name": "Jennifer Lee"},
                    "words": "This is exactly what we need. Can we integrate this with Trello? We use it heavily for project management."
                },
                {
                    "start_time": "1734700205000",
                    "end_time": "1734700235000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "We have Trello integration - you can push review links directly to your Trello cards. I can show you that in a moment."
                },
                {
                    "start_time": "1734700235000",
                    "end_time": "1734700265000",
                    "speaker": {"name": "David Chen"},
                    "words": "What about file sizes? Our product photos are often 50-100MB each, high-resolution for print."
                },
                {
                    "start_time": "1734700265000",
                    "end_time": "1734700295000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Not a problem at all. We handle files up to 500MB and support all the major image formats. Your high-res files will work perfectly."
                },
                {
                    "start_time": "1734700295000",
                    "end_time": "1734700330000",
                    "speaker": {"name": "Mike Johnson"},
                    "words": "I'm sold. What's the pricing for our team? We have about 25 people internally, plus we work with 5-6 external photographers regularly."
                },
                {
                    "start_time": "1734700330000",
                    "end_time": "1734700365000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "For your team size with external collaborators, you'd be on our Business plan. I'll send you detailed pricing after this call, but the ROI typically pays for itself within the first month just from time savings."
                },
                {
                    "start_time": "1734700365000",
                    "end_time": "1734700400000",
                    "speaker": {"name": "Mike Johnson"},
                    "words": "Let's do a trial. We have our spring collection photoshoot coming up next month - that would be the perfect pilot project."
                },
                {
                    "start_time": "1734700400000",
                    "end_time": "1734700435000",
                    "speaker": {"name": "Jennifer Lee"},
                    "words": "Yes, I'll coordinate that. The spring collection would be ideal - it's our biggest shoot of Q1."
                },
                {
                    "start_time": "1734700435000",
                    "end_time": "1734700470000",
                    "speaker": {"name": "GoVisually Sales Rep"},
                    "words": "Perfect! I'll get you set up today with trial access. Let's schedule a quick onboarding call next week to get your team trained before the shoot."
                },
                {
                    "start_time": "1734700470000",
                    "end_time": "1734700500000",
                    "speaker": {"name": "Mike Johnson"},
                    "words": "Sounds great. Thanks everyone, this is exactly what we've been looking for."
                }
            ]
        }
    }


def send_readai_webhook():
    """Send Read.ai webhook to production"""
    print("\n" + "="*80)
    print("Testing Read.ai Webhook with Attendee Notes")
    print("="*80)

    payload = create_readai_payload()

    print(f"\nPayload preview:")
    print(f"  Session ID: {payload['session_id']}")
    print(f"  Title: {payload['title']}")
    print(f"  Meeting Owner: {payload['owner']['name']} <{payload['owner']['email']}>")
    print(f"  Attendees:")
    for p in payload['participants']:
        print(f"    - {p['name']} <{p['email']}>")
    print(f"  Duration: 40 minutes")
    print(f"  Transcript blocks: {len(payload['transcript']['speaker_blocks'])}")

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
                print(f"\n🎉 SUCCESS! Read.ai webhook queued")
                print(f"Event ID: {data.get('event_id')}")
                print(f"Idempotency Key: {data.get('idempotency_key')}")
                return True
            elif data.get("duplicate"):
                print(f"\n⚠️  DUPLICATE: Event already processed")
                return True
        else:
            print(f"\n❌ FAILED: {response.text}")
            return False

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


def main():
    print("\n" + "📊"*40)
    print("READ.AI WEBHOOK TEST: Mike Johnson from Allbirds")
    print("📊"*40)
    print("\nThis tests:")
    print("  1. Read.ai webhook processing")
    print("  2. MEDDIC extraction from transcript")
    print("  3. Attendee notes with speaking stats")
    print("  4. Matching to existing Calendly lead")
    print("\nTarget environment: PRODUCTION")
    print(f"Base URL: {BASE_URL}")
    print("\n" + "="*80)

    input("\nPress Enter to send webhook...")

    success = send_readai_webhook()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Read.ai webhook: {'✅ SUCCESS' if success else '❌ FAILED'}")
    print("\n📊 Monitor worker logs and check Zoho CRM for:")
    print("   Email: mike.johnson@allbirds.com")
    print("   Company: Allbirds")
    print("\n📝 Expected in Zoho:")
    print("   ✅ Lead status updated to 'Demo Complete'")
    print("   ✅ MEDDIC fields populated")
    print("   ✅ Read.ai Demo Summary note created")
    print("   ✅ Meeting Attendees section showing:")
    print("      - Mike Johnson (Meeting Owner)")
    print("      - Jennifer Lee")
    print("      - David Chen")
    print("      - GoVisually Sales Rep (Internal)")
    print("   ✅ Speaking stats and sample quotes for each person")
    print("\n💡 Check the note content in Zoho to see the new attendee tracking!")
    print("="*80)


if __name__ == "__main__":
    main()
