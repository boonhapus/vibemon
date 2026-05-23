# Vibemon Emote Animation Plan (Locked)

## Goal
Add paid, personalized emote animations generated from existing Vibemon assets, with version history and rollback, without bloating core domain schema.

## Scope
- Backend-first implementation plan for:
  - async per-emote animation generation
  - paid credit handling (charge-on-success)
  - versioned animation history
  - current-version pointers
  - polling status API for web frontend
- Out of scope for v1:
  - websockets/SSE push
  - multi-provider routing
  - full historical gallery UX polish

## Locked Product Decisions
- Animation is optional and paid.
- Hard precondition: generation only allowed after `Vibemon` is `MANIFESTED` and required emote pose assets exist.
- Async generation after manifest; never blocks birth/adoption.
- One native image-to-video generation call per emote (no per-frame LLM calls).
- Require provider with native image-to-video support in v1.
- Per-emote jobs (with optional batch trigger), dedup in-flight.
- Batch billing is per-emote success.
- Per-emote readiness is visible immediately, even during batch.
- Capture credits on success only (hold/authorize first, release on failure).
- Rollback to old version is free.
- Keep `Vibemon.aesthetic` lean (reference surface only), no in-memory version arrays.
- Persist history in DB/storage; use explicit current pointer in DB.
- Add animation as first-class asset kinds.
- Use canonical current slots + separate historical version records.
- Promote new current via atomic pointer swap.
- Dedupe by fingerprint (normalized inputs + prompt version + rendered prompt hash + model/settings).
- Prompt templates remain `.mdc`; template version in frontmatter.
- Style control: preset + optional short text note (moderated before enqueue), with per-emote persisted defaults and per-request override.
- Return mapped product error codes to UI; keep raw provider errors server-side.
- Polling status endpoint for web v1.
- Status returns manifest URL; manifest stores object keys, not signed URLs.
- Manifest keys signed at fetch/session step.
- Deleting Vibemon cascades animation/history asset cleanup.

## Architecture Overview
1. Request enqueue (single emote or batch).
2. Validate preconditions + moderation + entitlement + dedupe.
3. Create job row(s) with `queued` state.
4. In-process worker executes jobs.
5. Generate video clip (provider image-to-video).
6. Validate output + optional one quality retry + technical retries.
7. Persist version artifacts.
8. Promote to current pointers atomically.
9. Capture credit on success; release hold on failure.
10. Surface status via polling endpoint.

## Data Model Plan
Implement via SQLAlchemy models + migration.

### 1) Extend asset kinds
Add canonical per-emote current animation artifacts:
- `animation/emote-resting/current.webm`
- `animation/emote-resting/current.manifest.json`
- ... same for `happy`, `frustrated`, `proud`, `confused`, `sad`
- Optional: frame asset kinds for current only (or store frames in version table and map into current refs on promote).

Update:
- `backend/app/data_store/types.py` (`AssetKind`)
- `backend/app/data_store/const.py` (`ASSET_CONTENT_TYPES`, required sets if needed)

### 2) Animation job table
`vibemon_animation_job`
- `id` (uuid)
- `vibemon_id` (fk)
- `emote` (enum/string)
- `state` (`queued|running|succeeded|failed|canceled`)
- `error_code` (nullable)
- `error_message` (nullable user-safe)
- `provider_model`
- `fingerprint`
- `requested_by` (nullable trainer id)
- `credit_hold_id` (nullable)
- `attempt_count`
- timestamps (`created_at`, `started_at`, `finished_at`, `updated_at`)
- dedupe indexes for active jobs (`vibemon_id + emote + state in queued/running`)

### 3) Animation version history table
`vibemon_animation_version`
- `id` (uuid)
- `vibemon_id` (fk)
- `emote`
- `fingerprint`
- `provider_model`
- `prompt_template_version`
- `prompt_render_hash`
- `style_preset`
- `style_note_original` (approved text)
- `style_note_normalized`
- `webm_object_key`
- `manifest_object_key`
- optional `quality_report_json`
- `is_deleted` (soft-delete optional)
- timestamps
- unique/index as appropriate for dedupe lookup

### 4) Current pointer table
`vibemon_animation_current`
- `vibemon_id` (fk)
- `emote`
- `version_id` (fk to history table)
- `updated_at`
- unique `(vibemon_id, emote)`

### 5) Per-emote style defaults
`vibemon_animation_pref`
- `vibemon_id` (fk)
- `emote`
- `style_preset`
- `style_note_original`
- `style_note_normalized`
- `updated_at`
- unique `(vibemon_id, emote)`

## Storage/Object Key Plan
- Current canonical keys use fixed slot paths in `AssetKind`.
- Historical versions use versioned subpaths, e.g.:
  - `animation/emote-happy/versions/<version_id>/clip.webm`
  - `animation/emote-happy/versions/<version_id>/manifest.json`
  - (current-only frames) `animation/emote-happy/current/frames/<frame>.png`
- Promote by writing version artifacts first, then atomically updating:
  - `vibemon_animation_current`
  - corresponding `vibemon_asset` current rows

## Prompting & Fingerprint Plan
Fingerprint inputs:
- reference asset hash
- target emote still hash
- selected model id
- generation params (duration/fps/style preset/etc.)
- style note normalized
- prompt frontmatter version
- rendered prompt hash

Rules:
- If identical fingerprint already has successful version, reuse it.
- If same fingerprint has queued/running job, return existing job id.
- No duplicate credit charges for reused outputs.

## Worker Plan
In-process background worker with durable DB queue semantics.

Execution steps per job:
1. Transition `queued -> running` (guard with row lock/compare-and-set).
2. Build inputs from persisted assets (reference + emote still).
3. Run provider image-to-video call.
4. Technical validation:
   - alpha present (or fallback matte-removal once)
   - duration/fps bounds
   - artifact checks
5. Quality validation:
   - identity consistency
   - emotion fidelity
   - loop smoothness
6. Retry policy:
   - transient technical: bounded auto retries
   - quality mismatch: one tuned retry
7. Persist version artifacts.
8. Promote current atomically.
9. Capture credit hold.
10. Mark `succeeded` and publish status.

Failure path:
- Release credit hold.
- Mark `failed` with mapped error code.
- Keep raw provider error in logs/internal columns only.

## API Plan (Web v1)
All responses use mapped product error codes.

### 1) Enqueue single emote
`POST /v1/vibemon/{id}/animations/{emote}`
- body:
  - optional `style_preset`
  - optional `style_note`
  - optional `use_saved_defaults` (default true)
- behavior:
  - validate manifested precondition
  - moderation check
  - dedupe/reuse logic
  - enqueue/create or return existing in-flight

### 2) Enqueue batch
`POST /v1/vibemon/{id}/animations:batch`
- body: list of emotes or `all=true`
- returns per-emote job handles

### 3) Poll status
`GET /v1/vibemon/{id}/animations/status`
- returns per emote:
  - state
  - current version id (if any)
  - current manifest url (if ready)
  - active job id
  - last error code/message

### 4) Version history
`GET /v1/vibemon/{id}/animations/{emote}/versions`
- paginated list (newest first)

### 5) Restore version
`POST /v1/vibemon/{id}/animations/{emote}/restore`
- body: `version_id`
- free operation, updates current pointer atomically, records restore event

### 6) Save defaults
`PUT /v1/vibemon/{id}/animations/{emote}/preferences`
- style preset + optional note

### 7) Sign manifest keys
`POST /v1/assets/sign-manifest`
- input: manifest object key or key list
- output: signed URLs for current client session

## Billing/Credits Plan
- On enqueue: create credit hold authorization (if required by billing system).
- On success: capture.
- On failure/cancel/reuse-existing: release/no-op.
- Rollback: no charge.
- Batch: per-emote hold/capture semantics.

## Validation & Moderation Plan
- Validate style note length and character policy.
- Moderate style note before job creation.
- Reject early with deterministic code (`ANIM_STYLE_NOTE_REJECTED`, etc.).

## Testing Plan
### Unit
- fingerprint normalization and dedupe behavior
- precondition gating (`MANIFESTED` + required assets)
- moderation rejection path
- retry policy branching
- atomic promote logic
- billing hold/capture/release transitions

### Integration
- single emote success end-to-end
- batch partial success
- in-flight dedupe (same emote concurrent requests)
- restore old version updates current without new generation
- delete Vibemon cascades animation assets/history cleanup

### Regression
- existing christen/manifest/adopt flows unaffected
- `vibemon_asset` behavior for existing sprite/audio kinds unchanged

## Rollout Plan
1. Land DB schema + model changes behind feature flag.
2. Add asset kinds and storage plumbing.
3. Add API endpoints with enqueue/status stubs.
4. Implement worker loop and provider integration.
5. Enable single-emote generation in staging.
6. Validate quality + cost + latency metrics.
7. Enable batch endpoint.
8. Gradual production rollout (staff/internal -> small cohort -> full).

## Observability
- Metrics:
  - job count by state/emote
  - success/failure rates
  - retries by reason
  - median/p95 generation time
  - credit capture/release counts
  - dedupe hit rate
- Logs:
  - job lifecycle transitions
  - provider request ids
  - validation failure reasons
- Alerts:
  - sustained failure spike
  - stuck running jobs
  - provider timeout surge

## Implementation Checklist
- [ ] Add new DB tables (`job`, `version`, `current`, `pref`)
- [ ] Add animation `AssetKind` constants + content types
- [ ] Add repository/service layer for animation domain
- [ ] Add moderation + style normalization helpers
- [ ] Add fingerprint builder + dedupe lookup
- [ ] Implement worker execution loop
- [ ] Implement provider adapter interface for image-to-video
- [ ] Persist version artifacts + current pointer swap transaction
- [ ] Add billing hook integration (hold/capture/release)
- [ ] Add status/history/restore/preferences/signing endpoints
- [ ] Add tests (unit/integration/regression)
- [ ] Add feature flag + rollout config

## Notes for Future Expansion (Post-v1)
- multi-provider routing and fallback
- push notifications (SSE/WebSocket)
- historical frame persistence beyond current
- “force new attempt” generation option
- richer style controls per emote archetype
