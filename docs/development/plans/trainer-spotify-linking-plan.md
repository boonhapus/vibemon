# Trainer ↔ Spotify Linking Plan (Stub)

## Goal

Establish the OAuth Authorization Code flow that lets a **Trainer** link their Spotify account to their Vibemon profile, persisting a refresh token used by `SoundProvider` to fetch listening data on their behalf.

## Why this is its own plan

`SoundProvider` (see `sound-provider-plan.md`) requires `trainer.spotify_refresh_token` to exist. The OAuth flow, token storage, refresh logic, and revocation handling are a self-contained slice with its own surface area (HTTP route, DB migration, secret handling, frontend/CLI link action). Bundling it into the provider plan would muddy review and rollout.

## Scope

- In scope:
  - `GET /spotify/authorize` — generates Spotify authorize URL with scopes, returns redirect.
  - `GET /spotify/callback?code=...&state=...` — exchanges code for `(access_token, refresh_token)`, persists refresh token against the trainer.
  - DB migration adding `trainer.spotify_refresh_token: SecretStr | None` column.
  - Token storage helper (encrypted-at-rest if/when the app gains a secret backend; SecretStr-only for now).
  - Token-refresh helper consumed by `SpotifyAPIClient._ensure_token()`.
  - State parameter for CSRF protection.
  - Revocation endpoint: `POST /spotify/unlink` clears the refresh token from the trainer record.
  - Scopes requested: `user-top-read`, `user-read-recently-played`. **No write scopes.**
  - Settings: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`.
  - Tests: callback happy path, state mismatch rejection, expired-code handling, token refresh flow.

- Out of scope:
  - `SoundProvider` itself.
  - Provider-picker UX (the surface where a trainer opts sound into a birth).
  - Production callback host (localhost for v1; revisit at deployment).
  - Trainer-facing UI for the link action (a CLI command in the script-frontend era is fine).
  - Multi-account linking (one Spotify account per trainer in v1).

## Locked Decisions (proposed — open for review)

1. Refresh tokens stored as `SecretStr` on the `Trainer` model. No bespoke encryption in v1; relies on DB access controls.
2. Single Spotify account per trainer. Re-linking overwrites the existing refresh token.
3. Only read scopes requested (`user-top-read`, `user-read-recently-played`). No playback control, no playlist mutation.
4. State parameter is HMAC-signed `(trainer_id, expiry_ts)`. Rejects callbacks where state is missing, expired, or signature-invalid.
5. Token refresh happens lazily inside `SpotifyAPIClient._ensure_token()`. No background refresh job; refresh on first use after expiry.
6. Failed token refresh (revoked, expired) → clear the trainer's stored refresh token and surface a "please re-link" signal to the next birth attempt.

## Dependencies

- ADR-0001 (`BirthSeed` gains `trainer_id`) — not strictly required for this plan but lands as part of the same arc.

## Status

**Stub.** Full design pending dedicated grilling session. This file exists so `sound-provider-plan.md` has a concrete reference for its precondition.
