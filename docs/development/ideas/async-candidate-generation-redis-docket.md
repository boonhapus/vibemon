# Async Candidate Generation (Redis + Docket)

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Area** | Generation / Infrastructure |
| **Related** | [../plans/infrastructure-plan.md](../plans/infrastructure-plan.md) |

## Summary

Add a job-backed async path for candidate generation while preserving today's domain rules: one active generation job per trainer, credits consumed only after a candidate is successfully shown, and multiple unresolved candidate reviews until each 24-hour timeout resolves.

## Problem

Synchronous generation is fine at current load, but request latency and operational control will suffer as traffic grows. We need a queue-backed path without changing credit, hold, or review semantics.

## Concept

Keep `VibemonService` as the domain orchestrator. Add an interface-layer enqueue path (API/worker boundary), not domain-layer queue semantics. Use Docket workers on Redis streams; maintain trainer-scoped generation hold in DB as the source of truth for single in-flight generation.

## Design

### Suggested components

- API command endpoint enqueues `GenerateCandidateCommand` with idempotency key.
- Worker dequeues command, calls `VibemonService.generate_candidate(...)`.
- DB lock/hold prevents concurrent per-trainer generation regardless of duplicate jobs.
- Job status table maps request id → queued/running/succeeded/failed for polling or webhook updates.

### Failure handling

- **Worker crash**: stale hold recovered by existing hold-timeout cleanup.
- **Duplicate enqueue**: dedupe via idempotency key at command boundary.
- **Partial failures**: preserve rule that credit is only consumed after successful shown candidate.

## Implementation

- Start behind feature flag: `candidate_generation_async`.
- Keep synchronous path as fallback.
- Add observability: queue depth, job latency, failure classes, stale hold count.

## Open Questions

- Polling vs. webhook for job status in the frontend?
- Worker scaling: single container vs. horizontal pool at launch?
