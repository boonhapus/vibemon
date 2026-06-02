# Book Provider

A Vibemon is born from the stories a trainer carries with them. Goodreads or
StoryGraph reading history at birth time — shelves, ratings, genres, moods —
folds into an `Affinity` for literary taste.

---

## Data Sources

**StoryGraph API** (preferred — rich mood/genre taxonomy, content warnings,
pace tagging):

- Reading history (books logged, dates, editions)
- Ratings, reviews, shelves
- Per-book: genres, moods, pace (slow/medium/fast), tropes, content warnings,
  page count, format, fiction/non-fiction, publication year

**Goodreads API** (fallback — broader adoption, but shallower taxonomy):

- Read / currently-reading / to-read shelves
- Ratings, reviews, shelves
- Per-book: genres (user-shelved), page count, publication year, author, series

**Open Library enrichment (optional):** Subject tags, Dewey decimal, first
sentence, awards.

---

## Secrets

| Key | Required | Purpose |
| --- | -------- | ------- |
| `books.api_key` | yes | StoryGraph or Goodreads API key |
| `books.user_id` | yes | Target user ID |
| `books.source` | yes | `"storygraph"` or `"goodreads"` |

---

## Type → Genre / Mood Mapping

| Type | Signal Description |
|------|-------------------|
| NORMAL | contemporary fiction, literary fiction, general non-fiction |
| FIRE | thrillers, page-turners, fast-paced action |
| WATER | romance, emotional drama, slow-burn literary |
| GRASS | nature writing, gardening, rural memoirs |
| ICE | horror, gothic, cold suspense, isolation |
| FLYING | fantasy adventure, travel writing, exploration |
| FIGHTING | war, political struggle, survival narratives |
| POISON | crime, mystery, noir, psychological suspense |
| GROUND | historical fiction, epic sagas, mythology retold |
| BUG | speculative, weird fiction, surreal, experimental |
| ROCK | gritty realism, working-class stories, memoirs |
| GHOST | supernatural, paranormal, dark fantasy |
| DRAGON | epic fantasy, high fantasy, sprawling world-building |
| ELECTRIC | sci-fi, cyberpunk, dystopian |
| DARK | grimdark, true crime, bleak literary |
| STEEL | military sci-fi, industrial non-fiction, hard-boiled |
| FAIRY | children's, YA fantasy, whimsical, fairy tales |
| PSYCHIC | philosophy, literary theory, dense classics |

---

## Signal Design (6 stat axes)

| Stat | Signal | Data Source |
|------|--------|------------|
| HP | Avg page count | Diary-weighted mean book length |
| Attack | Pace intensity | Fraction of books tagged "fast-paced" (StoryGraph) or genre-thriller density |
| Defense | Genre breadth | Distinct genres / total books read |
| Sp. Attack | Rating stretch | Fraction of ratings <2★ or >4★ |
| Sp. Defense | Reread rate | Books logged more than once |
| Speed | Books per month | Reading rate over last 6 months |

---

## Intensity

Ratio of recent (last 90d) vs baseline (last year) books-per-month rate. A
reading sprint (e.g. finishing a trilogy in a week) yields high intensity.

---

## Provider Notes

| Condition | Note |
| --------- | ---- |
| No reading history | `"No books logged"` |
| Single genre >60% of library | `"Single genre dominates"` |
| Reread fraction >30% | `"High reread loyalty"` |
| Fallback to Goodreads | `"Using Goodreads source"` |

---

## Moves

Book-themed move names in `data/moves.json` (e.g. Dog-ear, Cliffhanger Chapter,
Appendix, Epilogue, Marginalia, Bookmark, Chapter Break).

---

## Proposed Structure

```
providers/book/
  __init__.py              # re-export BookProvider
  provider.py              # BookProvider(VibeProvider)
  schema.py                # BookObservation, parsed reading models
  const.py                 # Genre → VibemonTypeT mapping
  data/
    moves.json
  storygraph/
    __init__.py
    api.py                 # StoryGraph API client
    schema.py              # StoryGraph response models
  goodreads/
    __init__.py
    api.py                 # Goodreads API client
    schema.py              # Goodreads response models
```

---

## Wiring

Same opt-in pattern — gated behind secrets, registered in `scripts/_common.py`
and `frontend/src/lib/domains/generation/provider-options.ts`.
