# GitHub Provider

A Vibemon is born from how a trainer builds. GitHub profile activity at birth
time — languages, commit cadence, project longevity — folds into an `Affinity`
for developer craft.

---

## Data Sources

**GitHub API** (v4 GraphQL, needs personal access token):

- User profile (bio, created date, public repos)
- Repositories (languages, stars, forks, archived status, created/pushed dates,
  topics, description)
- Commit activity (last 90d push cadence per repo, contribution calendar)
- Pull requests (created, merged, closed, reviews given)
- Issue activity (opened, commented)
- Org memberships, pinned repos, sponsors

**Public fallback:** Unauthed v3 REST (60 req/hr, no private repo data, no
contribution calendar detail).

---

## Secrets

| Key | Required | Purpose |
| --- | -------- | ------- |
| `github.token` | yes | GitHub personal access token |
| `github.username` | yes | Target user |

---

## Type → Language Mapping

| Type | Languages |
|------|-----------|
| NORMAL | C#, Shell, Lua, SQL |
| FIRE | Go, Zig |
| WATER | Swift, Elixir |
| GRASS | Ruby |
| ICE | Crystal, Nim |
| FLYING | HTML, CSS, Tailwind |
| FIGHTING | Go, Rust (systems) |
| POISON | PHP, VBA |
| GROUND | Java, SQL, Terraform |
| BUG | JavaScript, Gleam |
| ROCK | C, Zig |
| GHOST | Lua, Assembly |
| DRAGON | C++, Scala, OCaml |
| ELECTRIC | Kotlin, Dart |
| DARK | Assembly, Haskell |
| STEEL | Rust, C++, OCaml |
| FAIRY | TypeScript, Ruby, Kotlin |
| PSYCHIC | Python, Haskell, Lisp, Prolog |

Languages not listed are bucketed by closest family (e.g. Clojure → PSYCHIC,
R → GRASS, Julia → ELECTRIC).

---

## Signal Design (6 stat axes)

| Stat | Signal | Data Source |
|------|--------|------------|
| HP | Project longevity | Mean age of repos that still show activity (commitment endurance) |
| Attack | Commit cadence | Commits/week averaged over last 90 days |
| Defense | Language breadth | Distinct languages across all repos |
| Sp. Attack | PR quality bar | Fraction of authored PRs that were merged without issue reopen |
| Sp. Defense | Issue responsiveness | Mean time to first response on owned repos |
| Speed | Recent velocity | Commits/day in last 14 days vs last 90 days |

---

## Intensity

Ratio of recent (last 14d) vs baseline (last 90d) commit rate. A hackathon
sprint yields high intensity. Zero activity across the window → floor intensity.

---

## Provider Notes

| Condition | Note |
| --------- | ---- |
| No repos or activity | `"No public repositories found"` |
| Single language >70% of bytes | `"Single language dominates"` |
| All repos archived | `"All repositories archived"` |
| API rate-limited, degraded data | `"GitHub API rate limit reached"` |

---

## Moves

Development-themed move names in `data/moves.json` (e.g. Rebase, Squash, Hotfix,
Code Review, Stack Overflow, Edge Case, Merge Conflict, Pair Program).

---

## Proposed Structure

```
providers/github/
  __init__.py              # re-export GitHubProvider
  provider.py              # GitHubProvider(VibeProvider)
  schema.py                # GitHubObservation, parsed repo/commit models
  const.py                 # Language → VibemonTypeT mapping
  data/
    moves.json
  api/
    __init__.py
    graphql.py             # GitHub v4 GraphQL client
    schema.py              # GitHub GraphQL response models
```

---

## Wiring

Same opt-in pattern — gated behind secrets, registered in `scripts/_common.py`
and `frontend/src/lib/domains/generation/provider-options.ts`.
