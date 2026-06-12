# Movie Provider

| | |
| --- | --- |
| **Status** | Idea |
| **Priority** | Low |
| **Complexity** | Medium |
| **Area** | Providers |
| **Related** | [tv-provider.md](tv-provider.md), [book-provider.md](book-provider.md) |

## Summary

A **Vibemon** is born from the stories a trainer watches. Letterboxd diary history at birth time — rated films, genres, moods, themes — folds into an **Affinity** for cinematic taste.

## Problem

Trainers who express identity through film have no birth signal today. Music, climate, and biome cover other slices of life; cinematic diary data is a natural, structured affinity source with rich genre and pacing metadata.

## Concept

Opt-in **Movie Provider** using Letterboxd API (RSS fallback) to map film diary signals to element affinity, six stat axes, and intensity from recent vs. baseline viewing rate.

## Design

### Data sources

**Letterboxd API** (official, needs API key + secret):

- Diary entries (recent history, rewatches)
- Ratings, reviews, likes, watchlist
- Per-film metadata: genres, themes, moods, content descriptors, runtime, release year, country, language

**Fallback:** Letterboxd public RSS feed for diary/watched (read-only, no API key needed but much thinner).

### Secrets

| Key | Required | Purpose |
| --- | -------- | ------- |
| `letterboxd.api_key` | yes | Official API authentication |
| `letterboxd.api_secret` | yes | Official API authentication |
| `letterboxd.username` | yes | Target user |

### Type mapping

| Type | Signal Description |
|------|-------------------|
| NORMAL | broad comedy, drama, slice-of-life |
| FIRE | action, adrenaline, thrillers |
| WATER | romance, drama, emotional depth |
| GRASS | nature docs, pastoral, eco-films |
| ICE | horror, suspense, isolation |
| FLYING | adventure, fantasy, escapism |
| FIGHTING | martial arts, war, combat sports |
| POISON | noir, crime, psychological thriller |
| GROUND | westerns, historical, grounded epics |
| BUG | animation, creature features, surreal |
| ROCK | gritty realism, coming-of-age, indie |
| GHOST | supernatural, gothic, psychological |
| DRAGON | epic fantasy, mythological, spectacle |
| ELECTRIC | sci-fi, cyberpunk, tech thrillers |
| DARK | film noir, gothic, bleak dramas |
| STEEL | action, war, industrial / post-apocalyptic |
| FAIRY | musicals, animated, whimsical, family |
| PSYCHIC | art house, philosophical, experimental |

### Signal design (6 stat axes)

| Stat | Signal | Data Source |
|------|--------|------------|
| HP | Avg film runtime | Diary-weighted mean duration |
| Attack | Genre intensity score | Action/Horror/War density |
| Defense | Era spread | Release year variance (breadth of taste) |
| Sp. Attack | Rating aggression | Fraction of ratings <2★ or >4★ |
| Sp. Defense | Rewatch rate | Diary entries that are rewatches |
| Speed | Diary pace | Films/week in last 30 days |

### Intensity

Ratio of recent (last 30d) vs baseline (last year) diary entry rate. A binge-watching spike yields high intensity.

### Provider notes

| Condition | Note |
| --------- | ---- |
| Empty diary, fallback to watchlist | `"No recent diary entries"` |
| Single genre >60% of diary | `"Single genre dominates"` |
| Used RSS fallback instead of API | `"API quota reduced"` |

### Moves

Movie-themed move names in `data/moves.json` (e.g. Close-Up, Tracking Shot, Montage, Flashback, Slow Burn).

### Proposed structure

```
providers/movie/
  __init__.py              # re-export MovieProvider
  provider.py              # MovieProvider(VibeProvider)
  schema.py                # MovieObservation, parsed film models
  const.py                 # Genre → VibemonTypeT mapping
  data/
    moves.json
  letterboxd/
    __init__.py
    api.py                 # Letterboxd API client
    schema.py              # Letterboxd response models
```

### Wiring

Same opt-in pattern as **Music Provider** — gated behind secrets, registered in `scripts/_common.py` and `frontend/src/lib/domains/generation/provider-options.ts`.

## Open Questions

- RSS fallback acceptable for beta or API-only?
- Mood/theme tags from Letterboxd vs. genre-only v1?
