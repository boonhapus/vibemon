# P5-T2 — GitHub OAuth Frontend & Guest Mode

**Phase:** 5 — GitHub Integration and Polish
**Dependencies:** P5-T1, P1-T7
**Depends on this:** P5-T3

---

## Objective

Add the GitHub connect button to the landing page and implement "Play as Guest" mode for users who skip all authentication.

## Tasks

1. **Create `frontend/src/lib/auth/github.ts`**
   - Build GitHub authorization URL:
     ```
     https://github.com/login/oauth/authorize?
       client_id={GITHUB_CLIENT_ID}
       &redirect_uri={origin}/callback/github
       &scope=read:user repo
       &state={random_state}
     ```
   - Store `state` in `sessionStorage` for CSRF validation

2. **Create callback route**
   - `frontend/src/routes/callback/github/+page.svelte`
   - Extract `code` and `state` from URL params
   - Validate `state` matches stored value
   - Call `GET /api/v1/auth/github/callback?code={code}&state={state}`
   - Store returned access token in generation store
   - Redirect back to `/`

3. **Update the landing page**
   - Add "Connect GitHub" button below Spotify
   - If GitHub token exists, show green checkmark and username
   - Include token in `auth_tokens.github` when generating

4. **Implement "Play as Guest" mode**
   - Add a "Play as Guest" button that skips all auth
   - Posts to `/api/v1/generate` with `auth_tokens: {}` and `user_id: "guest_{random}"`
   - Both player and enemy are weather-only
   - Works with location only (geolocation or city input)

5. **Auth state management**
   - Track which providers are connected in the generation store
   - Show a summary: "Connected: Spotify ✓ GitHub ✓" or "Guest mode"
   - Clear auth state on "Play Again" if desired, or persist for the session

## Acceptance Criteria

- GitHub OAuth flow works end-to-end: click → authorize → token captured → shown on landing page
- "Play as Guest" generates a weather-only Vibemon without any auth
- All three modes (Spotify+GitHub, Spotify-only, Guest) produce valid battles

## Files Created

```
frontend/src/lib/auth/github.ts
frontend/src/routes/callback/github/+page.svelte
```

## Files Modified

```
frontend/src/routes/+page.svelte
frontend/src/lib/stores/generation.ts
```
