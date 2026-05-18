# Providers split impure fetch from pure synthesize

The `Provider` interface forces every plugin to expose two methods: `fetch(seed)` may do I/O and returns a raw payload, while `synthesize(seed, payload)` must be pure and returns an `Affinity`. This isolates all external calls into one stage so payloads can be captured as a `BirthSnapshot` and replayed deterministically through `synthesize` without re-hitting upstream APIs. The simpler single-method alternative would have made replay impossible whenever an upstream changed or rate-limited. See `app/plugins/provider.py:74`.
