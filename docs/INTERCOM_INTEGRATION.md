# Intercom → Zoho CRM Integration

**Tag-based workflow to qualify support contacts for sales outreach**

## Overview

The Intercom integration automatically creates Zoho CRM leads when support contacts are tagged as sales-qualified. When a support team member tags a contact with "Lead" in Intercom, a webhook triggers that:

1. Extracts 15+ fields from the Intercom contact
2. Creates/updates a Zoho Lead with all available data
3. Optionally enriches with Apollo.io + website scraping
4. Creates a detailed note with direct link to Intercom conversation
5. Sends Slack notification with key details

## Configuration

### Environment Variables

```bash
# Required
INTERCOM_API_KEY=dG9rOmIxYTgxMTE0X...  # Intercom Access Token
INTERCOM_QUALIFYING_TAGS=Lead          # Comma-separated list of tags

# Optional
INTERCOM_WEBHOOK_SECRET=               # For webhook signature verification
INTERCOM_ADMIN_ID=3610925              # Your Intercom admin ID
STATUS_SUPPORT_QUALIFIED=Qualified     # Zoho lead status for Intercom leads
ENABLE_AUTO_ENRICH_INTERCOM=true       # Auto-enrich with Apollo + Website
```

### Webhook Setup in Intercom

1. Go to **Intercom Dashboard** → **Settings** → **Developer Hub** → **Webhooks**
2. Click **"New webhook"**
3. Configure:
   - **Endpoint URL**: `https://your-domain.com/webhooks/intercom`
   - **Topics**: Check both:
     - ✅ `contact.user.tag.created`
     - ✅ `contact.lead.tag.created`
4. Click **"Save"**

### Testing the Webhook

Use the test script:
```bash
python3 scripts/test_intercom_lead_tag.py
```

Or tag a real contact in Intercom:
1. Go to **Intercom** → **Contacts**
2. Select any contact with an email
3. Add the **"Lead"** tag
4. Check worker logs and Zoho CRM

## Data Mapping

### Standard Zoho Fields

| Zoho Field | Source | Example |
|------------|--------|---------|
| `Email` | Intercom contact email | `emma@craftbrew.io` |
| `First_Name` | Parsed from contact name | `Emma` |
| `Last_Name` | Parsed from contact name | `Wilson` |
| `Phone` | Intercom contact phone | `+1-555-789-0123` |
| `Company` | Associated company name | `CraftBrew` |
| `Website` | Associated company website | `https://craftbrew.io` |
| `Industry` | Associated company industry | `Food & Beverage` |
| `No_of_Employees` | Associated company size | `45` |
| `Country` | Contact location country | `United States` |
| `State` | Contact location region | `California` |
| `City` | Contact location city | `San Francisco` |
| `Lead_Source` | Always "Intercom" | `Intercom` |
| `Lead_Status` | Configurable via env | `Qualified` |

### Description Field (GoVisually-Specific)

The `Description` field captures valuable GoVisually usage data:

```
Plan Type: team
GoVisually Version: 1.81.6
User Type: primary
PM Tool: Clickup, Proofing Tool: Nothing at the moment
```

**Custom Attributes Mapped:**
- `plan_type` → Plan tier (team, enterprise, etc.)
- `gv_version` → Product version in use
- `user_type` → User role (primary, guest, etc.)
- `project_management_tool_used` → Current PM tool (competitive intel)
- `proofing_tool_used` → Current proofing solution (competitive intel)

## Zoho Note Content

A detailed note is created in Zoho with the following structure:

### Example Note

```markdown
## Intercom Contact Qualified

[View in Intercom](https://app.intercom.com/a/apps/wfkef3s2/users/69443551bc4e32ab1fe5b2e4/all-conversations)

**Contact ID:** 69443551bc4e32ab1fe5b2e4
**Qualifying Tags:** Lead

### Engagement
**Signed Up:** 2025-12-18T17:09:28.000+00:00
**Last Seen:** 2025-12-19T01:00:33.283+00:00

### Location
San Francisco, California, United States

### Device Information
**Browser:** microsoft edge 143.0.0.0
**OS:** Windows 10

### Company Information
**Name:** Crocker Art Museum
**Website:** https://crockerart.org

### GoVisually Usage
**Plan Type:** team
**Version:** 1.81.6
**User Type:** primary
**Initial Channel:** I've been sent an artwork for review
**Main Goal:** Other
**Job Role:** Other

### Tools Currently Using
**Project Management:** Clickup
**Proofing Tool:** Nothing at the moment

### Other Attributes
**company_type:** Non-Profit
**user:** aduncan@crockerart.org
```

### Fields Included

**Engagement Metrics:**
- Signed up date (when they first joined GoVisually)
- Last seen date (recent activity)

**Location Data:**
- City, Region/State, Country
- Helps sales reps with timezone planning and regional context

**Device Information:**
- Browser and version
- Operating system
- Useful for technical troubleshooting and feature adoption

**Company Information:**
- Company name (from Intercom association)
- Website
- Company size
- Industry

**GoVisually Usage:**
- Plan type, version, user type
- Initial channel (how they first engaged)
- Main goal, job role
- Competitive intel (current PM tool, proofing tool)

**Intercom Link:**
- Direct clickable link to view the full conversation history in Intercom

## Slack Notification

When a contact is qualified, a Slack notification is sent with:

```
🎯 Support Contact Qualified

Email: emma.wilson@craftbrew.io
Name: Emma Wilson
Company: CraftBrew
Qualifying Tags: Lead
Location: San Francisco, California, United States
Plan Type: team
Zoho Lead ID: 123456789
```

## Auto-Enrichment

When `ENABLE_AUTO_ENRICH_INTERCOM=true` (default), leads are automatically enriched with:

### Apollo.io Enrichment
- Job title, seniority, department
- LinkedIn URL, additional phone numbers
- Company funding, tech stack

### Website Scraping
- Multi-page website intelligence (Crawl4AI)
- Company description, products/services
- Pricing, competitors, sales approach tactics

### Company Logo
- Automatic logo upload via BrandFetch

All enrichment data is added as a separate note in Zoho.

## Workflow Example

1. **Support Conversation**
   - Customer `aduncan@crockerart.org` contacts support via Intercom
   - Support team helps them with an issue
   - They mention interest in upgrading their plan

2. **Qualification**
   - Support rep tags contact with "Lead"
   - Webhook fires to your API

3. **Automatic Processing**
   - API validates webhook signature
   - Stores event in Redis
   - Enqueues background job

4. **Lead Creation**
   - Worker extracts all Intercom data
   - Creates Zoho lead with 15+ fields
   - Links to Intercom conversation
   - Triggers auto-enrichment (if enabled)

5. **Sales Handoff**
   - Sales rep receives Slack notification
   - Opens Zoho lead to see full context:
     - What plan they're on (`team`)
     - What tools they currently use (`Clickup`, `Nothing at the moment`)
     - Their location (`San Francisco, CA`)
     - Direct link to Intercom conversation history
     - Website intelligence and Apollo data

6. **Sales Outreach**
   - Rep has full context for personalized outreach
   - Can reference their current setup and pain points
   - Can click through to Intercom to see support conversation history

## Multiple Tag Support (Future Enhancement)

Currently configured for single tag: "Lead"

To add more qualifying tags in the future:
```bash
INTERCOM_QUALIFYING_TAGS=Lead,Hot,Enterprise,Expansion
```

Each tag will trigger the same workflow.

## Idempotency

Webhook events are deduplicated using:
```
Key: intercom:{topic}:{contact_id}:{created_at}
TTL: 90 days
```

This prevents duplicate lead creation if:
- Intercom retries a failed webhook
- Same contact is tagged multiple times rapidly
- Webhook is accidentally triggered twice

## Troubleshooting

### Webhook not triggering

**Check webhook configuration:**
1. Go to Intercom → Settings → Developer Hub → Webhooks
2. Click on your webhook
3. Check "Recent deliveries" tab
4. Verify webhooks are being sent and response code is 200

**Common issues:**
- Wrong endpoint URL
- Topics not selected (need both `contact.user.tag.created` and `contact.lead.tag.created`)
- Network/firewall blocking requests

### Lead not created in Zoho

**Check worker logs:**
```bash
docker logs gv-sales-integrator-worker-1 -f
```

**Common issues:**
- Contact has no email address (required)
- Tag name doesn't match `INTERCOM_QUALIFYING_TAGS` (case-sensitive)
- Zoho API credentials invalid
- `DRY_RUN=true` (won't write to Zoho)

### Signature verification failing

If you set `INTERCOM_WEBHOOK_SECRET`:
- Verify the secret matches between Intercom and your `.env`
- Check for leading/trailing whitespace in the secret

If not set, signature verification is skipped (logged as warning).

### Missing data in Zoho note

Some fields are optional and only appear if available:
- Company data (only if contact associated with company in Intercom)
- Location (only if Intercom has captured it)
- Custom attributes (only if set in Intercom)
- Device info (only if contact has accessed GoVisually)

## API Reference

### Webhook Endpoint

**POST** `/webhooks/intercom`

**Headers:**
- `Content-Type: application/json`
- `X-Intercom-Signature: <hmac-sha256>` (optional)

**Supported Topics:**
- `contact.user.tag.created` - User tagged
- `contact.lead.tag.created` - Lead tagged

**Response:**
```json
{
  "ok": true,
  "queued": true,
  "event_id": "89421069-5119-4f9d-9b70-aae5d2f6b02e",
  "idempotency_key": "intercom:contact.user.tag.created:69443551:1766147339"
}
```

**Ignored Response** (tag not qualifying):
```json
{
  "ok": true,
  "ignored": true,
  "reason": "tag_not_qualifying",
  "tag": "Support",
  "qualifying_tags": ["Lead"]
}
```

**Duplicate Response:**
```json
{
  "ok": true,
  "duplicate": true,
  "event_id": "previous-event-id"
}
```

## Files

**Implementation:**
- `app/api/routes_webhooks_intercom.py` - Webhook endpoint
- `app/jobs/intercom_jobs.py` - Background job processor
- `app/services/intercom_service.py` - Data extraction and formatting
- `app/schemas/intercom.py` - Pydantic models

**Testing:**
- `scripts/test_intercom_lead_tag.py` - Test script
- `scripts/test_intercom_connection.py` - API connection test

**Documentation:**
- `docs/INTERCOM_INTEGRATION.md` - This file
