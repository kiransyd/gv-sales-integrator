# Intercom Product Usage Signal Analysis

**Investigation Date**: 2025-12-20
**Sample Contact**: lucious.begay@calvaryabq.org
**Purpose**: Determine what product usage data is available in Intercom for sales automation

---

## 📊 Current State: What We Have

### ✅ Data Currently Tracked in Intercom

**Custom Attributes** (stored in `custom_attributes`):
- `gv_version`: "1.81.6" - GoVisually version user is on
- `plan_type`: "team" - Subscription plan tier
- `user_type`: "primary" - User role (primary vs guest)

**Engagement Metrics** (Intercom built-in):
- `signed_up_at`: 1723738978 (Aug 15, 2024)
- `last_seen_at`: 1766165364 (Dec 19, 2025)
- `last_contacted_at`: Support team last reached out
- `last_email_opened_at`: User last opened an email
- `browser`: "safari"
- `browser_version`: "26.1"
- `os`: "OS X 10.15.7"

**Location Data**:
- City: Albuquerque
- Region: New Mexico
- Country: United States

**Good News**: Intercom's built-in tracking already captures valuable engagement signals.

---

## ❌ Critical Missing Data: Usage Signals We Need

To enable **Product Usage Signal → Proactive Outreach** automation, GoVisually needs to track these additional data points in Intercom:

### 1. **Project Activity** (Expansion Signals)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `projects_count` | Integer | Total projects created | `23` |
| `projects_last_30_days` | Integer | Recent activity level | `5` |
| `last_project_created` | ISO 8601 | Recency indicator | `2025-12-15T10:30:00Z` |
| `active_projects` | Integer | Current workload | `8` |

**Use Case**: If `projects_last_30_days >= 10` → Power user signal

### 2. **Team Growth** (Expansion Signals)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `teammates_count` | Integer | Current team size | `9` |
| `teammates_invited_last_30_days` | Integer | Growth velocity | `3` |
| `last_teammate_invited` | ISO 8601 | Team expansion timing | `2025-12-10T14:20:00Z` |

**Use Case**: If `plan_type == "team"` AND `teammates_count >= 8` → Approaching seat limit

### 3. **Storage Usage** (Upgrade Triggers)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `storage_used_mb` | Integer | Current usage | `850` |
| `storage_limit_mb` | Integer | Plan limit | `1024` |
| `storage_percent` | Integer | Calculated % | `83` |

**Use Case**: If `storage_percent >= 80` → Upsell more storage

### 4. **Feature Adoption** (Enterprise Intent)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `enterprise_features_tried` | JSON Array | Features user accessed | `["sso_attempted", "custom_branding"]` |
| `integrations_enabled` | JSON Array | Connected tools | `["slack", "asana"]` |
| `api_usage_last_30_days` | Integer | API calls made | `1250` |

**Use Case**: If `"sso_attempted" in enterprise_features_tried` → Hot lead for Enterprise

### 5. **Workspace Management** (Multi-Department Usage)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `workspaces_count` | Integer | Number of workspaces | `3` |
| `departments_using` | JSON Array | Cross-team adoption | `["Marketing", "Design", "Product"]` |

**Use Case**: If `workspaces_count >= 2` → Enterprise with multi-workspace feature

### 6. **Inactivity Tracking** (Churn Risk)
| Attribute | Type | Purpose | Example Value |
|-----------|------|---------|---------------|
| `days_since_last_login` | Integer | Calculated daily | `14` |
| `days_since_last_project` | Integer | Product engagement | `7` |
| `login_frequency_30_days` | Integer | Engagement level | `18` |

**Use Case**: If `days_since_last_login >= 14` → Churn risk alert

---

## 🚀 Implementation Options

### Option A: GoVisually → Intercom (Recommended)

**How it works:**
1. GoVisually tracks events locally (already happening)
2. Send updates to Intercom via JavaScript SDK or API
3. Intercom stores as contact attributes
4. Your API receives webhooks when attributes change

**Advantages:**
- ✅ Support team sees usage data during conversations
- ✅ Single source of truth for customer data
- ✅ No polling needed (webhook-driven)
- ✅ Intercom's powerful segmentation tools

**Implementation in GoVisually:**

```javascript
// In GoVisually frontend/backend

// When user creates a project
function onProjectCreated(project) {
  // Track event
  Intercom('trackEvent', 'project_created', {
    project_id: project.id,
    project_name: project.name,
    collaborators: project.team.length
  });

  // Update running count
  const user = getCurrentUser();
  Intercom('update', {
    projects_count: user.totalProjects,
    projects_last_30_days: user.recentProjects.length,
    last_project_created: new Date().toISOString(),
    active_projects: user.activeProjects.length
  });
}

// When user invites teammate
function onTeammateInvited(email) {
  const user = getCurrentUser();

  Intercom('trackEvent', 'teammate_invited', {
    invited_email: email,
    total_teammates: user.team.length
  });

  Intercom('update', {
    teammates_count: user.team.length,
    last_teammate_invited: new Date().toISOString()
  });
}

// Periodic storage check (run every hour or on key actions)
function updateStorageUsage() {
  const user = getCurrentUser();
  const storageUsed = user.storage.usedMB;
  const storageLimit = user.storage.limitMB;
  const storagePercent = Math.round((storageUsed / storageLimit) * 100);

  Intercom('update', {
    storage_used_mb: storageUsed,
    storage_limit_mb: storageLimit,
    storage_percent: storagePercent
  });

  // If threshold crossed, fire event too
  if (storagePercent >= 80 && !user.storage.alertSent80) {
    Intercom('trackEvent', 'storage_threshold_reached', {
      threshold: 80,
      storage_used_mb: storageUsed
    });
  }
}

// When user tries enterprise feature
function onEnterpriseFeatureAccessed(featureName) {
  const user = getCurrentUser();
  const enterpriseTried = user.enterpriseFeaturesTriedList || [];

  if (!enterpriseTried.includes(featureName)) {
    enterpriseTried.push(featureName);
  }

  Intercom('trackEvent', 'enterprise_feature_accessed', {
    feature: featureName,
    plan_type: user.planType
  });

  Intercom('update', {
    enterprise_features_tried: enterpriseTried
  });
}

// Daily background job to update activity metrics
function updateActivityMetrics() {
  const user = getCurrentUser();
  const lastLogin = user.lastLoginDate;
  const lastProject = user.lastProjectDate;
  const loginCount30Days = user.loginsLast30Days;

  const daysSinceLogin = Math.floor((Date.now() - lastLogin) / (1000 * 60 * 60 * 24));
  const daysSinceProject = Math.floor((Date.now() - lastProject) / (1000 * 60 * 60 * 24));

  Intercom('update', {
    days_since_last_login: daysSinceLogin,
    days_since_last_project: daysSinceProject,
    login_frequency_30_days: loginCount30Days,
    last_active_date: new Date().toISOString()
  });
}
```

**Server-side alternative (using Intercom REST API):**

```python
# In GoVisually backend (Python/Node/etc.)

import httpx

INTERCOM_API_KEY = "your_key"

def update_intercom_contact(user_id: str, attributes: dict):
    """Update Intercom contact attributes."""
    headers = {
        "Authorization": f"Bearer {INTERCOM_API_KEY}",
        "Content-Type": "application/json",
        "Intercom-Version": "2.11"
    }

    payload = {
        "external_id": user_id,  # GoVisually user ID
        "custom_attributes": attributes
    }

    response = httpx.post(
        "https://api.intercom.io/contacts",
        headers=headers,
        json=payload
    )
    response.raise_for_status()

# Usage
update_intercom_contact(
    user_id="66be2b62c2b347001527e1ee",
    attributes={
        "projects_count": 23,
        "teammates_count": 9,
        "storage_percent": 83
    }
)
```

---

### Option B: Direct to Your API (Bypass Intercom)

**How it works:**
1. GoVisually sends events directly to your FastAPI
2. Your app stores and analyzes usage patterns
3. Your app updates Intercom (so support team can see)
4. Your app creates Zoho tasks

**Advantages:**
- ✅ Full control over data and logic
- ✅ Complex pattern detection possible
- ✅ No Intercom event/attribute limits

**Disadvantages:**
- ❌ Data in two places (your DB + Intercom)
- ❌ Support team doesn't see real-time usage
- ❌ More infrastructure to maintain

---

## 🎯 Recommended Approach

**Phase 1: Quick Win (This Week)**
- Add 5 key attributes to Intercom:
  - `projects_count`
  - `teammates_count`
  - `storage_percent`
  - `days_since_last_login`
  - `enterprise_features_tried` (JSON array)

**Phase 2: Event Tracking (Next 2 Weeks)**
- Configure Intercom webhooks for `contact.attribute.updated`
- Build expansion signal detection in your API
- Auto-create Zoho tasks when signals detected

**Phase 3: Advanced Patterns (Month 2)**
- Track events: `project_created`, `teammate_invited`, etc.
- Build churn risk scoring
- Predictive analytics for expansion likelihood

---

## 🔔 Intercom Webhook Configuration

To receive updates when usage data changes, configure these webhook topics in Intercom:

### Webhook Topics to Enable

1. **`contact.attribute.updated`** (Not available - see note below)
2. **`contact.user.tag.created`** (Already enabled ✅)
3. **`contact.lead.tag.created`** (Already enabled ✅)

**Important Note**: Intercom does NOT have a `contact.attribute.updated` webhook topic. Instead, you have two options:

### Workaround A: Tag-Based Triggers (Recommended)
When GoVisually updates Intercom attributes, also auto-tag the contact based on thresholds:

```javascript
// In GoVisually
function updateUsageAndCheckSignals(user) {
  // Update attributes
  Intercom('update', {
    teammates_count: user.team.length,
    storage_percent: user.storagePercent
  });

  // Auto-tag if expansion signal detected
  if (user.team.length >= 8 && user.planType === 'team') {
    Intercom('update', {
      tags: [{ name: 'Expansion: Team Size Limit', add: true }]
    });
    // This will trigger your existing contact.user.tag.created webhook!
  }

  if (user.storagePercent >= 80) {
    Intercom('update', {
      tags: [{ name: 'Expansion: Storage Limit', add: true }]
    });
  }
}
```

**How it works:**
1. GoVisually checks for expansion signals locally
2. If detected → auto-add tag to Intercom contact
3. Tag creation fires `contact.user.tag.created` webhook
4. Your existing webhook handler processes it

**Tags to auto-apply:**
- `Expansion: Team Size Limit` - 8+ users on team plan
- `Expansion: Storage Limit` - 80%+ storage used
- `Expansion: Power User` - 20+ projects created
- `Expansion: Enterprise Feature Interest` - Tried SSO/etc
- `Churn Risk: Inactive 14 Days` - No login in 2 weeks

### Workaround B: Polling (Fallback)
Create a scheduled job that polls Intercom Search API every 6 hours:

```python
# In your app (app/jobs/scheduled_jobs.py)

def scan_intercom_for_usage_signals():
    """
    Scheduled job: Check Intercom contacts for expansion signals.
    Runs every 6 hours.
    """
    from app.services.intercom_client import search_contacts

    # Find team plan users with 8+ teammates
    contacts = search_contacts({
        "plan_type": "team",
        "teammates_count": {"gte": 8}
    })

    for contact in contacts:
        # Check if already tagged
        tags = [t["name"] for t in contact.get("tags", {}).get("data", [])]
        if "Expansion: Team Size Limit" not in tags:
            # Auto-tag (will trigger webhook)
            add_intercom_tag(contact["id"], "Expansion: Team Size Limit")
```

---

## 📈 Expansion Signal Detection Logic

Once data is in Intercom, here's how your API will detect signals:

```python
# app/services/usage_signal_service.py

def detect_expansion_signals(contact_data: dict) -> list[dict]:
    """
    Analyze Intercom contact for expansion signals.

    Returns list of signals with recommended actions.
    """
    signals = []

    plan_type = contact_data.get("custom_attributes", {}).get("plan_type")
    teammates = contact_data.get("custom_attributes", {}).get("teammates_count", 0)
    projects = contact_data.get("custom_attributes", {}).get("projects_count", 0)
    storage_pct = contact_data.get("custom_attributes", {}).get("storage_percent", 0)
    enterprise_tries = contact_data.get("custom_attributes", {}).get("enterprise_features_tried", [])
    days_inactive = contact_data.get("custom_attributes", {}).get("days_since_last_login", 0)

    # SIGNAL 1: Team size approaching limit
    if plan_type == "team" and teammates >= 8:
        signals.append({
            "signal": "team_size_limit",
            "priority": "high",
            "details": f"{teammates}/10 users (approaching limit)",
            "action": "Offer Enterprise trial with unlimited seats",
            "urgency_days": 7,  # Contact within 7 days
            "zoho_task": True
        })

    # SIGNAL 2: Storage threshold
    if storage_pct >= 80:
        urgency = "urgent" if storage_pct >= 95 else "high"
        signals.append({
            "signal": "storage_limit",
            "priority": urgency,
            "details": f"{storage_pct}% storage used",
            "action": "Upsell additional storage or Enterprise",
            "urgency_days": 3 if storage_pct >= 95 else 7,
            "zoho_task": True
        })

    # SIGNAL 3: Power user behavior
    if projects >= 20:
        signals.append({
            "signal": "power_user",
            "priority": "medium",
            "details": f"{projects} projects created",
            "action": "Check in about advanced needs, API access",
            "urgency_days": 14,
            "zoho_task": True
        })

    # SIGNAL 4: Enterprise feature interest
    if enterprise_tries:
        signals.append({
            "signal": "enterprise_feature_interest",
            "priority": "high",
            "details": f"Tried: {', '.join(enterprise_tries)}",
            "action": "Sales call to discuss Enterprise features",
            "urgency_days": 3,
            "zoho_task": True,
            "hot_lead": True
        })

    # SIGNAL 5: Churn risk
    if days_inactive >= 14:
        signals.append({
            "signal": "churn_risk_inactivity",
            "priority": "urgent",
            "details": f"Inactive for {days_inactive} days",
            "action": "Reach out to re-engage, offer help",
            "urgency_days": 1,
            "zoho_task": True,
            "churn_prevention": True
        })

    return signals
```

---

## 🔄 Complete Flow Example

**Scenario**: Team plan user invites 8th teammate

1. **GoVisually Product**:
   ```javascript
   // User invites teammate #8
   onTeammateInvited("newperson@company.com");

   // Updates Intercom
   Intercom('update', {
     teammates_count: 8
   });

   // Auto-tags contact
   Intercom('update', {
     tags: [{ name: 'Expansion: Team Size Limit', add: true }]
   });
   ```

2. **Intercom**:
   - Stores `teammates_count: 8`
   - Adds tag "Expansion: Team Size Limit"
   - Fires webhook: `contact.user.tag.created`

3. **Your FastAPI** (`POST /webhooks/intercom`):
   - Receives webhook
   - Parses contact data
   - Detects `teammates_count: 8` on team plan
   - Enqueues background job

4. **RQ Worker** (`app/jobs/usage_signal_jobs.py`):
   ```python
   def process_expansion_signal(contact_email, signals):
       # Create/update Zoho lead
       lead_id = upsert_lead_by_email(contact_email, {
           "Lead_Status": "Expansion Opportunity"
       })

       # Create Zoho task
       create_zoho_task(
           lead_id=lead_id,
           subject="🚀 Upsell Opportunity: Team at capacity (8/10 users)",
           due_date=date.today() + timedelta(days=7),
           priority="High",
           description="""
           EXPANSION SIGNAL: Team Size Limit

           Current: 8 users (80% of team plan limit)
           Plan: Team
           Company: [Company Name]

           ACTION REQUIRED:
           - Reach out within 7 days
           - Offer Enterprise trial (unlimited seats)
           - Highlight: SSO, priority support, custom branding
           - Timing critical: Before they hit hard 10-user limit

           [Link to Intercom conversation]
           """
       )

       # Slack alert
       notify_expansion_opportunity(
           email=contact_email,
           signal="Team Size Limit (8/10 users)",
           urgency="high",
           action="Contact within 7 days with Enterprise offer",
           lead_id=lead_id
       )
   ```

5. **Sales Rep**:
   - Gets Slack notification
   - Sees Zoho task with full context
   - Calls customer: "Hey, noticed you're growing fast! Let's talk about Enterprise..."

---

## 💾 Summary: What GoVisually Needs to Track

### Priority 1: Critical (This Week)
- ✅ `plan_type` (already tracked)
- ⚠️ `teammates_count`
- ⚠️ `storage_percent`
- ⚠️ `projects_count`

### Priority 2: Important (Next 2 Weeks)
- `enterprise_features_tried` (JSON array)
- `days_since_last_login`
- `last_project_created`

### Priority 3: Nice to Have (Month 2)
- `projects_last_30_days`
- `integrations_enabled`
- `workspaces_count`
- `api_usage_last_30_days`

---

## 🎯 Next Steps

1. **GoVisually Team**: Implement Intercom attribute updates
   - Start with top 5 attributes
   - Use JavaScript SDK or REST API
   - Test with staging environment first

2. **Your API**: Build webhook handler for tag-based triggers
   - Extend existing `/webhooks/intercom` endpoint
   - Add signal detection logic
   - Connect to Zoho task creation

3. **Testing**: Use real user data to validate
   - Monitor webhooks in Intercom dashboard
   - Check Zoho tasks created correctly
   - Verify Slack notifications work

4. **Iteration**: Tune thresholds based on data
   - Maybe 9 users is better trigger than 8?
   - Adjust based on actual conversion rates
   - Add new signals as patterns emerge

---

**Last Updated**: 2025-12-20
