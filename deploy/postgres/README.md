# Local Postgres (Docker / Colima)

Vibemon requires explicit storage URLs in `.env`. Use this stack when you want a production-shaped Postgres 16 instance on your machine.

No custom Dockerfile is required — the official `postgres:16-alpine` image is enough.

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

## Colima (macOS)

Start a VM with Docker inside (lighter profile for DB-only dev):

```bash
colima start --cpu 2 --memory 4 --disk 30
```

For a full app stack test box (matches `docs/development/plans/infrastructure-plan.md`):

```bash
colima start --cpu 6 --memory 14 --disk 120 \
  --vm-type vz --mount-type virtiofs \
  --network-address
```

Auto-start on login:

```bash
brew services start colima
```

After macOS updates or sleep issues, check status:

```bash
colima status
colima ssh -- date   # clock drift breaks JWT / replication
```

## Windows

Docker Desktop is the straightforward path: enable WSL2 backend, then use the same `docker compose` commands below from PowerShell or your WSL shell.

Colima on Windows only runs inside WSL2 (not native PowerShell). If you use that route, install Colima in your Linux distro and run `colima start` there; bind mounts and paths must stay inside WSL (`/home/...`), not `C:\...`.

## Start Postgres

From the repo root:

```bash
cd deploy/postgres
cp .env.example .env   # optional; defaults work for local dev
docker compose up -d
docker compose ps
docker compose logs -f postgres
```

Stop (keep data):

```bash
docker compose stop
```

Reset database (destructive):

```bash
docker compose down -v
docker compose up -d
```

## Connect from vibemon

Set in repo-root `.env` (or export in your shell):

```bash
VIBEMON_STORAGE__DATABASE=postgresql+asyncpg://vibemon:vibemon@127.0.0.1:5432/vibemon
```

Use the password from `deploy/postgres/.env` if you changed `POSTGRES_PASSWORD`.

Initialize schema from `vibemon/backend`:

```bash
uv run python scripts/init_db.py
```

Quick sanity check with `psql` inside the container:

```bash
docker compose exec postgres psql -U vibemon -d vibemon -c 'SELECT 1'
```

## Schema lifecycle (pre-1.0)

While models are still in flux, recreate the DB after model changes:

```bash
docker compose exec postgres dropdb -U vibemon vibemon
docker compose exec postgres createdb -U vibemon vibemon
cd ../../vibemon/backend && uv run python scripts/init_db.py
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `port 5432 already in use` | Set `POSTGRES_PORT=5433` in `.env` and use `@127.0.0.1:5433` in the URL |
| Colima not running | `colima start` |
| Empty `docker` command on Mac | `colima start` creates the daemon; ensure Docker CLI is installed |
| Permission errors on bind mounts | This compose uses a named volume only — no host bind mount needed |
