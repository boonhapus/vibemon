# Async Candidate Generation (Redis + Docket)

Status: Idea
Date: 2026-05-18

## Goal
Add a job-backed async path for candidate generation while preserving current domain rules:
- One active generation job per trainer.
- Credits consumed only after candidate is successfully shown.
- Multiple unresolved candidate reviews allowed until each 24-hour timeout resolves.

## Why
Synchronous generation is fine now, but async orchestration can improve request latency and operational control once load grows.

## Proposed shape
- Keep `VibemonService` as the domain orchestrator.
- Add an interface-layer enqueue path (API/worker boundary), not domain-layer queue semantics.
- Use Docket workers backed by Redis streams; run workers in Docker where useful.
- Maintain trainer-scoped generation hold in DB as the source of truth for single in-flight generation.

## Suggested components
- API command endpoint enqueues `GenerateCandidateCommand` with idempotency key.
- Worker dequeues command, calls `VibemonService.generate_candidate(...)`.
- DB lock/hold prevents concurrent per-trainer generation regardless of duplicate jobs.
- Job status table maps request id -> queued/running/succeeded/failed for polling or webhook updates.

## Failure handling
- Worker crash: stale hold recovered by existing hold-timeout cleanup.
- Duplicate enqueue: dedupe via idempotency key at command boundary.
- Partial failures: preserve current rule that credit is only consumed after successful shown candidate.

## Rollout notes
- Start behind feature flag: `candidate_generation_async`.
- Keep synchronous path as fallback.
- Add observability: queue depth, job latency, failure classes, stale hold count.

