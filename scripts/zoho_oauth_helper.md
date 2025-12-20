# Zoho OAuth Refresh Token Helper (Server-to-Server)

This service uses Zoho **refresh token flow** to obtain short-lived access tokens.

## What you need
- `ZOHO_CLIENT_ID`
- `ZOHO_CLIENT_SECRET`
- `ZOHO_REFRESH_TOKEN`
- `ZOHO_DC` (`us|au|eu|in`)

## Notes
- The refresh token is long-lived, but treat it like a password.
- If you rotate the refresh token, update it in your Render/production env vars.

## High-level steps (manual)
1. Create a Zoho OAuth client in the correct data center (`ZOHO_DC`).
2. Authorize the client for CRM scopes (e.g. `ZohoCRM.modules.ALL`).
3. Exchange the authorization code for a refresh token.

Because the exact UI steps vary by Zoho region/account setup, the recommended approach is:
- Follow Zoho’s CRM v2 OAuth documentation for your data center
- Confirm the refresh token works by hitting the token endpoint used by this service:
  - `https://accounts.zoho.<domain>/oauth/v2/token`







