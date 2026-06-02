<p align="center">
  <img src="docs/public/morph.webp" alt="Vibemon morph" width="480" />
</p>

# Vibemon

**Adopt a crew of mons borne from your weather, your hood, and your playlists.** Raise your lineup, run into wild encounters, and battle turn-based—every birth and fight picks up the mood of whatever vibe you're living in.

<details>
<summary>Development</summary>

The backend lives under [`vibemon/backend/`](vibemon/backend/). Copy [`.env.example`](.env.example) to `.env` at the repo root and set storage URLs before running workflows or scripts.

**Deploy & infra** — production-shaped local stacks and compose runbooks:

- [Postgres](deploy/postgres/README.md) — app database (`VIBEMON_STORAGE__DATABASE`)
- [Redis](deploy/redis/README.md) — provider HTTP cache (`VIBEMON_STORAGE__CACHE`)

Broader rollout targets and service topology: [`docs/development/plans/infrastructure-plan.md`](docs/development/plans/infrastructure-plan.md).

**Docs** — domain language in [`docs/development/CONTEXT.md`](docs/development/CONTEXT.md); system shape in [`docs/development/ARCHITECTURE.md`](docs/development/ARCHITECTURE.md). Manual UX rehearsal via [`vibemon/backend/scripts/README.md`](vibemon/backend/scripts/README.md).

</details>
