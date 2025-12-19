# Slack Event Notifications Guide

This document explains how to send events to your Slack channel using the enhanced Slack integration.

## Overview

The app now sends rich Slack notifications for key events in your sales pipeline:

- ✅ **New Demo Booked** - When someone books a demo via Calendly
- ❌ **Demo Canceled** - When a demo is canceled
- ✅ **Demo Completed** - When a Read.ai meeting is completed and MEDDIC analysis is added
- 🔍 **Lead Enrichment Complete** - When auto-enrichment finishes (Apollo + Website scraping)

## Setup

### 1. Get Your Slack Webhook URL

1. Go to https://api.slack.com/apps
2. Create a new app or select an existing one
3. Go to **Incoming Webhooks** → **Activate Incoming Webhooks**
4. Click **Add New Webhook to Workspace**
5. Select the channel where you want notifications
6. Copy the webhook URL (looks like: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`)

### 2. Configure in `.env`

Add your Slack webhook URL to your `.env` file:

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

**If using Pabbly Connect or other intermediaries**, also set the format mode:

```bash
# For Pabbly Connect (recommended)
SLACK_FORMAT_MODE=attachments

# OR for plain text (most compatible)
SLACK_FORMAT_MODE=text

# OR for direct Slack webhooks (default)
SLACK_FORMAT_MODE=blocks
```

See `SLACK_PABBLY_COMPATIBILITY.md` for details on format modes.

### 3. Restart Services

Restart your API and worker services to pick up the new configuration:

```bash
docker compose restart api worker
```

## Event Types

### 🎯 New Demo Booked

**When it fires:** Every time a Calendly `invitee.created` webhook is processed successfully.

**What it includes:**
- Lead email
- Lead name
- Company name
- Demo date/time
- Zoho Lead ID

**Example notification:**
```
🎯 New Demo Booked
John Doe from Acme Corp has booked a demo.

Email: john@acme.com
Name: John Doe
Company: Acme Corp
Demo Date: Dec 20, 2024 at 2:00 PM EST
Zoho Lead ID: 1234567890
```

### ❌ Demo Canceled

**When it fires:** Every time a Calendly `invitee.canceled` webhook is processed.

**What it includes:**
- Lead email
- Lead name
- Company name (if available)
- Zoho Lead ID

**Example notification:**
```
❌ Demo Canceled
Jane Smith from TechCo has canceled their demo.

Email: jane@techco.com
Name: Jane Smith
Company: TechCo
Zoho Lead ID: 1234567891
```

### ✅ Demo Completed

**When it fires:** Every time a Read.ai `meeting.completed` webhook is processed and MEDDIC analysis is added to Zoho.

**What it includes:**
- Lead email
- Lead name
- Company name
- Meeting duration
- MEDDIC confidence level
- Zoho Lead ID

**Example notification:**
```
✅ Demo Completed
Demo meeting completed for John Doe from Acme Corp. MEDDIC analysis added to Zoho.

Email: john@acme.com
Name: John Doe
Company: Acme Corp
Duration: 45 minutes
MEDDIC Confidence: High
Zoho Lead ID: 1234567890
```

### 🔍 Lead Enrichment Complete

**When it fires:** After auto-enrichment completes for a Calendly lead (if `ENABLE_AUTO_ENRICH_CALENDLY=true`).

**What it includes:**
- Lead email
- Company name
- Data sources used (e.g., "apollo_person, apollo_company, website")
- Zoho Lead ID

**Example notification:**
```
🔍 Lead Enrichment Complete
Auto-enrichment completed for john@acme.com from Acme Corp.

Email: john@acme.com
Company: Acme Corp
Data Sources: apollo_person, apollo_company, website
Zoho Lead ID: 1234567890
```

## Customization

### Disable Specific Notifications

If you want to disable certain notifications, you can comment out the notification calls in the job files:

- **Disable demo booked notifications:** Comment out `notify_demo_booked()` in `app/jobs/calendly_jobs.py`
- **Disable demo canceled notifications:** Comment out `notify_demo_canceled()` in `app/jobs/calendly_jobs.py`
- **Disable demo completed notifications:** Comment out `notify_demo_completed()` in `app/jobs/readai_jobs.py`
- **Disable enrichment notifications:** Comment out `notify_enrichment_completed()` in `app/jobs/calendly_jobs.py`

### Custom Messages

You can create custom Slack notifications by using the `send_slack_event()` function directly:

```python
from app.services.slack_service import send_slack_event

send_slack_event(
    title="🎉 Custom Event",
    message="This is a custom notification",
    color="good",  # "good", "warning", or "danger"
    fields=[
        {"title": "Field 1", "value": "Value 1"},
        {"title": "Field 2", "value": "Value 2"},
    ],
)
```

### Simple Text Alerts

For simple text-only alerts, use `send_slack_alert()`:

```python
from app.services.slack_service import send_slack_alert

send_slack_alert(text="Simple alert message")
```

## Troubleshooting

### Notifications Not Appearing

1. **Check webhook URL:** Verify `SLACK_WEBHOOK_URL` is set correctly in `.env`
2. **Check logs:** Look for Slack-related warnings in worker logs:
   ```bash
   docker compose logs worker | grep -i slack
   ```
3. **Test webhook:** Test your webhook URL manually:
   ```bash
   curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
     -H 'Content-Type: application/json' \
     -d '{"text":"Test message"}'
   ```

### Notifications Too Frequent

If you're getting too many notifications, you can:
- Disable specific event types (see "Disable Specific Notifications" above)
- Remove the notification calls from the job files
- Set up Slack channel filters to mute certain notification types

### Missing Information

Some fields may be empty if:
- The data isn't available in the webhook payload
- LLM extraction didn't find the information
- The lead doesn't exist in Zoho yet

The notifications will still send, but some fields may show "N/A" or be empty.

## Architecture

### How It Works

1. **Event Processing:** When a webhook is received and processed successfully, the job calls the appropriate notification function
2. **Slack Service:** The `slack_service.py` module formats the message using Slack Block Kit
3. **Webhook POST:** The formatted message is sent to your Slack webhook URL
4. **Error Handling:** If Slack fails, it's logged but doesn't crash the job (failures are silent)

### Files Modified

- `app/services/slack_service.py` - Enhanced with event notification functions
- `app/jobs/calendly_jobs.py` - Added notifications for demo booked/canceled and enrichment
- `app/jobs/readai_jobs.py` - Added notifications for demo completed

### Existing Functionality

The existing failure alert functionality (in `app/jobs/retry.py`) remains unchanged. You'll still get alerts when jobs fail after retries or on permanent errors.

## Best Practices

1. **Use a dedicated channel:** Create a `#sales-pipeline` or `#demo-notifications` channel for these alerts
2. **Set up filters:** Use Slack's notification settings to control when you're notified
3. **Monitor volume:** If you have many demos, consider disabling enrichment notifications (they fire for every booking)
4. **Test first:** Test with `DRY_RUN=true` to see notifications without affecting production

## Example Workflow

Here's what happens when a new demo is booked:

1. **Calendly webhook arrives** → Stored in Redis → Job enqueued
2. **Worker processes job** → Extracts lead info → Calls LLM → Updates Zoho
3. **Slack notification sent** → "🎯 New Demo Booked" appears in your channel
4. **Auto-enrichment starts** → Apollo + Website scraping → Updates Zoho
5. **Enrichment notification sent** → "🔍 Lead Enrichment Complete" appears

When the demo completes:

1. **Read.ai webhook arrives** → Stored in Redis → Job enqueued
2. **Worker processes job** → Extracts transcript → Calls LLM for MEDDIC → Updates Zoho
3. **Slack notification sent** → "✅ Demo Completed" appears in your channel

---

**Need help?** Check the main README.md or ARCHITECTURE.md for more details about the system.
