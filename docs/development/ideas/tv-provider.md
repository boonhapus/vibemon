# TV Provider

A Vibemon is born from the stories a trainer commits to across seasons. Trakt
watch history at birth time — shows, episode pacing, genre loyalty — folds into
an `Affinity` for episodic taste.

---

## Data Sources

**Trakt API** (official, needs OAuth client ID + access token):

- Watch history (episode-by-episode, timestamps, rewatching)
- Show and episode ratings
- DVR / collected / watchlist
- Per-show metadata: genres, status, network, country, language, air day,
  runtime, episode count, season count

**Enrichment (optional):** TVDB for extended genre tags, content ratings, and
thematic classifications.

---

## Why Separate from Movie Provider

| Dimension | Movie | TV |
|-----------|-------|-----|
| Consumption unit | One-shot film | Multi-episode arc |
| Binge signal | N/A | Episode/day pace |
| Commitment signal | N/A | Season completion %, show dropout rate |
| Genre breadth | Per-film genres | Per-show genres + episode-level genre drift |
| Completionism | N/A | Fraction of started shows that are finished |
| Catch-up vs current | N/A | How recently a show aired vs when watched |
| Data source | Letterboxd | Trakt (+ TVDB for enrichment) |

---

## Secrets

| Key | Required | Purpose |
| --- | -------- | ------- |
| `trakt.client_id` | yes | Trakt API OAuth |
| `trakt.access_token` | yes | Trakt API OAuth |

---

## Type → Genre Mapping

| Type | Signal Description |
|------|-------------------|
| NORMAL | sitcoms, workplace comedies, reality |
| FIRE | action thrillers, crime procedurals |
| WATER | dramas, soaps, emotional character pieces |
| GRASS | nature docs, travelogues, cooking shows |
| ICE | horror anthologies, true crime, suspense |
| FLYING | fantasy epics, sci-fi adventure, travel |
| FIGHTING | martial arts dramas, combat series |
| POISON | noir thrillers, psychological dramas |
| GROUND | westerns, historical dramas, period pieces |
| BUG | anime, animation, surreal comedy |
| ROCK | gritty dramas, coming-of-age series |
| GHOST | supernatural dramas, paranormal series |
| DRAGON | high fantasy, epic sci-fi, long-running sagas |
| ELECTRIC | cyberpunk, dystopian, tech-driven series |
| DARK | gothic dramas, bleak crime, dark comedy |
| STEEL | military dramas, post-apocalyptic, industrial |
| FAIRY | animated comedies, magical girl, whimsical |
| PSYCHIC | prestige dramas, anthology, experimental |

---

## Signal Design (6 stat axes)

| Stat | Signal | Data Source |
|------|--------|------------|
| HP | Avg episode runtime | Diary-weighted mean episode duration |
| Attack | Binge intensity | Max episodes in a single day (last 30d) |
| Defense | Show diversity | Distinct shows watched / total episodes |
| Sp. Attack | Completionism | Fraction of started seasons that are 100% watched |
| Sp. Defense | Catch-up latency | Time gap between air date and watch date (old = stable, fresh = reactive) |
| Speed | Daily episode rate | Episodes/day averaged over last 30 days |

---

## Intensity

Ratio of recent (last 30d) vs baseline (last year) episode-per-day rate. A
weekend binge spike yields high intensity.

---

## Provider Notes

| Condition | Note |
| --------- | ---- |
| No watch history | `"No recent episode views"` |
| Single show >70% of total episodes | `"Single show dominates"` |
| High dropout rate (many started, few finished) | `"Low completion rate"` |
| No enrichment available | `"TVDB enrichment unavailable"` |

---

## Moves

Episode-themed move names in `data/moves.json` (e.g. Binge Watch, Cliffhanger,
Cold Open, Filler Arc, Season Finale, Double Episode).

---

## Proposed Structure

```
providers/tv/
  __init__.py              # re-export TVProvider
  provider.py              # TVProvider(VibeProvider)
  schema.py                # TVObservation, parsed episode models
  const.py                 # Genre → VibemonTypeT mapping
  data/
    moves.json
  trakt/
    __init__.py
    api.py                 # Trakt API client
    schema.py              # Trakt response models
  tvdb/
    __init__.py
    api.py                 # TVDB enrichment client
    schema.py              # TVDB response models
```

---

## Wiring

Same opt-in pattern — gated behind secrets, registered in `scripts/_common.py`
and `frontend/src/lib/domains/generation/provider-options.ts`.
