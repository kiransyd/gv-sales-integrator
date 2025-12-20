# 🎉 DISCOVERY: GoVisually Usage Data Already in Intercom!

**Investigation Date**: 2025-12-20
**Sample Company**: Calvary Design Team (ID: 6631059bebbd37855746fc2d)
**Finding**: Product usage signals are ALREADY being tracked in Intercom Company objects!

---

## 🔍 What We Found

### ✅ Company-Level Usage Data (Already Tracked!)

Intercom Company `custom_attributes` contains rich GoVisually usage data:

```json
{
  "gv_no_of_members": 10,
  "gv_total_active_projects": 110,
  "gv_projects_allowed": 1000,
  "gv_subscription_plan": "Team Yearly",
  "gv_subscription_status": "paid",
  "gv_subscription_exp": "5/2028",
  "gv_subscription_exp_in_sec": 1782341678,
  "gv_checklists": 0
}
```

**Plus Intercom built-in metrics:**
- `user_count`: 10 (total users in company)
- `session_count`: 120 (total sessions)
- `last_request_at`: 1766166672 (last activity timestamp)

---

## 🎯 Expansion Signals We Can Detect RIGHT NOW

### Signal 1: Team at Maximum Capacity 🔥
**Data**: `gv_no_of_members: 10` + `gv_subscription_plan: "Team Yearly"`
**Threshold**: Team plan = 10 user limit
**Status**: ⚠️ **AT LIMIT** (cannot add more users!)
**Action**: Urgent upsell to Enterprise (unlimited users)
**Priority**: CRITICAL

### Signal 2: Power User - Extremely High Project Volume 🚀
**Data**: `gv_total_active_projects: 110`
**Threshold**: 20+ projects = power user
**Status**: ✅ **DETECTED** (110 is 5.5x threshold!)
**Action**: Check in about advanced needs, API access, automation
**Priority**: HIGH

### Signal 3: Long-Term Committed Customer 💙
**Data**: `gv_subscription_exp: "5/2028"` (3+ years out)
**Status**: ✅ Paying customer, good standing
**Action**: VIP treatment, early access to new features
**Priority**: MEDIUM (retention)

### Signal 4: Paid vs Free Status ✅
**Data**: `gv_subscription_status: "paid"`
**Status**: Paying customer
**Action**: None (good standing)

---

## 🚨 REAL EXPANSION OPPORTUNITY DETECTED

**Company**: Calvary Design Team
**Contact**: lucious.begay@calvaryabq.org

### Current Situation:
- ✅ Team Yearly plan
- ⚠️ **10/10 users (AT CAPACITY)**
- 🚀 **110 active projects** (power user)
- 💰 Paid through 5/2028
- 📊 Last active: Dec 19, 2025 (today!)

### Expansion Signals:
1. **Team Size Limit** (URGENT) - Cannot add more users without upgrading
2. **Power User Behavior** - 110 projects suggests heavy reliance on GoVisually
3. **Recent Activity** - Active today, engaged user

### Recommended Action:
**Create Zoho Task:**
```
Subject: 🔥 URGENT: Calvary Design Team at Capacity (10/10 users)

Priority: High
Due Date: Within 48 hours

Details:
Company: Calvary Design Team (calvaryabq.org)
Contact: Lucious Begay (lucious.begay@calvaryabq.org)
Plan: Team Yearly (expires 5/2028)

EXPANSION SIGNALS:
- ⚠️ AT 10/10 user limit (cannot add more teammates!)
- 🚀 110 active projects (power user)
- 📊 Active today (engaged customer)

ACTION REQUIRED:
Contact within 48 hours to offer Enterprise trial.

TALKING POINTS:
1. "I noticed you're at your 10-user limit. Are you blocked from adding teammates?"
2. "With 110 active projects, you're clearly power users. Enterprise gives you unlimited users, priority support, SSO, and custom branding."
3. "Your team is clearly growing. Let's make sure GoVisually grows with you."

TIMING: Critical - they may be actively trying to add user #11 right now!
```

---

## 📊 All Available Company Signals

### Subscription Data
| Field | Example Value | Use Case |
|-------|--------------|----------|
| `gv_subscription_plan` | "Team Yearly" | Identify plan tier, upsell opportunities |
| `gv_subscription_status` | "paid" | Payment health, churn risk |
| `gv_subscription_exp` | "5/2028" | Renewal timing, contract length |
| `gv_subscription_exp_in_sec` | 1782341678 | Programmatic expiration checks |

### Usage Metrics
| Field | Example Value | Use Case |
|-------|--------------|----------|
| `gv_no_of_members` | 10 | Team size, capacity planning |
| `gv_total_active_projects` | 110 | Product engagement, power user detection |
| `gv_projects_allowed` | 1000 | Plan limits |
| `gv_checklists` | 0 | Feature adoption |

### Intercom Built-in
| Field | Example Value | Use Case |
|-------|--------------|----------|
| `user_count` | 10 | Cross-check with gv_no_of_members |
| `session_count` | 120 | Overall engagement |
| `last_request_at` | 1766166672 | Activity recency, churn risk |

---

## 🔄 How to Access This Data

### Option 1: Webhook + Company Lookup (Recommended)
When you receive an Intercom tag webhook, fetch the associated company:

```python
# app/services/intercom_service.py

def get_company_for_contact(contact_data: dict) -> dict | None:
    """
    Fetch full company data for a contact.

    Contact payload includes company references, but not full data.
    Need to make additional API call.
    """
    companies = contact_data.get("companies", {}).get("data", [])

    if not companies:
        return None

    # Get first company ID
    company_id = companies[0].get("id")
    if not company_id:
        return None

    # Fetch full company data from Intercom API
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.INTERCOM_API_KEY}",
        "Accept": "application/json",
        "Intercom-Version": "2.11"
    }

    response = httpx.get(
        f"https://api.intercom.io/companies/{company_id}",
        headers=headers,
        timeout=30
    )
    response.raise_for_status()

    return response.json()
```

### Option 2: Parse from Contact Payload
The contact webhook includes company references, but NOT full custom attributes. You MUST fetch the company separately to get `gv_*` fields.

---

## 🎯 Updated Signal Detection Logic

```python
# app/services/usage_signal_service.py

def detect_company_expansion_signals(company_data: dict) -> list[dict]:
    """
    Analyze Intercom company for expansion signals.

    Uses actual GoVisually field names (gv_*).
    """
    signals = []

    custom_attrs = company_data.get("custom_attributes", {})

    # Extract GoVisually metrics
    team_size = custom_attrs.get("gv_no_of_members", 0)
    active_projects = custom_attrs.get("gv_total_active_projects", 0)
    plan_name = custom_attrs.get("gv_subscription_plan", "")
    subscription_status = custom_attrs.get("gv_subscription_status", "")
    subscription_exp_sec = custom_attrs.get("gv_subscription_exp_in_sec", 0)

    # SIGNAL 1: Team at capacity
    if "Team" in plan_name and team_size >= 10:
        signals.append({
            "signal": "team_at_capacity",
            "priority": "critical",
            "details": f"{team_size}/10 users - AT CAPACITY, cannot add more!",
            "action": "Urgent: Offer Enterprise with unlimited users",
            "urgency_days": 2,  # Contact within 48 hours
            "zoho_task": True,
            "hot_lead": True,
            "talking_points": [
                "Are you blocked from adding teammates?",
                "Enterprise gives unlimited users, priority support, SSO",
                "Your team is growing - let's make sure GoVisually grows with you"
            ]
        })

    # SIGNAL 2: Approaching team limit
    elif "Team" in plan_name and team_size >= 8:
        signals.append({
            "signal": "team_approaching_capacity",
            "priority": "high",
            "details": f"{team_size}/10 users - approaching limit",
            "action": "Proactive: Offer Enterprise trial before they hit limit",
            "urgency_days": 7,
            "zoho_task": True
        })

    # SIGNAL 3: Power user (high project volume)
    if active_projects >= 50:
        intensity = "extreme" if active_projects >= 100 else "high"
        signals.append({
            "signal": "power_user_projects",
            "priority": "high" if intensity == "extreme" else "medium",
            "details": f"{active_projects} active projects ({intensity} usage)",
            "action": "Check in about advanced needs, API access, automation",
            "urgency_days": 14,
            "zoho_task": True
        })

    # SIGNAL 4: Subscription expiring soon
    import time
    days_until_exp = (subscription_exp_sec - time.time()) / (60 * 60 * 24)
    if 0 < days_until_exp <= 90:  # Within 90 days
        signals.append({
            "signal": "subscription_expiring",
            "priority": "high" if days_until_exp <= 30 else "medium",
            "details": f"Subscription expires in {int(days_until_exp)} days",
            "action": "Renewal outreach, check satisfaction, upsell opportunity",
            "urgency_days": 7 if days_until_exp <= 30 else 14,
            "zoho_task": True
        })

    # SIGNAL 5: Churned/canceled
    if subscription_status in ["canceled", "cancelled", "expired"]:
        signals.append({
            "signal": "subscription_churned",
            "priority": "urgent",
            "details": f"Subscription status: {subscription_status}",
            "action": "Win-back campaign, understand why they left",
            "urgency_days": 1,
            "zoho_task": True,
            "churn_prevention": True
        })

    # SIGNAL 6: Low feature adoption
    checklists_used = custom_attrs.get("gv_checklists", 0)
    if active_projects >= 10 and checklists_used == 0:
        signals.append({
            "signal": "low_feature_adoption",
            "priority": "low",
            "details": f"{active_projects} projects but 0 checklists used",
            "action": "Education: Show them checklist feature, customer success outreach",
            "urgency_days": 30,
            "zoho_task": False  # Customer success, not sales
        })

    return signals
```

---

## 🔄 Updated Intercom Job Flow

```python
# app/jobs/intercom_jobs.py

def _process_contact_tagged(ctx: JobContext) -> None:
    """
    Process Intercom contact tag webhook.

    UPDATED: Also fetch and analyze company data for expansion signals.
    """
    # ... existing contact parsing code ...

    info = parse_intercom_contact_info(ev.payload)

    # NEW: Fetch company data
    company_data = get_company_for_contact(ev.payload)

    if company_data:
        logger.info(f"Fetched company data: {company_data.get('name')}")

        # Detect expansion signals from company usage data
        signals = detect_company_expansion_signals(company_data)

        if signals:
            logger.info(f"Detected {len(signals)} expansion signals for {company_data.get('name')}")

            # Process each signal
            for signal in signals:
                if signal.get("zoho_task"):
                    # Create Zoho task for sales team
                    create_expansion_task(
                        lead_id=lead_id,
                        signal=signal,
                        company_name=company_data.get("name"),
                        contact_email=info.email
                    )

                    # Send Slack alert for high-priority signals
                    if signal.get("priority") in ["critical", "urgent", "high"]:
                        notify_expansion_signal(
                            email=info.email,
                            company=company_data.get("name"),
                            signal=signal
                        )

    # ... rest of existing code ...
```

---

## 🚀 Implementation Steps

### Phase 1: Quick Win (This Week) ✅ Ready to implement!

1. **Extend Intercom webhook handler** (2 hours)
   - Add `get_company_for_contact()` function
   - Fetch company data when processing tag webhooks
   - Log company usage metrics

2. **Add signal detection logic** (2 hours)
   - Implement `detect_company_expansion_signals()`
   - Map GoVisually field names (`gv_*`)
   - Define thresholds for each signal

3. **Create Zoho tasks** (2 hours)
   - Generate task title/description from signal data
   - Include talking points and urgency
   - Set priority and due date

4. **Slack notifications** (1 hour)
   - Alert for critical/urgent signals
   - Include company name, signal type, recommended action

5. **Test with real data** (1 hour)
   - Tag a contact in Intercom
   - Verify company data fetched correctly
   - Check Zoho task created
   - Confirm Slack notification

**Total Effort**: ~8 hours (1 day)

### Phase 2: Scheduled Scanning (Next Week)

1. **Create scheduled job**
   - Scan all companies every 6 hours
   - Detect signals for companies without recent tags
   - Auto-tag companies with signals

2. **Build dashboard**
   - Show top expansion opportunities
   - Track signal detection accuracy
   - Monitor conversion rates

---

## 💎 The Gold Mine: What This Unlocks

### Immediate Value:
1. **Calvary Design Team** - AT CAPACITY (10/10 users), 110 projects → Immediate Enterprise upsell
2. **All "Team" plan companies at 8-10 users** → Proactive expansion outreach
3. **Companies with 50+ projects** → Power user engagement
4. **Subscriptions expiring in <90 days** → Renewal conversations

### Long-Term Value:
1. **Predictive analytics** - Which usage patterns lead to upgrades?
2. **Churn prevention** - Spot declining usage before cancellation
3. **Product insights** - Which features drive retention?
4. **Customer segmentation** - Target messaging by usage tier

---

## 📋 Next Actions

**Immediate (Do Now)**:
1. ✅ Tag Lucious Begay with "Expansion: Team at Capacity" in Intercom
2. ✅ See if webhook fires and company data is accessible
3. ✅ Manually create Zoho task for Calvary Design Team

**This Week**:
1. Implement company data fetching in webhook handler
2. Add expansion signal detection logic
3. Create Zoho task automation
4. Deploy and test with real webhooks

**Next Week**:
1. Build scheduled scanning job
2. Analyze all companies for expansion signals
3. Generate list of top 20 upsell opportunities

---

**Last Updated**: 2025-12-20

**Key Insight**: We don't need GoVisually to change anything! The data is already flowing into Intercom. We just need to read it and act on it. 🎉
