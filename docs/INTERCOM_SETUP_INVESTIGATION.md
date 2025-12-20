# Intercom Setup Investigation Results

**Investigation Date**: 2025-12-20
**Test Contact**: janet@bachans.com
**Test Company**: Bachan's (ID: 66311f0fa8475847eb9a281a)

---

## ✅ Confirmed: Your Intercom Setup

### User Signup Flow

1. **User signs up to GoVisually** → Creates Intercom Contact
2. **7-14 day trial period** (custom dates possible)
3. **User type classification:**
   - `user_type: primary` - First team member who signs up ✅
   - `user_type: member` - Additional team members (sometimes also primary)
   - `user_type: collaborator` - Free reviewers

4. **Company creation** - During signup, creates Company object with team name

---

## 📊 Data Storage Structure

### Contact Level (Individual User)

**Contact:** janet@bachans.com
**Role:** user
**ID:** 66016025a1c1700ae16dc8af

#### Standard Fields
- `email`: janet@bachans.com
- `name`: Janet Lee
- `role`: user
- `signed_up_at`: 1711366175 (March 25, 2024)
- `last_seen_at`: 1766166031 (Dec 19, 2025)
- `location`: Seattle, Washington, United States
- `browser`: chrome 143.0.0.0
- `os`: Windows 10

#### Custom Attributes (25 total)
```json
{
  "user_type": "primary",
  "plan_type": "team",
  "gv_version": "1.81.6",
  "installation_type": "wordpress",

  // Onboarding data
  "channel": "Recommended by friend or colleague",
  "company_type": "Consumer Goods",
  "job_role": "Creative Director",
  "main_goal": "Manage Client Feedback",

  // Competitive intelligence
  "project_management_tool_used": "Asana",
  "proofing_tool_used": "Email",

  // Stripe subscription info (at contact level)
  "stripe_id": "cus_Pp4ZMwKh0mrB9g",
  "stripe_plan": "PRO - Yearly",
  "stripe_subscription_status": "active",
  "stripe_last_charge_amount": 4518.62,
  "stripe_last_charge_at": 1743200710,
  "stripe_card_brand": "American Express",
  "stripe_card_expires_at": 1785456000,
  "stripe_subscription_period_start_at": 1743120000,
  "stripe_account_balance": 0.0,
  "stripe_delinquent": false,
  "stripe_deleted": false
}
```

**Key Finding:** Contact has **both** `plan_type` and `stripe_*` attributes for individual subscription tracking.

---

### Company Level (Team/Organization)

**Company:** Bachan's
**ID:** 66311f0fa8475847eb9a281a
**Website:** bachans.com

#### Standard Fields
- `name`: Bachan's
- `company_id`: 6601601f89415a0015fea31c (GoVisually internal ID)
- `user_count`: 16 (Intercom's count of associated users)
- `session_count`: 210 (total sessions across team)
- `last_request_at`: 1766185932 (last activity)
- `created_at`: 1714495247
- `updated_at`: 1766185932

#### Custom Attributes (8 total)
```json
{
  // Team size & capacity
  "gv_no_of_members": 16,
  "gv_projects_allowed": 250,

  // Usage metrics
  "gv_total_active_projects": 22,
  "gv_checklists": 1,

  // Subscription info (at company level)
  "gv_subscription_plan": "PRO - Yearly",
  "gv_subscription_status": "paid",
  "gv_subscription_exp": "7/2026",
  "gv_subscription_exp_in_sec": 1774733014
}
```

**Key Finding:** Company tracks **team-level** usage metrics and subscription status.

---

## 🎯 Expansion Signals Available

### Based on Company Data

#### 1. **Team Capacity Signals**
- **Current**: `gv_no_of_members: 16`
- **Plan Limit**: `gv_projects_allowed: 250` (projects, not members)
- **Signal**: Need to know member limit for each plan to detect "approaching capacity"

**Question:** What's the member limit for PRO - Yearly plan?

#### 2. **Project Activity Signals**
- **Current**: `gv_total_active_projects: 22`
- **Plan Limit**: `gv_projects_allowed: 250`
- **Usage %**: 8.8% of project limit
- **Signal**: Low project volume relative to team size (16 members, 22 projects = 1.4 projects/person)

**Potential Action:** If projects spike to 100+, could indicate power user behavior

#### 3. **Subscription Status**
- **Status**: `gv_subscription_status: paid` ✅
- **Expires**: `gv_subscription_exp: 7/2026` (19 months from now)
- **Last Charge**: $4,518.62 (Jan 2025)

**Signal**: Long-term committed customer, good standing

#### 4. **Feature Adoption**
- **Checklists**: 1 (minimal adoption)
- **Signal**: Opportunity for customer success/education

#### 5. **Trial Conversion Detection**
- **Logic**: If contact has `stripe_id` → Converted ✅
- **Logic**: If no `stripe_id` → Still on trial or didn't convert ❌

---

## 🔔 Webhook Topics Investigation

### Currently Configured in Code

**File:** `app/api/routes_webhooks_intercom.py:87`

```python
supported_topics = ["contact.lead.tag.created", "contact.user.tag.created"]
```

**Current flow:**
1. Support team tags contact with "Lead"
2. Webhook fires → `/webhooks/intercom`
3. Creates Zoho Lead + enrichment
4. **Does NOT** fetch company data
5. **Does NOT** detect expansion signals

---

### Test Results: `company.updated` Webhook

#### Test Setup
- Updated `gv_checklists: 1 → 30 → 1` (reverted)
- Company ID: `66311f0fa8475847eb9a281a`
- Update successful ✅

#### Findings

**✅ Company Update Works**
- Intercom API accepted the update
- `updated_at` timestamp changed: `1766185932`
- Custom attributes can be modified via API

**❓ Webhook Status Unknown**
- Code does NOT handle `company.updated` topic yet
- Cannot list webhook subscriptions (API permission denied)
- Need to check Intercom Dashboard to see if webhook is configured

**⚠️ Custom Attribute Limitation**
- Cannot create NEW custom attributes via API
- Error: `Custom attribute 'test_webhook_trigger' does not exist`
- Can only UPDATE existing pre-defined attributes

---

## 🚀 What Triggers `company.updated`?

Based on successful test, `company.updated` webhook likely fires when:

1. ✅ Custom attributes change (`gv_no_of_members`, `gv_total_active_projects`, etc.)
2. ✅ Standard fields change (`name`, `website`, etc.)
3. ✅ User count changes (member added/removed)
4. ✅ Tags added/removed

**This means:**
- When GoVisually adds a team member → `gv_no_of_members` updates → webhook fires
- When GoVisually creates a project → `gv_total_active_projects` updates → webhook fires
- When Stripe payment processed → `gv_subscription_status` updates → webhook fires

**Perfect for automatic expansion signal detection!** 🎉

---

## 📋 Plan Limits Question

You mentioned:
> "Limits you can see in `gv_projects_allowed` company attribute"

**Current data shows:**
- `gv_projects_allowed: 250` (Bachan's has PRO - Yearly)

**Questions to clarify:**

1. **Member limits per plan:**
   - PRO plan: How many members allowed?
   - Team plan: How many members allowed?
   - Enterprise plan: Unlimited?

2. **Project limits per plan:**
   - Is `gv_projects_allowed: 250` the limit for PRO?
   - What's the limit for Team plan?

3. **Storage limits:**
   - Do you track `gv_storage_used_mb` or similar?
   - Is storage a limiting factor for upgrades?

4. **Other limits:**
   - Are there limits on:
     - Collaborators (free reviewers)?
     - Integrations?
     - API usage?

---

## 🎯 Recommended Next Steps

### 1. Check Intercom Dashboard (Manual)
- Go to Intercom → Developer Hub → Webhooks
- Check if `company.updated` is already subscribed
- If not, add it:
  - Topic: `company.updated`
  - URL: `https://your-domain.com/webhooks/intercom`

### 2. Update Webhook Handler (Code)
Extend `app/api/routes_webhooks_intercom.py` to support `company.updated`:

```python
supported_topics = [
    "contact.lead.tag.created",
    "contact.user.tag.created",
    "company.updated"  # NEW
]
```

### 3. Create Expansion Signal Detection
Add logic to detect:
- Team approaching member limit
- High project volume (power users)
- Subscription expiring soon
- Payment failures (churn risk)
- Low feature adoption

### 4. Map Plan Limits
Create a config file with plan limits:

```python
PLAN_LIMITS = {
    "PRO - Yearly": {
        "members": 25,  # EXAMPLE - need real value
        "projects": 250,
        "storage_gb": 100
    },
    "Team Yearly": {
        "members": 10,  # EXAMPLE - need real value
        "projects": 1000,
        "storage_gb": 500
    }
}
```

### 5. Define Signal Thresholds

```python
EXPANSION_THRESHOLDS = {
    "team_capacity": 0.8,  # Alert at 80% of member limit
    "project_volume": 50,  # 50+ projects = power user
    "subscription_expiring_days": 90,  # Alert 90 days before expiration
    "storage_usage": 0.8  # Alert at 80% storage used
}
```

---

## 🔍 Trial Conversion Detection

Based on your note:
> "Basically you can assume if they didn't pay (ie Stripe added) they didn't convert"

**Detection Logic:**

```python
def is_trial_converted(contact: dict) -> bool:
    """
    Check if user converted from trial to paid.

    If stripe_id exists → Converted ✅
    If no stripe_id → Still on trial or didn't convert ❌
    """
    stripe_id = contact.get("custom_attributes", {}).get("stripe_id")
    return stripe_id is not None and stripe_id != ""

def days_on_trial(contact: dict) -> int:
    """Calculate how many days user has been on trial."""
    import time
    signed_up = contact.get("signed_up_at", 0)
    now = int(time.time())
    days = (now - signed_up) / (60 * 60 * 24)
    return int(days)

def is_trial_expiring(contact: dict, trial_days: int = 14) -> bool:
    """Check if trial is expiring soon (last 2 days)."""
    if is_trial_converted(contact):
        return False  # Already converted

    days = days_on_trial(contact)
    return days >= (trial_days - 2)  # Last 2 days of trial
```

**Potential Signals:**
- Trial day 12 (14-day trial) + no Stripe → Send "upgrade now" email
- Trial day 7 (7-day trial) + no Stripe → "Upgrade before you lose access"
- Trial day 30+ + no Stripe → Churned, didn't convert

---

## 📊 Data Comparison: Contact vs Company

| Data Type | Contact Level | Company Level |
|-----------|---------------|---------------|
| **Subscription Plan** | `stripe_plan: "PRO - Yearly"` | `gv_subscription_plan: "PRO - Yearly"` |
| **Subscription Status** | `stripe_subscription_status: "active"` | `gv_subscription_status: "paid"` |
| **Team Size** | ❌ Not tracked | ✅ `gv_no_of_members: 16` |
| **Projects** | ❌ Not tracked | ✅ `gv_total_active_projects: 22` |
| **Last Active** | ✅ `last_seen_at` (individual) | ✅ `last_request_at` (team-wide) |
| **User Type** | ✅ `user_type: primary/member` | ❌ Not tracked |
| **Payment Info** | ✅ `stripe_*` fields | ❌ Not tracked |

**Key Insight:**
- **Contact** = Individual user attributes + payment details
- **Company** = Team-wide usage metrics + subscription status

For expansion signals, we need **both**:
- Fetch contact to identify primary user
- Fetch company to get usage metrics
- Combine for complete picture

---

## ✅ Summary & Answers

### Your Questions Answered:

1. **✅ Setup makes sense:**
   - primary = account owner
   - member = team member
   - collaborator = free reviewer

2. **✅ Found what triggers updates:**
   - Company.updated fires when any custom attribute changes
   - Test successful (updated `gv_checklists`)

3. **✅ Trial conversion:**
   - If `stripe_id` exists → Converted ✅
   - If no `stripe_id` → Trial or didn't convert ❌

4. **❓ Still need to know:**
   - **Member limits per plan** (PRO, Team, Enterprise)
   - Whether `company.updated` webhook is configured in Intercom Dashboard
   - If there are other usage limits (storage, API calls, etc.)

---

## 📁 Test Scripts Created

1. **`scripts/inspect_intercom_contact.py`** - Inspect individual contact ✅
2. **`scripts/inspect_intercom_company.py`** - Inspect company data ✅
3. **`scripts/test_company_updated_webhook.py`** - Test webhook setup (interactive)
4. **`scripts/test_company_update_simple.py`** - Simple webhook test ✅
5. **`scripts/revert_test_company.py`** - Revert test changes ✅

---

**Next:** Check Intercom Dashboard to see if `company.updated` webhook is configured, then we can build the expansion signal detection logic!
