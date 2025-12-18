# Apollo + Website Enrichment - Implementation Guide

## What Was Built

A comprehensive lead enrichment system that combines:
1. **Apollo.io** person + company enrichment
2. **Website scraping** with LLM analysis
3. **Automatic enrichment** on Calendly webhooks
4. **Manual enrichment** via API endpoint (for Zoho button)

## Features

### Automatic Enrichment (Calendly)
When a demo is booked via Calendly:
- ✅ Apollo enriches person (job title, seniority, LinkedIn, phone)
- ✅ Apollo enriches company (size, revenue, industry, funding, tech stack)
- ✅ Website scraper analyzes company website (value prop, products, competitors)
- ✅ LLM extracts sales intelligence from website content
- ✅ All data automatically updates Zoho Lead
- ✅ Creates formatted enrichment note in Zoho

### Manual Enrichment (Zoho Button)
Sales rep clicks button in Zoho CRM:
- ✅ Same enrichment as automatic
- ✅ Works for any lead (not just Calendly)
- ✅ Re-enrichment capability (update stale data)
- ✅ Processes in 30-60 seconds

---

## Configuration

### Apollo API Tier Note

**Important:** Apollo.io has different API tiers:
- ✅ **Person Enrichment**: Available on most tiers (works with current API key)
- ⚠️ **Company Enrichment**: May require higher tier (returns 403 if not accessible)

If company enrichment is not available on your tier:
- Person enrichment + website scraping will still provide valuable data
- Consider upgrading Apollo tier for full company intelligence (size, revenue, funding, tech stack)
- Basic company info (name, industry, employee count) may be available in person enrichment response

### Environment Variables Added to `.env`

```bash
# Apollo.io
APOLLO_API_KEY=nfCSK9tOe_DdQYY6mc7zGw
APOLLO_CACHE_TTL_DAYS=30

# ScraperAPI
SCRAPER_API_KEY=eefd8d9db0ee8393fc4795706c2df8f5
SCRAPER_MAX_PAGES=5

# Enrichment Settings
ENABLE_AUTO_ENRICH_CALENDLY=true    # Auto-enrich on Calendly webhook
ENABLE_WEBSITE_SCRAPING=true         # Include website intelligence
ENRICH_SECRET_KEY=enrich_secret_2025 # Protect manual enrichment endpoint

# Apollo Zoho Field Mappings (create these custom fields in Zoho Leads)
ZCF_APOLLO_JOB_TITLE=Apollo_Job_Title
ZCF_APOLLO_SENIORITY=Apollo_Seniority
ZCF_APOLLO_DEPARTMENT=Apollo_Department
ZCF_APOLLO_LINKEDIN_URL=Apollo_LinkedIn_URL
ZCF_APOLLO_PHONE=Apollo_Phone
ZCF_APOLLO_COMPANY_SIZE=Apollo_Company_Size
ZCF_APOLLO_COMPANY_REVENUE=Apollo_Company_Revenue
ZCF_APOLLO_COMPANY_INDUSTRY=Apollo_Company_Industry
ZCF_APOLLO_COMPANY_FOUNDED_YEAR=Apollo_Company_Founded_Year
ZCF_APOLLO_COMPANY_FUNDING_STAGE=Apollo_Company_Funding_Stage
ZCF_APOLLO_COMPANY_FUNDING_TOTAL=Apollo_Company_Funding_Total
ZCF_APOLLO_TECH_STACK=Apollo_Tech_Stack
```

---

## Zoho CRM Setup

### Step 1: Create Custom Fields

Go to Zoho CRM → Settings → Customization → Modules → Leads → Layout Rules

Create these custom fields (type: Single Line):
- `Apollo_Job_Title`
- `Apollo_Seniority`
- `Apollo_Department`
- `Apollo_LinkedIn_URL`
- `Apollo_Phone`
- `Apollo_Company_Size`
- `Apollo_Company_Revenue`
- `Apollo_Company_Industry`
- `Apollo_Company_Founded_Year`
- `Apollo_Company_Funding_Stage`
- `Apollo_Company_Funding_Total`
- `Apollo_Tech_Stack` (type: Multi Line)

### Step 2: Create "Enrich Lead" Button

**Method 1: Using Zoho Workflow (Recommended)**

1. Go to Setup → Automation → Workflows
2. Create New Workflow: Module = Leads, Execute on = Instant
3. Add Instant Action → Function
4. Function Code (Deluge):

```deluge
// Enrich Lead Function
lead_email = lead.get("Email");
lead_id = lead.get("id");

if(isnull(lead_email) || lead_email == "")
{
    return "Error: Lead email is required for enrichment";
}

// Call enrichment API
response = invokeurl
[
    url: "https://your-api-url.com/enrich/lead"
    type: POST
    parameters: {
        "email": lead_email,
        "lead_id": lead_id
    }
    headers: {
        "Content-Type": "application/json",
        "X-Enrich-Secret": "enrich_secret_2025"
    }
];

return "Enrichment queued! Check back in 30-60 seconds. Event ID: " + response.get("event_id");
```

5. Save and name it "Enrich Lead with Apollo"
6. Go to Lead layout, add Custom Button → Link to Workflow
7. Button Label: "🔍 Enrich with Apollo"

**Method 2: Using Zoho Function (Alternative)**

1. Setup → Developer Space → Functions
2. Create New Function: "EnrichLead"
3. Paste function code above
4. Test with sample lead
5. Go to Leads layout → Custom Button → Trigger Function

---

## API Endpoints

### Manual Enrichment Endpoint

**POST** `/enrich/lead`

Request:
```json
{
  "email": "john@acme.com",
  "lead_id": "5123456000001234567"  // Optional Zoho Lead ID
}
```

Headers:
```
Content-Type: application/json
X-Enrich-Secret: enrich_secret_2025
```

Response:
```json
{
  "ok": true,
  "queued": true,
  "event_id": "abc-123-def",
  "message": "Lead enrichment queued for john@acme.com. Check back in 30-60 seconds."
}
```

---

## How It Works

### Data Flow

```
┌──────────────────┐
│ Calendly Webhook │ ────────┐
└──────────────────┘         │
                             ▼
┌──────────────────┐    ┌─────────────┐
│  Zoho Button     │───▶│ RQ Job Queue│
│  (Manual Enrich) │    └─────────────┘
└──────────────────┘         │
                             ▼
                    ┌────────────────────┐
                    │  Enrichment Worker │
                    └────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐     ┌──────────┐
    │ Apollo   │      │ Apollo   │     │ Scraper  │
    │ Person   │      │ Company  │     │ +  LLM   │
    │   API    │      │   API    │     │ Website  │
    └──────────┘      └──────────┘     └──────────┘
           │                 │                 │
           └─────────────────┼─────────────────┘
                             ▼
                    ┌────────────────┐
                    │ Zoho CRM       │
                    │ Update + Note  │
                    └────────────────┘
```

### Enrichment Process

1. **Extract Email** → Get lead email address
2. **Apollo Person Enrichment** → Job title, seniority, department, LinkedIn, phone
3. **Apollo Company Enrichment** → Company size, revenue, industry, funding, tech stack
4. **Website Scraping** → Scrape homepage, about, pricing, careers pages
5. **LLM Analysis** → Extract value prop, target market, pain points, competitors
6. **Zoho Update** → Update lead with all enriched fields
7. **Create Note** → Formatted enrichment summary in Zoho Notes

### Caching Strategy

- **Apollo Data:** Cached in Redis for 30 days (configurable via `APOLLO_CACHE_TTL_DAYS`)
- **Cache Key Pattern:**
  - Person: `apollo:person:{email}`
  - Company: `apollo:company:{domain}`
- **Benefits:** Saves API costs, faster enrichment on re-runs

---

## Example Enrichment Note in Zoho

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 LEAD ENRICHMENT - Dec 18, 2025 2:45 PM UTC

👤 PERSON INTEL (Apollo)
• Job Title: VP of Marketing
• Seniority: VP-level
• Department: Marketing
• LinkedIn: linkedin.com/in/john-smith
• Phone: +1-555-0123

🏢 COMPANY INTEL (Apollo)
• Employees: 150-200
• Revenue: $15M - $25M
• Industry: SaaS - Marketing Technology
• Founded: 2018
• Funding: Series B
  Total Raised: $12.5M
• Tech Stack: Salesforce, HubSpot, AWS, Stripe, Segment, Google Analytics

🌐 WEBSITE INTELLIGENCE (AI Analysis)
• Value Prop: All-in-one social media management for enterprise teams
• Target Market: Mid-market to enterprise B2B companies
• Products/Services: Social scheduling, analytics, collaboration tools
• Pricing Model: Tiered SaaS ($99-$499/mo per seat)
• Recent News: Launched AI-powered analytics feature (Nov 2025)
• Growth Signals: Hiring 5 engineers + 2 sales reps
• Key Pain Points: Managing multiple social accounts, ROI tracking
• Competitors Mentioned: Hootsuite, Sprout Social

🎯 SALES INSIGHTS
1. Focus on enterprise features and team collaboration
2. Emphasize ROI reporting and analytics capabilities
3. Position against Hootsuite/Sprout with unique differentiators

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Enriched by: apollo_person, apollo_company, website
```

---

## Files Created/Modified

### New Files Created:
1. `app/schemas/apollo.py` - Pydantic schemas for Apollo data
2. `app/services/apollo_service.py` - Apollo API client
3. `app/services/scraper_service.py` - Website scraping + LLM analysis
4. `app/jobs/enrich_jobs.py` - Enrichment job logic
5. `app/api/routes_enrich.py` - Manual enrichment endpoint

### Modified Files:
1. `.env` - Added Apollo/Scraper config
2. `app/settings.py` - Added enrichment settings
3. `app/jobs/calendly_jobs.py` - Added auto-enrichment call
4. `app/main.py` - Registered enrichment router
5. `app/util/text_format.py` - Added `extract_domain_from_email()`
6. `requirements.txt` - Added `beautifulsoup4==4.12.3`

---

## Testing

### Test Automatic Enrichment (Calendly)

1. Ensure `ENABLE_AUTO_ENRICH_CALENDLY=true` in `.env`
2. Post a Calendly webhook:
```bash
curl -X POST http://localhost:8000/webhooks/calendly \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/calendly_invitee_created.json
```
3. Check worker logs for enrichment progress
4. Check Zoho Lead for new Apollo fields + enrichment note

### Test Manual Enrichment (API)

```bash
curl -X POST http://localhost:8000/enrich/lead \
  -H 'Content-Type: application/json' \
  -H 'X-Enrich-Secret: enrich_secret_2025' \
  -d '{"email": "test@example.com"}'
```

Expected response:
```json
{
  "ok": true,
  "queued": true,
  "event_id": "abc-123",
  "message": "Lead enrichment queued for test@example.com. Check back in 30-60 seconds."
}
```

---

## Cost Optimization

### Apollo API Costs
- **Person Enrichment:** ~$0.02 per lookup
- **Company Enrichment:** ~$0.03 per lookup
- **Caching:** 30-day TTL saves repeat costs

### ScraperAPI Costs
- **~$0.001 per page** scraped
- Limit: 5 pages max per enrichment (`SCRAPER_MAX_PAGES`)

### Estimated Cost Per Lead
- Apollo Person: $0.02
- Apollo Company: $0.03
- Website (5 pages): $0.005
- **Total: ~$0.055 per lead enrichment**

With caching, re-enrichments within 30 days are free (Apollo only).

---

## Troubleshooting

### Enrichment Not Running

1. Check `ENABLE_AUTO_ENRICH_CALENDLY` is `true`
2. Check `APOLLO_API_KEY` is valid
3. Check worker logs for errors
4. Verify lead email is not personal domain (gmail.com, etc.)

### Apollo Enrichment Failing

1. **401 Unauthorized:** Invalid `APOLLO_API_KEY`
2. **403 Forbidden (Company Enrichment):**
   - API tier doesn't include company enrichment endpoint
   - Person enrichment + website scraping will still work
   - Check logs for: "Apollo company enrichment not available"
   - Solution: Upgrade Apollo tier or continue with person data only
3. **429 Rate Limited:** Too many requests, will auto-retry
4. **Empty Data:** Apollo doesn't have data for this email/domain

### Website Scraping Failing

1. **401 Unauthorized:** Invalid `SCRAPER_API_KEY`
2. **Timeout:** Website too slow, will auto-retry
3. **Empty Data:** Website structure couldn't be parsed

### Manual Endpoint 401 Error

- Check `X-Enrich-Secret` header matches `ENRICH_SECRET_KEY` in `.env`

---

## Next Steps

### Recommended Enhancements

1. **Add Enrichment Dashboard**
   - Track enrichment success rate
   - Monitor Apollo/Scraper API usage
   - Show cost per lead metrics

2. **Smart Re-Enrichment**
   - Auto re-enrich after 90 days
   - Detect when person changes jobs (different company domain in Apollo)

3. **Enrichment Scoring**
   - Assign quality score to enrichment (0-100)
   - Flag incomplete enrichments
   - Alert when high-value lead detected (funding, large company)

4. **Additional Data Sources**
   - Clearbit (alternative to Apollo)
   - Hunter.io (email verification)
   - BuiltWith (tech stack)

---

## Security Notes

- `ENRICH_SECRET_KEY` protects manual enrichment endpoint
- Apollo API key stored in `.env` (never committed to git)
- ScraperAPI key stored in `.env` (never committed to git)
- All API calls use HTTPS
- Redis cache has TTL to prevent stale data

---

## Support

For issues or questions:
1. Check worker logs: `docker compose logs -f worker`
2. Check API logs: `docker compose logs -f api`
3. Review enrichment event: `GET /debug/events/{event_id}`
4. Test Apollo API directly: `https://api.apollo.io/v1/people/match`

---

**Built with:** Apollo.io API + ScraperAPI + Google Gemini LLM
**Last Updated:** December 18, 2025
