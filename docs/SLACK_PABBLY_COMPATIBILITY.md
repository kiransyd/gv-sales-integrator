# Slack + Pabbly Compatibility Guide

When using Pabbly Connect (or other webhook intermediaries) between your app and Slack, the Block Kit format may not render correctly. This guide explains the different format options available.

## The Problem

When sending Slack Block Kit JSON through Pabbly, you might see raw JSON in Slack instead of formatted messages:

```
[{"type":"header","text":{"type":"plain_text","text":"🎯 New Demo Booked"}},...]
```

This happens because Pabbly forwards the JSON payload, but Slack doesn't receive it in the exact format it expects.

## Solution: Format Modes

The app now supports **3 format modes** that you can choose based on your setup:

### 1. **`blocks`** (Default - Direct Slack Webhooks)
- **Use when:** Sending directly to Slack webhook URL
- **Format:** Slack Block Kit JSON
- **Pros:** Rich formatting, modern, best visual appearance
- **Cons:** May not work through intermediaries like Pabbly

### 2. **`attachments`** (Recommended for Pabbly)
- **Use when:** Using Pabbly Connect or other intermediaries
- **Format:** Slack Legacy Attachments JSON
- **Pros:** Works reliably through intermediaries, still formatted nicely
- **Cons:** Slightly less flexible than Block Kit

### 3. **`text`** (Most Compatible)
- **Use when:** Nothing else works, or you want simple messages
- **Format:** Plain text with markdown
- **Pros:** Works everywhere, simple, reliable
- **Cons:** Less visual formatting, no colors/fields

## Configuration

### Option 1: Set in `.env` file (Recommended)

Add this to your `.env` or `.env.production`:

```bash
# For Pabbly Connect (recommended)
SLACK_FORMAT_MODE=attachments

# OR for plain text (most compatible)
SLACK_FORMAT_MODE=text

# OR for direct Slack (default)
SLACK_FORMAT_MODE=blocks
```

### Option 2: Set via Environment Variable

```bash
export SLACK_FORMAT_MODE=attachments
```

## Format Comparison

### Blocks Format (Default)
```json
{
  "text": "Fallback text",
  "blocks": [
    {
      "type": "header",
      "text": {"type": "plain_text", "text": "🎯 New Demo Booked"}
    },
    {
      "type": "section",
      "text": {"type": "mrkdwn", "text": "Message here"}
    }
  ]
}
```

### Attachments Format (Pabbly-Compatible)
```json
{
  "text": "Fallback text",
  "attachments": [
    {
      "color": "good",
      "title": "🎯 New Demo Booked",
      "text": "Message here",
      "fields": [
        {"title": "Email", "value": "test@example.com", "short": true},
        {"title": "Name", "value": "John Doe", "short": true}
      ]
    }
  ]
}
```

### Text Format (Most Compatible)
```json
{
  "text": "*🎯 New Demo Booked*\n\nMessage here\n\n*Email*: test@example.com\n*Name*: John Doe"
}
```

## Pabbly Connect Setup

### Step 1: Configure Format Mode

In your `.env` file:
```bash
SLACK_FORMAT_MODE=attachments
```

### Step 2: Configure Pabbly Webhook Action

1. **HTTP Method:** `POST`
2. **Content-Type Header:** `application/json`
3. **Request Body:** Use the webhook data from your app (Pabbly should pass it through)
4. **URL:** Your Slack webhook URL

### Step 3: Test

Run the test script:
```bash
python3 scripts/test_slack_webhook.py --demo-booked --env .env.production
```

Check your Slack channel - you should see a nicely formatted message instead of raw JSON.

## Troubleshooting

### Still seeing raw JSON?

1. **Check format mode:**
   ```bash
   # Verify it's set correctly
   grep SLACK_FORMAT_MODE .env
   ```

2. **Try attachments mode:**
   ```bash
   SLACK_FORMAT_MODE=attachments
   ```

3. **If attachments don't work, try text mode:**
   ```bash
   SLACK_FORMAT_MODE=text
   ```

### Messages not appearing at all?

1. **Check webhook URL:**
   ```bash
   # Verify webhook URL is set
   grep SLACK_WEBHOOK_URL .env
   ```

2. **Test directly (bypass Pabbly):**
   ```bash
   # Temporarily use direct Slack webhook
   python3 scripts/test_slack_webhook.py --demo-booked \
     --webhook-url https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
   ```

3. **Check Pabbly logs:**
   - Look for errors in Pabbly workflow execution
   - Verify the webhook action is receiving data
   - Check if Pabbly is modifying the payload

### Messages appear but formatting is wrong?

1. **Try a different format mode:**
   - If `blocks` doesn't work → try `attachments`
   - If `attachments` doesn't work → try `text`

2. **Check Pabbly payload transformation:**
   - Pabbly might be modifying the JSON structure
   - Try disabling any JSON transformation in Pabbly
   - Use "Raw" mode if available

## Recommendation

**For Pabbly Connect, use `attachments` mode:**

```bash
SLACK_FORMAT_MODE=attachments
```

This format:
- ✅ Works reliably through intermediaries
- ✅ Still provides nice formatting (colors, fields)
- ✅ Compatible with Slack's legacy attachment API
- ✅ Less likely to be mangled by Pabbly

## Example Output

### With `attachments` mode:
```
🎯 New Demo Booked
─────────────────
John Doe from Acme Corp has booked a demo.

Email: test@example.com
Name: John Doe
Company: Acme Corp
Demo Date: Dec 20, 2024 at 2:00 PM EST
```

### With `text` mode:
```
*🎯 New Demo Booked*

*John Doe* from *Acme Corp* has booked a demo.

*Email*: test@example.com
*Name*: John Doe
*Company*: Acme Corp
*Demo Date*: Dec 20, 2024 at 2:00 PM EST
```

Both will display nicely in Slack, but `attachments` has better visual formatting.

---

**Need help?** Check the main `SLACK_NOTIFICATIONS.md` guide or test with `scripts/test_slack_webhook.py`.


