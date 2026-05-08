---
name: db-analysis
description: >
  Repeatable SQLite analysis of vibemon.db — element, stat, move, and tier
  distributions compared against the balance skill's guidance. Load this skill
  when auditing randomly-generated world data for thematic drift, stat skew,
  or balance regressions.
metadata:
  version: 1.0.0
---

# Vibemon DB Analysis Skill

Audits a `.scripts/vibemon.db` SQLite database against the `vibemon/balance` skill's
reference tables — element distribution, stat profiles, BST tiers, move power bands,
level-1 ratios, and geographic/provider spread.

## When to load

- User asks "analyze the database", "check balance", "audit distribution"
- After a batch generation run to validate results
- Before a balance patch to understand current state
- When investigating stat or type skew

## Prerequisites

- `sqlite3` CLI on PATH
- `.scripts/vibemon.db` exists in project root
- `vibemon/balance` skill loaded for reference numbers

---

## Step 1 — Understand the schema

Run `.tables` and `.schema <table>` for each of:

```
identity    — base stats, elements, evo stage
vibemon     — runtime instances (level, links)
affinity    — links identity to vibemon
affinity_moves — which moves a vibemon knows
move        — type, category, power, pp, accuracy, priority, level_requirement
birth_context — geo coords + provider name
```

Key details:
- `identity.elements` is a JSON array: `["grass"]` or `["fire", "flying"]`
- `identity.base_hp` through `base_speed` are the 6 stats
- `move.power` is `NULL` for status moves
- `birth_context.provider_names` and `geo_coords` are JSON arrays

---

## Step 2 — Entity counts

```sql
SELECT 'identities' AS entity, COUNT(*) FROM identity
UNION ALL SELECT 'vibemon', COUNT(*) FROM vibemon
UNION ALL SELECT 'moves', COUNT(*) FROM move
UNION ALL SELECT 'affinities', COUNT(*) FROM affinity;
```

Expected: vibemon ≈ identities (some orphans OK), moves ≥ 200 for 150+ mons.

---

## Step 3 — Element distribution

### 3a. Element frequency (flattened from JSON)

```sql
SELECT
  e.value AS element,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM identity), 1) AS pct
FROM identity, json_each(identity.elements) AS e
GROUP BY e.value
ORDER BY count DESC;
```

### 3b. Single vs dual type ratio

```sql
SELECT
  CASE WHEN json_array_length(elements) = 1 THEN 'single' ELSE 'dual' END AS mode,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM identity), 1) AS pct
FROM identity
GROUP BY mode;
```

### 3c. Dual-type pairings

```sql
SELECT
  e1.value || '/' || e2.value AS pair,
  COUNT(*) AS count
FROM identity, json_each(identity.elements) AS e1, json_each(identity.elements) AS e2
WHERE json_array_length(identity.elements) = 2 AND e1.value < e2.value
GROUP BY e1.value, e2.value
ORDER BY count DESC;
```

**What to check**: Are all 18 types present? Water/Normal/Ground should not exceed ~50% combined.
Dual-type ratio should be 25-40%. Compare against `VibemonTypeT` in `backend/app/types.py`.

---

## Step 4 — Stat distribution

### 4a. Overall stat summary (avg, med, min, max)

```sql
SELECT 'HP' AS stat,
  ROUND(AVG(base_hp),1) AS avg, ROUND(AVG(base_hp),0) AS med,
  MIN(base_hp) AS min, MAX(base_hp) AS max FROM identity
UNION ALL SELECT 'ATK', ...same pattern for each stat...
UNION ALL SELECT 'BST',
  ROUND(AVG(base_hp+base_attack+base_defense+base_sp_attack+base_sp_defense+base_speed),1),
  ...etc... FROM identity;
```

**Compare against balance skill reference**:

| Stat | Min | Median | Max |
|------|-----|--------|-----|
| HP   | 1   | 70     | 255 |
| ATK  | 5   | 75     | 190 |
| DEF  | 5   | 70     | 230 |
| SPA  | 10  | 70     | 194 |
| SPD  | 20  | 70     | 230 |
| SPE  | 5   | 70     | 200 |

**Red flags**:
- Any stat avg < 50 or > 90 → skew likely
- Max values far below reference max → generation ceiling is capped (e.g. SPA max=56 means no special attackers)
- DEF is highest avg while ATK/SPE are lowest → generation algorithm favors defense

### 4b. Stat profile per element

```sql
SELECT
  e.value AS element,
  COUNT(*) AS n,
  ROUND(AVG(i.base_hp),1) AS hp,
  ROUND(AVG(i.base_attack),1) AS atk,
  ROUND(AVG(i.base_defense),1) AS def,
  ROUND(AVG(i.base_sp_attack),1) AS spa,
  ROUND(AVG(i.base_sp_defense),1) AS spd,
  ROUND(AVG(i.base_speed),1) AS spe,
  ROUND(AVG(i.base_hp+i.base_attack+i.base_defense+i.base_sp_attack+i.base_sp_defense+i.base_speed),1) AS bst
FROM identity i, json_each(i.elements) AS e
GROUP BY e.value
ORDER BY avg_bst DESC;
```

**Cross-reference with the Stat-Element Rating Matrix** from the balance skill.
For each element, check:
- Its S/A-grade stats are actually the highest
- Its D-grade stats are actually the lowest
- The pattern makes thematic sense

---

## Step 5 — BST tiers

### 5a. Tier distribution

```sql
SELECT
  CASE
    WHEN bst < 400 THEN 'RUNT'
    WHEN bst BETWEEN 400 AND 499 THEN 'MID'
    WHEN bst BETWEEN 500 AND 569 THEN 'SOLID'
    WHEN bst BETWEEN 570 AND 669 THEN 'APEX'
    ELSE 'MYTHIC'
  END AS tier,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM identity), 1) AS pct,
  ROUND(AVG(bst), 0) AS avg_bst
FROM (SELECT (base_hp + base_attack + base_defense + base_sp_attack + base_sp_defense + base_speed) AS bst FROM identity)
GROUP BY tier
ORDER BY avg_bst;
```

### 5b. BST histogram (25-point buckets)

```sql
SELECT
  ROUND((base_hp + base_attack + base_defense + base_sp_attack + base_sp_defense + base_speed) / 25.0) * 25 AS bucket,
  COUNT(*) AS count
FROM identity
GROUP BY bucket
ORDER BY bucket;
```

**What to check**: Healthy spread across tiers. RUNT ≥ 60% suggests stat generation
is undertuned. 0% MYTHIC or 0% APEX means the high end is missing.

---

## Step 6 — Move analysis

### 6a. Type distribution

```sql
SELECT type, COUNT(*) AS count, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM move), 1) AS pct
FROM move GROUP BY type ORDER BY count DESC;
```

All 18 types should be represented. Max share should not exceed ~12%.

### 6b. Category split

```sql
SELECT category, COUNT(*) AS count, ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM move), 1) AS pct
FROM move GROUP BY category ORDER BY count DESC;
```

Expected: Physical 35-45%, Special 30-40%, Status 20-30%.

### 6c. Power bands (damaging moves only)

```sql
SELECT
  CASE
    WHEN power BETWEEN 10 AND 30 THEN 'Spam (10-30)'
    WHEN power BETWEEN 35 AND 55 THEN 'Early STAB (35-55)'
    WHEN power BETWEEN 56 AND 64 THEN 'Gap (56-64)'
    WHEN power BETWEEN 65 AND 80 THEN 'Mid (65-80)'
    WHEN power BETWEEN 81 AND 100 THEN 'Workhorse (81-100)'
    WHEN power BETWEEN 101 AND 110 THEN 'High (101-110)'
    WHEN power BETWEEN 120 AND 150 THEN 'Signature (120-150)'
    WHEN power > 150 THEN 'Mega (150+)'
  END AS band,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM move WHERE power IS NOT NULL), 1) AS pct_of_damaging,
  ROUND(AVG(accuracy), 2) AS avg_acc,
  ROUND(AVG(pp), 1) AS avg_pp
FROM move
WHERE power IS NOT NULL
GROUP BY band
ORDER BY MIN(power);
```

**Reference from balance skill**:

| Band | Power | Typical PP | Typical Acc |
|------|-------|-----------|-------------|
| Spam | 10-30 | 25-40 | 1.0 |
| Early STAB | 35-55 | 20-30 | 1.0 |
| Mid | 65-80 | 15-20 | 0.95-1.0 |
| Workhorse | 81-100 | 10-15 | 0.9-1.0 |
| High | 101-110 | 5-10 | 0.8-1.0 |
| Signature | 120-150 | 5 | 0.7-0.9 |
| Mega | 150+ | 5 | 0.9 |

### 6d. Level-1 move check

```sql
SELECT COUNT(*) AS total_moves, COUNT(*) FILTER (WHERE level_requirement = 1) AS l1_moves,
  ROUND(100.0 * COUNT(*) FILTER (WHERE level_requirement = 1) / COUNT(*), 1) AS l1_pct
FROM move;
```

Expected: ~70% of moves at level 1.

### 6e. Level-1 power profile

```sql
SELECT
  CASE
    WHEN power IS NULL THEN 'Status'
    WHEN power BETWEEN 10 AND 30 THEN 'Spam (10-30)'
    WHEN power BETWEEN 35 AND 55 THEN 'Early STAB (35-55)'
    WHEN power BETWEEN 56 AND 64 THEN 'Gap (56-64)'
    WHEN power BETWEEN 65 AND 80 THEN 'Mid (65-80)'
    WHEN power BETWEEN 81 AND 100 THEN 'Workhorse (81-100)'
    ELSE 'High+ (100+)'
  END AS band,
  COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM move WHERE level_requirement = 1), 1) AS pct
FROM move
WHERE level_requirement = 1
GROUP BY band
ORDER BY MIN(power);
```

**L1 damaging move targets**:
- 20-30% at 10-30 power
- 45-60% at 35-45 power (early STAB)
- 10-20% at 50-55 power
- 0-5% at 56-60 power
- 0% above 60

### 6f. Priority distribution

```sql
SELECT priority, COUNT(*) AS count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM move), 1) AS pct,
  ROUND(AVG(power), 0) AS avg_power,
  COUNT(CASE WHEN power IS NOT NULL THEN 1 END) AS damaging
FROM move GROUP BY priority ORDER BY priority;
```

Check: ≤7% of moves with priority ≥ 1. +1 priority moves avg power ≤ 40.

---

## Step 7 — Provider & geographic spread

### 7a. Provider distribution

```sql
SELECT json_extract(provider_names, '$[0]') AS provider, COUNT(*) AS count
FROM birth_context GROUP BY provider ORDER BY count DESC;
```

### 7b. Level distribution

```sql
SELECT level, COUNT(*) AS count FROM vibemon GROUP BY level ORDER BY level;
```

---

## Step 8 — Compile findings

Organize findings by severity:

| Severity | When |
|----------|------|
| **CRITICAL** | Stat generation broken (max values far below reference, entire stat types unusable), entire type missing (0 Steel mons) |
| **HIGH** | Element-stat correlation inverted (Dark slow, Electric not fast), >60% tier in one bucket, L1 power curve inverted |
| **MEDIUM** | Type distribution skewed (Water/Normal/Ground > 60% combined), several types < 5 appearances |
| **LOW** | All moves L1 (expected early in project), single provider bias, all same evo stage |

Compare each finding against the `vibemon/balance` skill's reference tables.
Note where the data *expectedly* diverges (e.g. realworld geo-clustering producing
Water/Normal/Ground bias is thematic if the generation is location-aware).

---

## Analysis history

First run: 2026-05-08 — 153 identities, 214 moves. Key findings:
- SPA max capped at 56 (no special attackers possible)
- DEF avg 90 vs target 70, ATK avg 35 vs target 75
- Steel type entirely absent
- 88% RUNT tier, 0% MYTHIC
- L1 moves: 55% in Mid band (65-80) when should be ~5%
- Electric/Dark/Dragon stat profiles inverted vs element ratings
