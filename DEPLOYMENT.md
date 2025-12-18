# Deployment Guide

## Local Development

Use the dev compose file for hot reload:

```bash
docker compose -f docker-compose.dev.yml up --build
```

## Production Deployment (Coolify)

### 1. Push to GitHub

```bash
git add .
git commit -m "Add Apollo + Website enrichment"
git push origin master
```

### 2. Create New Project in Coolify

1. Go to Coolify dashboard
2. Click "New Project"
3. Select "Docker Compose"
4. Point to your GitHub repository
5. Select branch: `master`

### 3. Configure Coolify

**Compose File:**
- Coolify will automatically detect `docker-compose.yml`
- Make sure it's building all 3 services: `redis`, `api`, `worker`

**Environment Variables:**
- Copy all variables from `.env.production`
- **IMPORTANT:** Update `BASE_URL` to your actual production domain
- Paste into Coolify's "Environment Variables" section

**Port Mapping:**
- Coolify will expose port 8000 from the `api` service
- Map it to your domain (e.g., `your-domain.com` → `api:8000`)

### 4. Deploy

Click "Deploy" in Coolify. It will:
1. Clone your repo
2. Build Docker images
3. Start redis, api, and worker services
4. Expose the API on your domain

### 5. Verify Deployment

```bash
# Check health endpoint
curl https://your-domain.com/health

# Test enrichment
curl -X POST https://your-domain.com/enrich/lead \
  -H 'Content-Type: application/json' \
  -H 'X-Enrich-Secret: enrich_secret_2025' \
  -d '{"email": "test@deputy.com"}'
```

### 6. Update Webhooks

**Calendly:**
- Update webhook URL to: `https://your-domain.com/webhooks/calendly`

**Read.ai (if using):**
- Update webhook URL to: `https://your-domain.com/webhooks/readai`

### 7. Create Zoho Fields on Production

SSH into your Coolify server or use Coolify's terminal:

```bash
# Enter the api container
docker exec -it <container-name> bash

# Run the field creation script
python3 scripts/create_zoho_fields.py
```

## Monitoring

View logs in Coolify:
- API logs: Shows incoming requests and responses
- Worker logs: Shows background job processing and enrichment status

Or via command line:
```bash
docker compose logs -f api
docker compose logs -f worker
```

## Troubleshooting

**Services not starting:**
- Check logs in Coolify
- Verify all environment variables are set
- Ensure Redis is running: `docker compose ps`

**Enrichment not working:**
- Check worker logs for errors
- Verify API keys (Apollo, Gemini, ScraperAPI) are valid
- Test manually: Use curl to trigger enrichment

**Zoho updates failing:**
- Verify Zoho refresh token is valid
- Check Zoho field mappings in `.env`
- Run `scripts/create_zoho_fields.py` to ensure fields exist

## Rollback

In Coolify:
1. Go to Deployments
2. Select previous successful deployment
3. Click "Redeploy"
