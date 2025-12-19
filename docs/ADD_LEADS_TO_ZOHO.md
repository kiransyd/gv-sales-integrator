# Adding GoVisually Signup Leads to Zoho CRM

Hey Umair! 👋 This guide shows you how to send new GoVisually signup leads to our enrichment service, which will automatically create them in Zoho CRM with all the enrichment data (Apollo.io, website intelligence, etc.).
  
## Quick Overview

When a user signs up for GoVisually, you can send their email to our endpoint. The service will:
1. ✅ **Create the lead in Zoho** (if it doesn't exist)
2. 🔍 **Enrich with Apollo.io** (person + company data)
3. 🌐 **Scrape their website** for intelligence
4. 🤖 **Analyze with AI** (Gemini LLM)
5. 🎨 **Upload company logo** (BrandFetch)

All of this happens automatically in the background! 🚀

## The Endpoint

**Production URL:**
```
POST https://salesapi.apps.govisually.co/enrich/lead
```

**Authentication:**
You'll need to include a secret key in the request header:
```
X-Enrich-Secret: enrich_secret_2025
```

## Request Format

### Headers
```javascript
{
  'Content-Type': 'application/json',
  'X-Enrich-Secret': 'enrich_secret_2025'
}
```

### Body
```javascript
{
  "email": "john.doe@example.com"
}
```

That's it! Just the email. The `lead_id` is optional (only if you already have a Zoho lead ID).

## Next.js Examples

### Option 1: Server-Side (API Route) - Recommended ✅

Create a file: `app/api/enrich-lead/route.ts` (or `pages/api/enrich-lead.ts` for Pages Router)

```typescript
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { email } = await request.json();

    if (!email) {
      return NextResponse.json(
        { error: 'Email is required' },
        { status: 400 }
      );
    }

    // Call the enrichment endpoint
    const response = await fetch('https://salesapi.apps.govisually.co/enrich/lead', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Enrich-Secret': 'enrich_secret_2025', // Keep this in env var!
      },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(
        { error: data.detail || 'Failed to enrich lead' },
        { status: response.status }
      );
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Error enriching lead:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
```

Then call it from your signup handler:

```typescript
// In your signup component/handler
async function handleSignup(userData: { email: string; name?: string }) {
  // ... your existing signup logic ...
  
  // After successful signup, enrich the lead
  try {
    const response = await fetch('/api/enrich-lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userData.email }),
    });

    if (response.ok) {
      const result = await response.json();
      console.log('✅ Lead enrichment queued:', result.event_id);
      // Optional: Show success message to user
    } else {
      console.warn('⚠️ Lead enrichment failed (non-critical)');
      // Don't fail signup if enrichment fails - it's non-critical
    }
  } catch (error) {
    console.error('Error calling enrichment:', error);
    // Silently fail - don't block signup
  }
}
```

### Option 2: Client-Side (Not Recommended for Production)

If you must call it from the client, use environment variables:

```typescript
// .env.local (add to .gitignore!)
NEXT_PUBLIC_ENRICH_SECRET=enrich_secret_2025

// In your component
async function enrichLead(email: string) {
  try {
    const response = await fetch('https://salesapi.apps.govisually.co/enrich/lead', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Enrich-Secret': process.env.NEXT_PUBLIC_ENRICH_SECRET!,
      },
      body: JSON.stringify({ email }),
    });

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

**⚠️ Security Note:** Client-side exposes the secret key. Use server-side (Option 1) instead!

### Option 3: Using a Custom Hook

Create `hooks/useEnrichLead.ts`:

```typescript
import { useState } from 'react';

interface EnrichResponse {
  ok: boolean;
  queued: boolean;
  event_id: string;
  message: string;
}

export function useEnrichLead() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const enrichLead = async (email: string): Promise<EnrichResponse | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/enrich-lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to enrich lead');
      }

      const data = await response.json();
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMessage);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { enrichLead, loading, error };
}
```

Use it in your component:

```typescript
import { useEnrichLead } from '@/hooks/useEnrichLead';

function SignupForm() {
  const { enrichLead, loading, error } = useEnrichLead();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = e.target.email.value;

    // Your signup logic here...
    
    // Enrich the lead (non-blocking)
    enrichLead(email).then((result) => {
      if (result) {
        console.log('Lead enrichment queued:', result.event_id);
      }
    });
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Your form fields */}
    </form>
  );
}
```

## Response Format

### Success Response
```json
{
  "ok": true,
  "queued": true,
  "event_id": "abc-123-def-456",
  "message": "Lead enrichment queued for john.doe@example.com. Check back in 30-60 seconds."
}
```

### Error Responses

**401 Unauthorized** (Wrong secret key)
```json
{
  "detail": "Invalid enrichment secret key"
}
```

**400 Bad Request** (Missing email)
```json
{
  "detail": "Email is required"
}
```

## Best Practices

### 1. **Don't Block User Signup** ⚠️
Enrichment is non-critical. If it fails, don't fail the signup:

```typescript
try {
  await enrichLead(email);
} catch (error) {
  // Log but don't throw - signup should still succeed
  console.error('Enrichment failed (non-critical):', error);
}
```

### 2. **Use Environment Variables** 🔐
Store the secret key in environment variables:

```bash
# .env.local
ENRICH_SECRET_KEY=enrich_secret_2025
```

```typescript
// In your API route
const secret = process.env.ENRICH_SECRET_KEY;
```

### 3. **Handle Errors Gracefully** 🛡️
The enrichment service is async and non-blocking. Always handle errors gracefully:

```typescript
const result = await enrichLead(email).catch((error) => {
  // Log for monitoring but don't break user flow
  console.error('Enrichment error:', error);
  return null;
});
```

### 4. **Fire and Forget** 🚀
You don't need to wait for enrichment to complete. The endpoint returns immediately with `queued: true`. The actual enrichment happens in the background (30-60 seconds).

## Integration Points

### Where to Add This

**1. After User Signup**
```typescript
// After successful signup
await signupUser(userData);
await enrichLead(userData.email); // Add here
```

**2. After Email Verification**
```typescript
// After email is verified
await verifyEmail(token);
await enrichLead(user.email); // Add here
```

**3. After Trial Starts**
```typescript
// When user starts free trial
await startTrial(userId);
await enrichLead(user.email); // Add here
```

## Testing

### Test the Endpoint Directly

```bash
curl -X POST https://salesapi.apps.govisually.co/enrich/lead \
  -H "Content-Type: application/json" \
  -H "X-Enrich-Secret: enrich_secret_2025" \
  -d '{"email": "test@example.com"}'
```

### Test in Your App

1. **Development:** Use a test email
2. **Check Zoho:** After 30-60 seconds, search for the lead in Zoho CRM
3. **Verify:** Check that enrichment data is populated

## What Happens After You Send?

1. **Immediate Response** (within 1 second)
   - Returns `queued: true` with an `event_id`
   - Your code can continue immediately

2. **Background Processing** (30-60 seconds)
   - Finds or creates lead in Zoho
   - Enriches with Apollo.io
   - Scrapes company website
   - Analyzes with AI
   - Uploads company logo

3. **Result in Zoho**
   - Lead is created/updated with all enrichment data
   - Enrichment note is added
   - Company logo is uploaded (if available)

## Troubleshooting

### Lead Not Appearing in Zoho?

1. **Check the email format** - Must be valid email
2. **Wait 30-60 seconds** - Processing is async
3. **Check Zoho search** - Search by email address
4. **Check logs** - Look for errors in your API route

### Getting 401 Unauthorized?

- Verify `X-Enrich-Secret` header matches `enrich_secret_2025`
- Check that the header name is exactly `X-Enrich-Secret` (case-sensitive)

### Getting 400 Bad Request?

- Ensure `email` field is present in the request body
- Verify email is a valid string

### Enrichment Not Working?

- Some leads might not have enrichment data (personal emails, small companies)
- This is normal - the lead will still be created in Zoho
- Check the enrichment note in Zoho to see what data was found

## Example: Complete Signup Flow

```typescript
// app/api/signup/route.ts
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { email, name, password } = await request.json();

    // 1. Create user in your database
    const user = await createUser({ email, name, password });

    // 2. Send welcome email
    await sendWelcomeEmail(email);

    // 3. Enrich lead in Zoho (non-blocking)
    fetch('https://salesapi.apps.govisually.co/enrich/lead', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Enrich-Secret': process.env.ENRICH_SECRET_KEY!,
      },
      body: JSON.stringify({ email }),
    }).catch((error) => {
      // Log but don't fail signup
      console.error('Enrichment failed (non-critical):', error);
    });

    // 4. Return success
    return NextResponse.json({ success: true, user });
  } catch (error) {
    return NextResponse.json(
      { error: 'Signup failed' },
      { status: 500 }
    );
  }
}
```

## Need Help?

- **Endpoint Issues:** Check the response status and error message
- **Integration Questions:** Ask the dev team
- **Zoho Issues:** Check if the lead was created (might just be missing enrichment data)

---

**Quick Reference:**
- **Endpoint:** `POST https://salesapi.apps.govisually.co/enrich/lead`
- **Header:** `X-Enrich-Secret: enrich_secret_2025`
- **Body:** `{ "email": "user@example.com" }`
- **Response:** `{ "ok": true, "queued": true, "event_id": "..." }`

Happy coding! 🎉
