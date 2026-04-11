# P5-T1 — GitHub OAuth Proxy & Provider

**Phase:** 5 — GitHub Integration and Polish
**Dependencies:** P1-T6 (orchestrator)
**Depends on this:** P5-T2

---

## Objective

Add GitHub as a data source. Unlike Spotify PKCE, GitHub OAuth requires a backend proxy to exchange the code for a token (to keep the client secret off the browser).

## Tasks

1. **Create `backend/app/routes/auth.py`**
   - `GET /api/v1/auth/github/callback?code={code}&state={state}`
   - Exchange the code for an access token by POSTing to `https://github.com/login/oauth/access_token` with `client_id`, `client_secret`, `code`
   - `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` from environment variables
   - Return the access token as JSON: `{"access_token": "ghp_..."}`
   - Validate `state` parameter matches what the frontend sent (CSRF protection)

2. **Create `backend/app/providers/github.py`**
   - Subclass `VibemonProvider`; `source_id = "github"`
   - Activate when `"github"` key is present in `auth_tokens`

3. **Fetch GitHub data**
   - Recent commits (last 30 days): `GET /user/repos` → for each repo, `GET /repos/{owner}/{repo}/commits?since={30_days_ago}&author={username}`
   - Or use the Events API: `GET /users/{username}/events?per_page=100`
   - Repository count: `GET /user/repos?per_page=100`
   - Language breakdown: aggregate `language` field across repos
   - Extract username from `GET /user`

4. **Map to `SourceData`**
   Follow the provider mapping table:
   - Commit count (normalised 0–200) → `hp_factor`
   - Repository count (normalised 1–30) → `sp_attack_factor`
   - Primary language C/Rust/Assembly → `defense_factor` boost
   - Primary language Python/JS/Ruby → `speed_factor` boost
   - PR merge rate → `sp_defense_factor`
   - Issue close rate → `speed_factor` boost
   - Average commit hour 22h–4h → Dark vote (0.5)
   - Average commit hour 6h–10h → Electric vote (0.4)

5. **Set flavour text**
   - Include primary language, commit count, and a coding-themed quip

6. **Register in `PROVIDER_REGISTRY`**

7. **Write tests**
   - Mock GitHub API responses
   - Verify stat factor calculations
   - Test API failure → provider returns empty gracefully
   - Test OAuth callback endpoint with mock code exchange

## Acceptance Criteria

- GitHub OAuth callback exchanges code for token and returns it
- `GitHubProvider.fetch()` returns a populated `SourceData` with coding-derived stats
- Provider failure does not crash the generation pipeline
- `stat_origins` contains GitHub-specific explanations

## Files Created

```
backend/app/routes/auth.py
backend/app/providers/github.py
tests/test_github_provider.py
tests/test_auth_callback.py
```
