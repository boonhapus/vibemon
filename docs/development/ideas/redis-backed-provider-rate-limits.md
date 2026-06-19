# Redis-Backed Provider Rate Limits

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Area** | Providers / Infrastructure |
| **Related** | [infrastructure-plan.md](../plans/infrastructure-plan.md), [async-candidate-generation-redis-docket.md](async-candidate-generation-redis-docket.md) |

## Summary

Move provider upstream rate limiting from in-process hooks to a Redis-backed coordinator so sliding-window caps and in-flight concurrency mutexes hold across uvicorn workers, background jobs, and dev laptops hitting the same shared Redis.

## Problem

`app/providers/_api/rate_limits.py` hoists one `RateLimiterHook` per upstream quota key inside a single Python process. That fixes limit multiplication when multiple provider instances run concurrently in one worker, but production plans call for **uvicorn×3** and async job workers. Each process still gets its own deque and semaphore, so effective throughput scales with worker count and we can still trip vendor 429s.

## Concept

Keep `RateLimiterHook` as the niquests integration point, but back its shared state with Redis:

- **Sliding window** — sorted set or fixed-window counter keyed by quota id (e.g. `open-meteo`, `lastfm`).
- **Concurrency mutex** — Redis semaphore / lease counter for in-flight caps (Open-Meteo `concurrency=1`, MusicBrainz multiplexing rules, Last.fm pool of 5).

Reuse the existing Redis instance already planned for HTTP response cache and session store. Quota keys should match upstream identity (same keying as today's `rate_limits.py`), not per-client logging labels.

## Design

### Quota keys

Continue the current registry shape: one key per upstream bucket (`open-meteo` spans weather + elevation clients). Settings-dependent profiles (MusicBrainz public vs self-hosted concurrency) stay part of the key suffix.

### Hook behavior

`pre_request` and `ThrottledSessionMixin.acquire_concurrency` consult Redis before proceeding. On Redis failure, prefer **fail closed** (brief wait/retry) for vendor protection rather than bypassing limits.

### Scope

- Process-local limiters remain acceptable for single-worker dev without Redis.
- Redis path activates when `Settings` points at shared Redis (same gate as HTTP cache backend).

## Implementation

1. Add a small `RedisRateLimitBackend` (or extend cache Redis helpers) with `acquire_window_slot` + `acquire_concurrency` / `release_concurrency`.
2. Teach `RateLimiterHook` to delegate to injected backend; default stays in-memory for tests.
3. Wire production settings to Redis backend; keep ``rate_limits.shared()`` as the hook lookup seam.
4. Load-test two workers against one Open-Meteo quota to confirm flat combined throughput.

## Open Questions

- Count cache hits toward upstream limits, or only network sends?
- TTL / key cardinality for long windows (30-day Open-Meteo cap)?
- Separate Redis DB index vs shared namespace prefix?

## Success Criteria

- Three uvicorn workers collectively stay under configured Open-Meteo and MusicBrainz limits in a soak test.
- No regression in single-process dev when Redis is unavailable locally.

## Anti-Goals

- Replacing vendor 429 retry policy (`provider_retry_policy`) — reactive backoff stays.
- Global rate limiting of our own game API routes — this idea is upstream provider protection only.
