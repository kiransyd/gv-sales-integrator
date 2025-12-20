# Company Expansion Signals Implementation

**Implementation Date**: 2025-12-20
**Status**: ✅ Complete - Ready for Testing

---

## 📋 What Was Implemented

We've built an automatic expansion signal detection system that monitors Intercom company updates and creates Zoho tasks for sales follow-up.

### System Flow

```
GoVisually Product
    ↓
Updates Intercom Company (e.g., team member added)
    ↓
Intercom fires company.updated webhook
    ↓
Your FastAPI receives webhook
    ↓
Background job analyzes company data
    ↓
Detects expansion signals
    ↓
Creates Zoho Tasks + Sends Slack Alerts
```

---

## 🎯 Signals Detected

### 1. Team at Capacity (CRITICAL 🔥)
- **Trigger**: `gv_no_of_members >= plan_limit`
- **Example**: 25/25 members on PRO plan
- **Action**: URGENT: Offer Enterprise with unlimited users
- **Urgency**: Contact within 48 hours
- **Talking Points**:
  - "Are you blocked from adding teammates?"
  - "Enterprise gives you unlimited users, priority support, SSO"

### 2. Team Approaching Capacity (HIGH 🚀)
- **Trigger**: `gv_no_of_members >= 80% of plan_limit`
- **Example**: 20/25 members (80%)
- **Action**: Proactive Enterprise trial offer
- **Urgency**: 7 days

### 3. Power User - High Project Volume (HIGH 🚀)
- **Trigger**: `gv_total_active_projects >= 100`
- **Action**: Check advanced needs, API access, automation
- **Urgency**: 14 days

### 4. Approaching Project Limit (MEDIUM/HIGH ⚡)
- **Trigger**: `gv_total_active_projects >= 80% of gv_projects_allowed`
- **Action**: Offer plan upgrade with higher limits
- **Urgency**: 7-14 days

### 5. Subscription Expiring Soon (MEDIUM/HIGH ⚡)
- **Trigger**: `gv_subscription_exp_in_sec` within 90 days
- **Action**: Renewal outreach, satisfaction check, upsell
- **Urgency**: 7-14 days

### 6. Subscription Churned (CRITICAL 🔥)
- **Trigger**: `gv_subscription_status in ["canceled", "cancelled", "expired", "unpaid"]`
- **Action**: URGENT: Win-back campaign
- **Urgency**: 24 hours

### 7. Low Feature Adoption (LOW 📌)
- **Trigger**: `gv_total_active_projects >= 10` but `gv_checklists == 0`
- **Action**: Customer success: educate about features
- **Urgency**: 30 days
- **Note**: Does NOT create Zoho task (customer success, not sales)

---

## 📁 Files Created/Modified

### New Files Created ✅

1. **`app/services/expansion_signal_service.py`**
   - Core signal detection logic
   - Plan limits configuration
   - Zoho task formatting

2. **`docs/COMPANY_EXPANSION_SIGNALS_IMPLEMENTATION.md`**
   - This documentation file

### Modified Files ✅

3. **`app/api/routes_webhooks_intercom.py`**
   - Added support for `company.updated` webhook
   - Refactored handlers into separate functions
   - Routes to `process_company_updated` job

4. **`app/jobs/intercom_jobs.py`**
   - Added `_process_company_updated()` function
   - Added `process_company_updated()` entry point
   - Handles signal detection and Zoho task creation

5. **`app/services/intercom_service.py`**
   - Added `get_primary_contact_for_company()` function
   - Searches for user with `user_type=primary`

6. **`app/services/slack_service.py`**
   - Added `notify_expansion_opportunity()` function
   - Priority-based colors and emojis
   - Rich notification with all signal details

---

## ⚙️ Configuration

### Plan Limits (IMPORTANT: Update These!)

The system needs to know plan limits to detect capacity signals. Update these in:

**File**: `app/services/expansion_signal_service.py`
**Location**: Lines 18-35

```python
PLAN_LIMITS = {
    "PRO - Yearly": {
        "members": 25,  # ← UPDATE WITH ACTUAL LIMIT
        "projects": 250,
    },
    "Team Yearly": {
        "members": 10,  # ← UPDATE WITH ACTUAL LIMIT
        "projects": 1000,
    },
    # Add other plans as needed
}
```

**Action Required**:
1. Get actual member limits for each plan from GoVisually
2. Update the `PLAN_LIMITS` dict
3. Add any missing plan names

### Webhook Configuration ✅

Already configured in Intercom:
- ✅ `company.updated` - ON
- ✅ `contact.lead.tag.created` - ON
- ✅ `contact.user.tag.created` - ON
- ✅ Endpoint: `https://your-domain.com/webhooks/intercom`

---

## 🧪 Testing

### Manual Test Process

1. **Trigger a company update** (multiple options):

   **Option A: Update via script** (safest):
   ```bash
   .venv/bin/python scripts/test_company_update_simple.py <company_id>
   # Then revert:
   .venv/bin/python scripts/revert_test_company.py
   ```

   **Option B: Real change in GoVisually**:
   - Add a team member
   - Create a project
   - Update subscription

2. **Check webhook received**:
   ```bash
   # Check API logs
   docker logs gv-sales-integrator-web-1 -f | grep "company.updated"
   ```

   Expected:
   ```
   INFO: Company updated: Bachan's (ID: 66311f0fa8475847eb9a281a)
   INFO: Queued company.updated job: <event_id> for company Bachan's
   ```

3. **Check job processed**:
   ```bash
   # Check worker logs
   docker logs gv-sales-integrator-worker-1 -f | grep "company.updated"
   ```

   Expected:
   ```
   INFO: Processing company.updated: Bachan's (ID: ..., 16 users)
   INFO: Detected X expansion signals for Bachan's
   INFO: Found primary contact for Bachan's: janet@bachans.com
   INFO: Created Zoho task <task_id> for signal: team_approaching_capacity
   INFO: Sent Slack notification for signal: team_approaching_capacity
   ```

4. **Verify Zoho task created**:
   - Go to Zoho CRM → Tasks
   - Look for task with subject like: "🚀 Team Approaching Capacity: Bachan's"
   - Check task is linked to Lead (janet@bachans.com)
   - Verify due date is set correctly

5. **Verify Slack notification** (if priority is high/critical):
   - Check your Slack channel
   - Look for expansion opportunity notification
   - Verify all fields are present

### Test Companies

- **Bachan's** (ID: `66311f0fa8475847eb9a281a`)
  - 16 members on PRO - Yearly
  - 22 active projects
  - Good for testing "approaching capacity" signal

### Expected Signals for Test Companies

**Bachan's** should detect:
- ⚡ Power User (22 projects)
- Possibly approaching capacity if member limit is 25 (16/25 = 64%)

---

## 🐛 Troubleshooting

### Webhook not firing

**Check Intercom Dashboard**:
1. Go to Intercom → Developer Hub → Webhooks
2. Click on your webhook
3. Check "Recent deliveries" tab
4. Look for `company.updated` events
5. Check response code (should be 200)

**Common issues**:
- Webhook URL incorrect
- `company.updated` topic not selected
- Firewall blocking requests

### Job not processing

**Check worker logs**:
```bash
docker logs gv-sales-integrator-worker-1 -f
```

**Common issues**:
- Worker not running: `docker-compose up worker`
- Redis connection issues
- Job failed due to missing function (check imports)

### No signals detected

**Possible reasons**:
1. **Plan limits not configured**: Update `PLAN_LIMITS` in `expansion_signal_service.py`
2. **Company data doesn't match thresholds**: Check actual values
3. **Missing custom attributes**: Company may not have `gv_*` fields

**Debug**:
```bash
# Inspect company data
.venv/bin/python scripts/inspect_intercom_company.py <company_id>
```

### No Zoho task created

**Possible reasons**:
1. **No primary contact found**: Check if company has user with `user_type=primary`
2. **Zoho API error**: Check worker logs for error messages
3. **`create_zoho_task=False`**: Some signals (like low_feature_adoption) don't create tasks

**Debug**:
```python
# In worker logs, look for:
logger.warning("No primary contact found for company: <name>")
logger.error("Failed to create Zoho task for signal <type>: <error>")
```

### No Slack notification

**Possible reasons**:
1. **Priority is low/medium**: Slack only fires for high/critical
2. **Slack webhook URL not configured**: Check `.env` for `SLACK_WEBHOOK_URL`
3. **Slack API error**: Check worker logs

---

## 📊 Example Zoho Task

When a signal is detected, a Zoho task like this is created:

**Subject**: 🔥 Team At Capacity: Bachan's

**Description**:
```
EXPANSION SIGNAL: Team At Capacity

Company: Bachan's
Contact: janet@bachans.com
Intercom Company ID: 66311f0fa8475847eb9a281a

SIGNAL DETAILS:
- 25/25 members - AT LIMIT, cannot add more!

ACTION REQUIRED:
- URGENT: Offer Enterprise/upgrade with unlimited users
- Contact within 2 days

TALKING POINTS:
- I noticed you're at your member limit. Are you blocked from adding teammates?
- Enterprise gives you unlimited users, priority support, SSO, and custom branding.
- Your team is clearly growing - let's make sure GoVisually grows with you.

METRICS:
- team_size: 25
- member_limit: 25

[View in Intercom](https://app.intercom.com/a/apps/wfkef3s2/companies/66311f0fa8475847eb9a281a)
```

**Fields**:
- Due Date: <Today + 2 days>
- Priority: High
- Status: Not Started
- Linked to: Lead (janet@bachans.com)

---

## 🎯 What Happens Next

### Automatic Flow

1. **Team member added in GoVisually**
   - GoVisually updates Intercom: `gv_no_of_members: 16 → 17`

2. **Webhook fires immediately**
   - Intercom sends `company.updated` to your API

3. **Job processes in seconds**
   - Detects signals
   - Creates Zoho task
   - Sends Slack alert

4. **Sales team sees task**
   - Task appears in Zoho with all context
   - Slack notification for urgent items
   - Team contacts customer within SLA

### Manual Oversight

- **Review signals**: Check Zoho tasks daily
- **Update plan limits**: When new plans added
- **Tune thresholds**: Adjust signal detection based on conversion data
- **Monitor false positives**: Remove/adjust noisy signals

---

## 🔄 Future Enhancements

### Phase 2 (Optional)
- [ ] Add more signals (storage usage, API calls, etc.)
- [ ] Score leads based on multiple signals
- [ ] Track signal → conversion rate
- [ ] Build dashboard showing top opportunities
- [ ] Add scheduled job to scan all companies (not just updates)

### Configuration Improvements
- [ ] Move `PLAN_LIMITS` to database or settings
- [ ] Allow customizing signal thresholds via env vars
- [ ] Add signal enable/disable flags

### Reporting
- [ ] Weekly summary of signals detected
- [ ] Track which signals lead to successful upsells
- [ ] Identify underutilized signals

---

## ✅ Summary

### What Works Now

✅ **Automatic detection** of 7 expansion signals
✅ **Real-time processing** via webhooks (seconds delay)
✅ **Zoho task creation** with rich context and talking points
✅ **Slack notifications** for high-priority signals
✅ **Primary contact lookup** to link tasks to right person
✅ **Idempotency** to prevent duplicate processing
✅ **Error handling** with detailed logging

### What's Next

1. **Update plan limits** in `expansion_signal_service.py`
2. **Run test** to verify end-to-end flow
3. **Monitor for 1 week** and tune thresholds
4. **Train sales team** on new automated tasks

---

**Questions or issues?** Check worker logs first, then review this doc's troubleshooting section.

**Ready to test!** 🚀
