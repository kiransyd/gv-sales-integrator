#!/usr/bin/env python3
"""
Test script: John Citizen from Kettle & Fire books a Calendly meeting,
then has a Read.ai recorded meeting with Mary, Alima, and Chad.

This tests the complete flow:
1. Calendly webhook (invitee.created) for John Citizen
2. Read.ai webhook (meeting_completed) with multiple attendees
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import httpx

# Production configuration
BASE_URL = "https://salesapi.apps.govisually.co"
CALENDLY_SIGNING_KEY = "m6nb-XWn5X7791jp09V9M9dTqsW4Hqw_-ani7I5Tvl4"
READAI_SHARED_SECRET = ""  # Empty in production - will pass

# Meeting details
MEETING_TIME = datetime.now(timezone.utc) + timedelta(days=2)
MEETING_START_TIME = MEETING_TIME.isoformat()
MEETING_END_TIME = (MEETING_TIME + timedelta(minutes=45)).isoformat()


def generate_calendly_signature(payload_bytes: bytes, signing_key: str) -> str:
    """Generate Calendly webhook signature"""
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
    signature = hmac.new(
        signing_key.encode("utf-8"),
        signed_payload,
        hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def create_calendly_payload():
    """Create realistic Calendly invitee.created payload for John Citizen"""
    return {
        "event": "invitee.created",
        "payload": {
            "invitee": {
                "email": "john.citizen@kettleandfire.com",
                "name": "John Citizen",
                "uri": "https://api.calendly.com/scheduled_events/test-john-kf-event/invitees/test-john-kf-invitee",
                "uuid": "test-john-kf-invitee"
            },
            "event": {
                "uri": "https://api.calendly.com/scheduled_events/test-john-kf-event",
                "uuid": "test-john-kf-event",
                "start_time": MEETING_START_TIME,
                "timezone": "America/Los_Angeles"
            },
            "questions_and_answers": [
                {
                    "question": "What is your company name?",
                    "answer": "Kettle & Fire"
                },
                {
                    "question": "What is your company website?",
                    "answer": "https://www.kettleandfire.com"
                },
                {
                    "question": "What is your role?",
                    "answer": "VP of Marketing"
                },
                {
                    "question": "How many people are on your team?",
                    "answer": "15-20 people"
                },
                {
                    "question": "What are your main pain points?",
                    "answer": "We need a better way to collaborate with our external agency on video content reviews. Currently using email and it's a mess - lots of back and forth, lost feedback, version control issues."
                },
                {
                    "question": "What tools do you currently use?",
                    "answer": "Asana for project management, Google Drive for file sharing, email for feedback loops"
                },
                {
                    "question": "What would you like to see in the demo?",
                    "answer": "How we can streamline video reviews with our agency, better feedback workflows, and version control"
                },
                {
                    "question": "How did you hear about us?",
                    "answer": "Recommended by colleague at another DTC brand"
                }
            ],
            "event_type": "https://api.calendly.com/event_types/FBHFVVJGIXH2RYRF"
        }
    }


def create_readai_payload():
    """Create realistic Read.ai meeting_completed payload with multiple attendees"""
    return {
        "session_id": "01KCTV7J1AEMB269BR9GTSD1DK-JOHN-KF",
        "trigger": "meeting_end",
        "title": "GoVisually Demo - Kettle & Fire",
        "start_time": MEETING_START_TIME,
        "end_time": MEETING_END_TIME,
        "participants": [
            {
                "name": "John Citizen",
                "email": "john.citizen@kettleandfire.com"
            },
            {
                "name": "Mary Thompson",
                "email": "mary.thompson@kettleandfire.com"
            },
            {
                "name": "Alima Patel",
                "email": "alima.patel@kettleandfire.com"
            },
            {
                "name": "Chad Williams",
                "email": "chad.williams@kettleandfire.com"
            },
            {
                "name": "GoVisually Rep",
                "email": "demo@govisually.com"
            }
        ],
        "owner": {
            "name": "John Citizen",
            "email": "john.citizen@kettleandfire.com"
        },
        "summary": """In this demo meeting, the Kettle & Fire team discussed their video content review challenges with the GoVisually team. John Citizen (VP of Marketing) explained their current process using email and Google Drive is inefficient and causing version control issues. Mary Thompson (Creative Director) emphasized the need for better collaboration with their external agency. Alima Patel (Brand Manager) highlighted specific pain points around feedback loops taking too long. Chad Williams (Video Producer) shared examples of lost feedback and confusion around which version is final. The team is looking for a solution that can streamline their video review process, improve agency collaboration, and provide better version control.""",
        "action_items": [
            {
                "text": "John to schedule internal team review of GoVisually trial"
            },
            {
                "text": "Mary to coordinate with agency on GoVisually pilot project"
            },
            {
                "text": "GoVisually to send trial access and onboarding materials"
            }
        ],
        "key_questions": [
            {
                "text": "How does GoVisually handle external agency access and permissions?"
            },
            {
                "text": "What integrations are available with Asana?"
            },
            {
                "text": "What's the pricing for a team of 20 with external collaborators?"
            }
        ],
        "topics": [
            {
                "text": "Video content review workflows"
            },
            {
                "text": "Agency collaboration challenges"
            },
            {
                "text": "Version control and feedback management"
            },
            {
                "text": "Integration with existing tools"
            }
        ],
        "report_url": "https://app.read.ai/analytics/meetings/01KCTV7J1AEMB269BR9GTSD1DK-JOHN-KF",
        "chapter_summaries": [
            {
                "title": "Introduction and Current Challenges",
                "description": "Team introduced themselves and discussed current video review process pain points",
                "topics": [
                    {
                        "text": "Current workflow using email and Google Drive"
                    },
                    {
                        "text": "Version control issues"
                    }
                ]
            },
            {
                "title": "GoVisually Platform Demo",
                "description": "GoVisually rep demonstrated video review features and collaboration tools",
                "topics": [
                    {
                        "text": "Video annotation and feedback features"
                    },
                    {
                        "text": "External collaborator access"
                    }
                ]
            },
            {
                "title": "Next Steps and Trial Setup",
                "description": "Discussed trial timeline and implementation plan",
                "topics": [
                    {
                        "text": "Trial setup and team onboarding"
                    },
                    {
                        "text": "Pilot project with agency"
                    }
                ]
            }
        ],
        "transcript": {
            "speakers": [
                {"name": "John Citizen"},
                {"name": "Mary Thompson"},
                {"name": "Alima Patel"},
                {"name": "Chad Williams"},
                {"name": "GoVisually Rep"}
            ],
            "speaker_blocks": [
                {
                    "start_time": "1734600000000",
                    "end_time": "1734600015000",
                    "speaker": {"name": "John Citizen"},
                    "words": "Hi everyone, thanks for joining. I'm John, VP of Marketing at Kettle & Fire. We're really excited to see how GoVisually can help us streamline our video content review process with our external agency."
                },
                {
                    "start_time": "1734600015000",
                    "end_time": "1734600030000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "Great to meet you all! Thanks for taking the time today. I'm looking forward to showing you how we can help solve those video review challenges."
                },
                {
                    "start_time": "1734600030000",
                    "end_time": "1734600050000",
                    "speaker": {"name": "Mary Thompson"},
                    "words": "Hi, I'm Mary, Creative Director. Our biggest pain point is the back-and-forth with our agency. Right now we're using email threads and it's just chaos - lost feedback, unclear versions, so much wasted time."
                },
                {
                    "start_time": "1734600050000",
                    "end_time": "1734600070000",
                    "speaker": {"name": "Alima Patel"},
                    "words": "I'm Alima, Brand Manager. I agree with Mary - the feedback loops take forever. Sometimes we're three or four email rounds deep before we get clarity on simple things."
                },
                {
                    "start_time": "1734600070000",
                    "end_time": "1734600095000",
                    "speaker": {"name": "Chad Williams"},
                    "words": "Chad here, I'm the Video Producer. From a production standpoint, the version control is a nightmare. I've had situations where we've gone back to edit version 3 when the client wanted changes to version 5. It's really frustrating."
                },
                {
                    "start_time": "1734600095000",
                    "end_time": "1734600120000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "Those are exactly the problems GoVisually solves. Let me show you our video review interface. You can see here how all feedback is timestamped and attached directly to the video frame."
                },
                {
                    "start_time": "1734600120000",
                    "end_time": "1734600145000",
                    "speaker": {"name": "John Citizen"},
                    "words": "This is really impressive. I can see how this would eliminate so much confusion. How does this work with external collaborators like our agency?"
                },
                {
                    "start_time": "1734600145000",
                    "end_time": "1734600170000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "Great question. You can invite external collaborators with guest access - they don't need to be on your paid plan. They get a link and can leave feedback directly on the video. All permissions are controlled by you."
                },
                {
                    "start_time": "1734600170000",
                    "end_time": "1734600195000",
                    "speaker": {"name": "Mary Thompson"},
                    "words": "That's perfect. And I can see the version history here on the sidebar. This alone would save us hours every week."
                },
                {
                    "start_time": "1734600195000",
                    "end_time": "1734600220000",
                    "speaker": {"name": "Alima Patel"},
                    "words": "What about integrations? We use Asana pretty heavily for project management."
                },
                {
                    "start_time": "1734600220000",
                    "end_time": "1734600245000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "We have Asana integration - you can push review links and updates directly to your Asana tasks. I can show you that in a moment."
                },
                {
                    "start_time": "1734600245000",
                    "end_time": "1734600270000",
                    "speaker": {"name": "Chad Williams"},
                    "words": "This looks really solid. I think this could solve a lot of our headaches. What's the pricing look like for our team size?"
                },
                {
                    "start_time": "1734600270000",
                    "end_time": "1734600300000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "For a team of 20 with external collaborators, you'd be looking at our Business plan. I'll send you detailed pricing after this call, but the ROI is typically realized within the first month just from time savings."
                },
                {
                    "start_time": "1734600300000",
                    "end_time": "1734600330000",
                    "speaker": {"name": "John Citizen"},
                    "words": "That sounds reasonable. I'd like to move forward with a trial. Can we get set up this week and maybe run a pilot project with our agency?"
                },
                {
                    "start_time": "1734600330000",
                    "end_time": "1734600360000",
                    "speaker": {"name": "GoVisually Rep"},
                    "words": "Absolutely! I'll send you trial access today along with onboarding materials. We can schedule a quick setup call later this week to get your team and agency onboarded."
                },
                {
                    "start_time": "1734600360000",
                    "end_time": "1734600390000",
                    "speaker": {"name": "Mary Thompson"},
                    "words": "Perfect. I'll coordinate with our agency contact to make sure they're ready to participate in the pilot."
                },
                {
                    "start_time": "1734600390000",
                    "end_time": "1734600420000",
                    "speaker": {"name": "John Citizen"},
                    "words": "Great, thanks everyone. This looks like exactly what we need. Looking forward to getting started."
                }
            ]
        }
    }


def send_calendly_webhook():
    """Send Calendly webhook to production"""
    print("\n" + "="*80)
    print("STEP 1: Sending Calendly Webhook (invitee.created)")
    print("="*80)

    payload = create_calendly_payload()
    payload_bytes = json.dumps(payload).encode('utf-8')
    signature = generate_calendly_signature(payload_bytes, CALENDLY_SIGNING_KEY)

    print(f"\nPayload preview:")
    print(f"  Event: {payload['event']}")
    print(f"  Invitee: {payload['payload']['invitee']['name']} <{payload['payload']['invitee']['email']}>")
    print(f"  Company: Kettle & Fire")
    print(f"  Meeting time: {payload['payload']['event']['start_time']}")

    headers = {
        "Content-Type": "application/json",
        "Calendly-Webhook-Signature": signature
    }

    url = f"{BASE_URL}/webhooks/calendly"
    print(f"\nSending to: {url}")

    try:
        response = httpx.post(url, content=payload_bytes, headers=headers, timeout=30.0)
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            data = response.json()
            if data.get("queued"):
                print(f"\n🎉 SUCCESS! Calendly webhook queued")
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


def send_readai_webhook():
    """Send Read.ai webhook to production"""
    print("\n" + "="*80)
    print("STEP 2: Sending Read.ai Webhook (meeting_completed)")
    print("="*80)

    payload = create_readai_payload()

    print(f"\nPayload preview:")
    print(f"  Session ID: {payload['session_id']}")
    print(f"  Title: {payload['title']}")
    print(f"  Meeting Owner: {payload['owner']['name']} <{payload['owner']['email']}>")
    print(f"  Attendees:")
    for p in payload['participants']:
        print(f"    - {p['name']} <{p['email']}>")
    print(f"  Duration: 45 minutes")
    print(f"  Transcript blocks: {len(payload['transcript']['speaker_blocks'])}")

    headers = {
        "Content-Type": "application/json"
    }

    # Add Read.ai secret header if set (empty in production, so skip)
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
    print("\n" + "🔥"*40)
    print("TESTING: John Citizen from Kettle & Fire")
    print("🔥"*40)
    print("\nThis will:")
    print("1. Send Calendly webhook for John Citizen booking a demo")
    print("2. Send Read.ai webhook for the recorded meeting with 4 Kettle & Fire team members")
    print("\nTarget environment: PRODUCTION")
    print(f"Base URL: {BASE_URL}")
    print("\n" + "="*80)

    input("\nPress Enter to continue...")

    # Step 1: Calendly webhook
    calendly_success = send_calendly_webhook()

    if not calendly_success:
        print("\n❌ Calendly webhook failed. Stopping.")
        return

    # Wait a bit for processing
    print("\n⏳ Waiting 5 seconds for Calendly webhook to process...")
    time.sleep(5)

    # Step 2: Read.ai webhook
    readai_success = send_readai_webhook()

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Calendly webhook: {'✅ SUCCESS' if calendly_success else '❌ FAILED'}")
    print(f"Read.ai webhook:  {'✅ SUCCESS' if readai_success else '❌ FAILED'}")
    print("\n📊 Check Zoho CRM for the lead:")
    print("   Email: john.citizen@kettleandfire.com")
    print("   Company: Kettle & Fire")
    print("\n📝 Expected in Zoho:")
    print("   ✅ Lead created from Calendly")
    print("   ✅ MEDDIC data from Read.ai")
    print("   ✅ Meeting Attendees section with 5 people (4 external, 1 internal)")
    print("   ✅ Speaking stats and sample quotes")
    print("   ✅ Meeting owner: John Citizen")
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
