# GoVisually Sales Intelligence Integrator

**Automated sales intelligence for Calendly + Read.ai → Zoho CRM**

Receives **Calendly** and **Read.ai** webhooks, enriches leads with **Apollo.io**, **Crawl4AI** website scraping, and **Gemini LLM** analysis, then updates **Zoho CRM** with actionable sales intelligence including company logos.

## ✨ Features

### 🎯 **Calendly Integration**
- Captures demo bookings via webhook
- Extracts 18+ fields from Calendly Q&A using LLM
- Auto-creates/updates Zoho Leads
- Includes: Demo Objectives, Discovery Questions, Sales Rep Cheat Sheet, BANT signals

### 🤖 **Auto-Enrichment**
- **Apollo.io**: Company size, industry, funding, tech stack, job titles
- **Crawl4AI**: FREE multi-page website scraping (homepage + key pages: about, products, pricing, careers, blog)
- **BrandFetch**: Automatic company logo upload to Zoho Lead photo
- **Gemini Grounded Search (2.5-flash)**: Real-time company news with source citations (funding, launches, partnerships, acquisitions)
- **Gemini LLM**: Deep industry-specific intelligence extraction (CPG regulations, SaaS compliance, certifications, product catalogs)

### 📊 **Read.ai Integration**
- Post-demo MEDDIC analysis from meeting transcripts
- Extracts: Metrics, Economic Buyer, Decision Criteria, Pain Points, Champion, Competition

### 🎨 **Sales-Focused Intelligence**
Website enrichment provides conversational, actionable notes:
- "What they do" (not "value proposition")
- "Who they sell to" (not "target market analysis")
- "🎯 HOW TO APPROACH THIS DEMO" with specific tactics

### 💰 **Cost Savings**
- **Before**: ScraperAPI ~$150/month
- **After**: Crawl4AI (free) + ScraperAPI fallback ~$5-15/month
- **Savings**: ~$135/month

## 🚀 Quick Start

### 1. Copy environment file:
```bash
cp .env.example .env
```

### 2. Configure required values in `.env`:
**Minimum for testing:**
- `DRY_RUN=true` (safe mode - no writes to Zoho)
- `GEMINI_API_KEY` (for LLM extraction)

**For production:**
- Zoho OAuth credentials (see `scripts/zoho_oauth_helper.md`)
- `CALENDLY_SIGNING_KEY` (webhook authentication)
- `READAI_SHARED_SECRET` (webhook authentication)
- `APOLLO_API_KEY` (optional - for enrichment)
- `BRAND_FETCH_API` (optional - for company logos)
- `SLACK_WEBHOOK_URL` (optional - for failure alerts)

### 3. Run with Docker Compose:
```bash
docker compose up --build
```

- **API**: http://localhost:8000
- **Health check**: GET http://localhost:8000/healthz
- **Worker**: Background job processor (RQ + Redis)

## 🔗 Webhook Configuration

### Calendly
```
URL: {BASE_URL}/webhooks/calendly
Events: invitee.created, invitee.canceled
Signing Key: Set CALENDLY_SIGNING_KEY in .env
```

### Read.ai
```
URL: {BASE_URL}/webhooks/readai
Event: meeting.completed
Secret: Set READAI_SHARED_SECRET in .env
Header: X-ReadAI-Secret
```

## 📡 API Endpoints

### Webhooks
- `POST /webhooks/calendly` - Calendly webhook receiver
- `POST /webhooks/readai` - Read.ai webhook receiver

### Manual Operations
- `POST /enrich/lead` - Manually enrich a lead by email
- `POST /scrape/website` - Scrape website and get sales intelligence

### Debug (dev only, requires `ALLOW_DEBUG_ENDPOINTS=true`)
- `GET /debug/info` - System info
- `GET /debug/events/{event_id}` - Event details
- `GET /debug/idem/{idempotency_key}` - Idempotency check
- `GET /debug/status` - **Comprehensive system status dashboard** 🆕

### Health
- `GET /healthz` - Health check

## 📊 System Status Dashboard

### `GET /debug/status`
Comprehensive real-time system monitoring endpoint showing everything about your deployment.

**Enable it:**
```bash
# In .env or .env.production
ALLOW_DEBUG_ENDPOINTS=true
```

**⚠️ Security Note:** This endpoint is protected and returns 404 when `ALLOW_DEBUG_ENDPOINTS=false` (default in production). Enable it temporarily when you need to debug, then disable it again.

**Access it:**
```bash
curl http://localhost:8000/debug/status | jq
```

**What it shows:**

**1. Server Health**
- Environment (dev/prod)
- DRY_RUN mode status
- Base URL configuration
- Debug endpoints status

**2. Redis Connection**
- Connection status & ping
- Redis version
- Uptime, memory usage
- Connected clients
- Total commands processed
- Keyspace info

**3. Queue Metrics** ⭐
- **Pending jobs** (waiting to be processed)
- **Started jobs** (currently running)
- **Finished jobs** (completed)
- **Failed jobs** (with error details)
- **Scheduled jobs** (future executions)
- **Active job details** (function name, created_at, started_at)
- **Recent failed jobs** (last 10 with error messages)

**4. Worker Status** ⭐
- Number of workers running
- Worker names and states (idle, busy, suspended)
- Current job being processed by each worker
- Successful/failed job counts per worker
- Worker birth dates (uptime)

**5. Recent Activity**
- Total events stored
- Last 10 events with source, type, status, timestamp

**6. Integration Status**
- Zoho: configured, data center, dry_run
- Apollo: configured
- Gemini: configured, model name
- BrandFetch: configured
- Calendly: configured
- Read.ai: configured
- Website scraping: enabled, Crawl4AI + ScraperAPI status
- Auto-enrichment: enabled

**7. System Metrics**
- CPU usage (%)
- Memory usage (MB & %)
- Number of threads
- API uptime (seconds)

**Example output:**
```json
{
  "timestamp": "2025-12-19T10:30:00.000Z",
  "server": {
    "status": "healthy",
    "environment": "prod",
    "dry_run_mode": false
  },
  "redis": {
    "status": "connected",
    "version": "7.2.0",
    "connected_clients": 3,
    "used_memory_human": "2.5M"
  },
  "queue": {
    "status": "healthy",
    "counts": {
      "pending": 5,
      "started": 1,
      "finished": 127,
      "failed": 2,
      "total": 6
    },
    "active_jobs": [
      {
        "id": "calendly:enrich:1234",
        "func_name": "app.jobs.calendly_jobs.process_calendly_webhook",
        "started_at": "2025-12-19T10:29:45.000Z"
      }
    ]
  },
  "workers": {
    "status": "healthy",
    "count": 1,
    "workers": [
      {
        "name": "worker.1",
        "state": "busy",
        "successful_job_count": 127,
        "failed_job_count": 2
      }
    ]
  },
  "integrations": {
    "zoho": {"configured": true},
    "apollo": {"configured": true},
    "gemini": {"configured": true, "model": "gemini-1.5-pro"}
  },
  "system": {
    "cpu_percent": 12.5,
    "memory_mb": 245.3,
    "uptime_seconds": 86400
  }
}
```

**Use cases:**
- Monitor queue backlog (are jobs piling up?)
- Check if workers are running (is the worker container alive?)
- Debug failed jobs (what's causing failures?)
- Monitor system resources (is memory spiking?)
- Verify integration configuration (is Zoho configured?)
- Track recent activity (what events came in recently?)

## 🧪 Testing

### Test Calendly webhook locally:
```bash
curl -X POST http://localhost:8000/webhooks/calendly \
  -H 'Content-Type: application/json' \
  -d @tests/fixtures/calendly_invitee_created.json
```

### Test website scraping:
```bash
# Using the test script (recommended)
python3 scripts/test_scrape_endpoint.py deputy.com

# Or with curl
curl -X POST http://localhost:8000/scrape/website \
  -H "Content-Type: application/json" \
  -H "X-Enrich-Secret: YOUR_SECRET" \
  -d '{"domain": "deputy.com"}'
```

### Test Read.ai webhook:
```bash
curl -X POST http://localhost:8000/webhooks/readai \
  -H 'Content-Type: application/json' \
  -H 'X-ReadAI-Secret: your-secret' \
  -d @tests/fixtures/readai_meeting_completed.json
```

### Run unit tests:
```bash
pytest -q
```

## 🔧 Development

### Local development with ngrok:
```bash
./scripts/start_ngrok.sh
```

Use the printed HTTPS URL as `BASE_URL` in `.env`, then update webhook settings in Calendly/Read.ai.

### Useful scripts:
- `scripts/test_scrape_endpoint.py` - Test website scraping
- `scripts/calendly_webhook_test.py` - Send test Calendly webhooks
- `scripts/check_zoho_lead.py` - Check Zoho Lead by email
- `scripts/zoho_oauth_helper.md` - Zoho OAuth setup guide

## 🏗️ Architecture

```
Calendly/Read.ai Webhook
    ↓
FastAPI API (validates signature)
    ↓
Store in Redis + Enqueue RQ Job
    ↓
RQ Worker (background processing)
    ↓
┌─────────────────────────────────────┐
│ CALENDLY FLOW:                      │
│ 1. Extract fields with Gemini LLM   │
│ 2. Create/Update Zoho Lead          │
│ 3. Auto-enrich:                     │
│    - Apollo.io (company/person)     │
│    - Crawl4AI website scraping      │
│    - Gemini LLM analysis            │
│    - BrandFetch logo upload         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ READ.AI FLOW:                       │
│ 1. Extract MEDDIC with Gemini LLM   │
│ 2. Update Zoho Lead                 │
│ 3. Add meeting notes                │
└─────────────────────────────────────┘
    ↓
Updated Zoho Lead with:
- 18+ Calendly fields
- Apollo enrichment data
- Website intelligence notes
- Company logo
- MEDDIC analysis
- Meeting transcript
```

## 🔐 Security

### Idempotency
- Incoming webhooks compute an idempotency key
- Calendly: `calendly:{event_type}:{external_id}`
- Read.ai: `readai:meeting_completed:{meeting_id}`
- Duplicate events are ignored (90-day TTL)

### Authentication
- **Calendly**: HMAC signature verification (`CALENDLY_SIGNING_KEY`)
- **Read.ai**: Shared secret header (`READAI_SHARED_SECRET`)
- **Manual endpoints**: API key header (`ENRICH_SECRET_KEY`)

### DRY_RUN Mode
Set `DRY_RUN=true` to test without writing to Zoho. Worker logs what it would send.

## 🌐 Deployment

### Coolify (Recommended)
1. Create new service from GitHub repo
2. Add Redis service
3. Set environment variables from `.env.production`
4. Deploy API + Worker containers
5. Configure webhooks with production URL

### Render / Railway / Other
1. Build from `Dockerfile` (web service for API)
2. Run separate worker: `python -m app.worker`
3. Add Redis instance and set `REDIS_URL`
4. Set all env vars from `.env.example`
5. Use platform URL as `BASE_URL`

## 📊 Zoho CRM Field Mapping

### Calendly Lead Intel (18 fields)
- `First_Name`, `Last_Name`, `Email`, `Company`, `Website`
- `Country`, `State`, `City`, `Phone`, `Industry`
- `Demo_Date`, `Team_members`, `Tools_Currently_Used`
- `Pain_Points`, `Demo_Objectives`, `Demo_Focus_Recommendation`
- `Discovery_Questions`, `Sales_Rep_Cheat_Sheet`

### Apollo Enrichment (10+ fields)
- `Apollo_Job_Title`, `Apollo_Seniority`, `Apollo_Department`
- `Apollo_LinkedIn_URL`, `Apollo_Phone`
- `Apollo_Company_Size`, `Apollo_Company_Industry`
- `Apollo_Company_Founded_Year`, `Apollo_Company_Funding_Stage`
- `Apollo_Company_Funding_Total`, `Apollo_Tech_Stack`

### Read.ai MEDDIC (9 fields)
- `MEDDIC_Metrics`, `MEDDIC_Economic_Buyer`
- `MEDDIC_Decision_Criteria`, `MEDDIC_Decision_Process`
- `MEDDIC_Identified_Pain`, `MEDDIC_Champion`
- `MEDDIC_Competition`, `MEDDIC_Confidence`

### Notes
- Auto-Enrichment note (Apollo + Website intelligence)
- Meeting transcript note
- MEDDIC analysis note

### Photos
- Company logo (uploaded to Lead photo field via BrandFetch)

## 🔍 Website Scraping

### Multi-Page Deep Scraping
- **Crawl4AI (Primary - FREE)**: Playwright-based headless browser
- **Up to 5 pages per domain**: Homepage + discovered key pages (about, products, pricing, careers, blog)
- **Smart page discovery**: Automatically finds relevant sections
- **Returns clean Markdown**: LLM-friendly format
- **Fast**: ~1.5 seconds per page
- **Cost**: $0

### ScraperAPI (Fallback - Paid)
- Only used when Crawl4AI fails (bot detection, etc.)
- Handles tough sites like Stripe
- **Cost**: ~$5-15/month (vs $150 before)

### Deep Intelligence Extraction
Gemini analyzes multi-page content and extracts **17 intelligence fields**:

**Core Intelligence:**
- Value proposition, target market, products/services
- Pricing model, recent news, growth signals
- Pain points, competitors, sales approach tactics

**Deep Industry-Specific Intelligence:**
- **Product catalogs**: CPG products, SaaS features, service offerings
- **Certifications**: ISO 27001, SOC2, HIPAA, FDA approval, USDA Organic, Fair Trade, B-Corp
- **Regulations**: Prop 65, GDPR, EPA, food safety, FDA, OSHA, industry-specific compliance
- **Team size signals**: Office locations, hiring activity, headcount indicators
- **Tech stack**: Technologies, platforms, integrations mentioned
- **Customer segments**: Industries served, customer types (B2B/B2C, SMB/Enterprise)
- **Use cases**: Specific problem scenarios and workflows
- **Content depth**: Blog activity, resources, thought leadership assessment

**Examples:**
- **CPG company** (Annie's): Product list (Mac & Cheese, Snacks), USDA Organic certification, FDA/food safety regulations
- **SaaS company** (Notion): Product features (AI Search, AI Chatbot), pricing ($35/user), Fortune 100 adoption, use cases

All in conversational, sales-focused tone - like a teammate briefing you before a demo call.

## 📰 Grounded News Search

### Gemini Grounded Search (gemini-2.5-flash)
Real-time company news powered by Google Search integration:

**What it finds:**
- Funding rounds and valuations
- Product launches and updates
- Strategic partnerships and acquisitions
- Leadership changes
- Company milestones and achievements
- Industry recognition and awards

**How it works:**
1. LLM automatically generates optimal search queries
2. Searches Google for recent news (last 6 months)
3. Synthesizes findings into conversational summary
4. Returns source citations with URLs

**Example Output:**
> "Hey team, Anthropic has had a busy six months, securing a massive $13 billion Series F funding round in September, which pushed their valuation to $183 billion, and their run-rate revenue has soared to over $5 billion. They've also been on a product spree, launching new Claude models..."
>
> **Sources:**
> 1. Wikipedia - [url]
> 2. TechCrunch - [url]
> 3. Investing.com - [url]

**Pricing:**
- **Free until Jan 5, 2026**
- After: Pay-per-query (charged per search executed)
- Gemini 2.5 models: Billed per prompt
- Typical usage: 1-3 queries per company = minimal cost

**When it runs:**
- Automatically during lead enrichment (Calendly webhook)
- On-demand via `/scrape/website` endpoint
- Populates `recent_news` field with grounded results
- Adds `news_sources` array with citation URLs

## 🐛 Troubleshooting

### Calendly webhooks not working
- **401 error**: Signature mismatch - check `CALENDLY_SIGNING_KEY`
- **No events**: Verify webhook URL in Calendly settings
- **Missing fields**: Check Zoho custom field API names in `.env`

### Zoho errors
- **401**: Invalid refresh token or wrong data center (`ZOHO_DC`)
- **429**: Rate limited - jobs retry with exponential backoff
- **Missing fields**: Run `scripts/check_zoho_lead.py email@example.com`

### LLM extraction issues
- **Schema errors**: Check Gemini API key and quota
- **Truncated responses**: Increase `maxOutputTokens` in `llm_service.py`
- **Repair loops**: Worker runs 2-step validation/repair automatically

### Website scraping fails
- **403 Forbidden**: Site blocks scraping - fallback to ScraperAPI
- **Timeout**: Increase timeout in `scraper_service.py`
- **No content**: Check Crawl4AI logs for browser errors

### Worker not processing
- Check Redis connection: `redis-cli ping`
- Check worker logs: `docker-compose logs -f worker`
- Check queue: `python -m rq info --url redis://localhost:6379/0`

## 📚 Documentation

- `ARCHITECTURE.md` - System architecture and design decisions
- `DEPLOYMENT.md` - Deployment guide for production
- `APOLLO_ENRICHMENT.md` - Apollo.io integration details
- `scripts/zoho_oauth_helper.md` - Zoho OAuth setup guide
- `docs/CALENDLY_WEBHOOK_PAYLOAD.md` - Calendly webhook payload reference

## 🤝 Contributing

This is a private GoVisually internal tool. For changes:
1. Create feature branch
2. Update tests if needed
3. Test locally with `DRY_RUN=true`
4. Deploy to staging first
5. Monitor worker logs for errors

## 📝 License

Proprietary - GoVisually Internal Use Only

## 🆘 Support

For issues or questions:
- Check worker logs in Coolify/Render dashboard
- Review relevant documentation above
- Check GitHub issues (if applicable)
- Contact dev team

---

**Built with:** FastAPI, RQ, Redis, Gemini LLM, Crawl4AI, Apollo.io, BrandFetch, Zoho CRM API
