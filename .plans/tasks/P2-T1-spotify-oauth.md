# P2-T1 — Spotify PKCE OAuth Flow (Frontend)

**Phase:** 2 — Spotify Integration
**Dependencies:** P1-T7
**Depends on this:** P2-T2

---

## Objective

Implement Spotify's OAuth2 PKCE flow entirely on the frontend. No backend involvement needed — PKCE is safe for SPAs.

## Tasks

1. **Create `frontend/src/lib/auth/spotify.ts`**
   - Generate a random `code_verifier` (64-char random string)
   - Derive `code_challenge` via SHA-256 + base64url
   - Build the Spotify authorization URL:
     ```
     https://accounts.spotify.com/authorize?
       client_id={PUBLIC_SPOTIFY_CLIENT_ID}
       &response_type=code
       &redirect_uri={window.location.origin}/callback/spotify
       &scope=user-read-recently-played user-top-read
       &code_challenge_method=S256
       &code_challenge={challenge}
     ```
   - Store `code_verifier` in `sessionStorage` before redirect

2. **Create callback route**
   - `frontend/src/routes/callback/spotify/+page.svelte`
   - Extract `code` from URL params
   - Exchange for access token: POST to `https://accounts.spotify.com/api/token` with `grant_type=authorization_code`, `code`, `redirect_uri`, `client_id`, `code_verifier`
   - Store the access token in the generation store
   - Redirect back to `/`

3. **Update the landing page**
   - Add a "Connect Spotify" button
   - If a Spotify token exists in state, show a green checkmark and the user's display name
   - Include the token in `auth_tokens.spotify` when posting to `/api/v1/generate`

4. **Handle token expiry**
   - Store `expires_in` alongside the token
   - Before making the generate request, check if the token has expired
   - If expired, prompt re-auth (PKCE tokens from the implicit grant cannot be refreshed without a backend)

5. **Environment variable**
   - `PUBLIC_SPOTIFY_CLIENT_ID` in `.env` (SvelteKit exposes `PUBLIC_` prefixed vars to the browser)

## Acceptance Criteria

- Clicking "Connect Spotify" redirects to Spotify, and after approval, the token is captured and displayed on the landing page
- The token is included in the generate request's `auth_tokens`
- Token state survives page navigation within the SPA session

## Files Created

```
frontend/src/
  lib/auth/spotify.ts
  routes/callback/spotify/+page.svelte
```

## Files Modified

```
frontend/src/routes/+page.svelte
frontend/src/lib/stores/generation.ts
frontend/.env
```
