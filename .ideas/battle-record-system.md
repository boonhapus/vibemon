# Battle Record System

## Problem
Track battles for XP distribution. Vibemon gain XP per round won, not whole battle.

## Schema Changes

1. **Add `id` field to `Vibemon`** (`backend/app/schema.py`)
   - Persistent UUID to track instance across battles

2. **No new schema needed** — reuse existing:
   - `Battle` — already has `trainer_a`, `trainer_b`, `winner`, `turn_history`
   - `TurnRecord` — already has `turn_number`, `actions`, `events`
   - `TurnEvent` — already has `fainted: bool`, `hp_delta`, `actor`

## Round Winner Logic

Calculate at XP distribution time:
- Look at each `TurnEvent` where `fainted: true`
- The Vibemon that caused the faint wins the round
- If no faint that round, it's a draw (no XP)

## Storage

- Serialize `Battle` (includes full turn history) as JSON
- Query: filter stored Battles by Vibemon ID appearing in team data
- Later: add linking table if queries become slow

## Priority: Low | Complexity: Low