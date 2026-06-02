# Local Redis (Docker / Colima)

Vibemon provider HTTP caches are selected by `VIBEMON_STORAGE__CACHE` in repo-root `.env`.
Use this stack when you want a production-shaped Redis instance on your machine instead of
the default SQLite file cache.

No custom Dockerfile is required — the official `redis:7-alpine` image is enough.

## Prerequisites

| Host | Runtime |
|------|---------|
| macOS | [Colima](https://github.com/abiosoft/colima) + Docker CLI (`brew install colima docker`) |
| Windows | [Docker Desktop](https://www.docker.com/products/docker-desktop/) or Colima inside WSL2 |
| Linux | Docker Engine + Compose plugin |

Verify:

```bash
docker version
docker compose version
```

## Start Redis

From the repo root:

```bash
cd deploy/redis
cp .env.example .env   # optional; defaults work for local dev
docker compose up -d
docker compose ps
docker compose logs -f redis
```

Stop (keep data):

```bash
docker compose stop
```

Reset cache (destructive):

```bash
docker compose down -v
docker compose up -d
```

## Connect from vibemon

Set in repo-root `.env`:

```bash
VIBEMON_STORAGE__CACHE=redis://127.0.0.1:6379/0
```

Restart backend processes or scripts so `Settings.load()` picks up the change.

Provider cache keys are namespaced by provider, for example:

- `musicbrainz_web_api:<hash>`
- `lastfm_web_api:<hash>`
- `reccobeats_web_api:<hash>`

Inspect keys:

```bash
docker compose exec redis redis-cli --scan --pattern 'musicbrainz_web_api:*' | head
```

Flush one provider namespace during dev (example):

```bash
docker compose exec redis redis-cli --scan --pattern 'musicbrainz_web_api:*'
```

To wipe the entire cache database during local dev:

```bash
docker compose exec redis redis-cli FLUSHDB
```

## Configuration notes

This compose matches `docs/development/plans/infrastructure-plan.md`:

- `appendonly no` — cache is regenerable; AOF not required
- `maxmemory 2gb` with `allkeys-lru` — evict oldest keys under memory pressure

For production, bind Redis to a private interface and protect it with `requirepass` or ACLs.
Do not expose an unauthenticated Redis port publicly.

Redis has **no** setting to skip authentication for clients on a local or private network.
Once `requirepass` (or an ACL password) is set, every connection must authenticate regardless
of source IP. `protected-mode` is different: it blocks unauthenticated *remote* connections
when no password is configured — it is not a LAN password bypass.

Typical production pattern: private network + firewall on port 6379 + password in the cache URL
(`redis://:password@host:6379/0`). Dev compose intentionally omits a password and publishes
6379 to localhost only.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port 6379 already in use` | Set `REDIS_PORT=6380` in `.env` and use `@127.0.0.1:6380` in the cache URL |
| Colima not running | `colima start` |
| Empty `docker` command on Mac | `colima start` creates the daemon; ensure Docker CLI is installed |
| Cache still writing SQLite | Confirm `VIBEMON_STORAGE__CACHE` uses `redis://` and restart the process |
