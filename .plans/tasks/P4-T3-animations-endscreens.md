# P4-T3 — Battle Animations & End Screens

**Phase:** 4 — Battle System
**Dependencies:** P4-T1, P4-T2
**Depends on this:** P5-T3

---

## Objective

Add hit/critical/faint animations to the Vibemon SVG wrappers and build the victory and defeat screens that conclude a battle.

## Tasks

1. **Hit shake animation**
   - When a Vibemon takes damage, apply CSS `@keyframes shake` to its SVG wrapper
   - Duration: 300ms
   - Horizontal displacement: ±5px
   - Trigger via a reactive flag in battle state (e.g. `player.isHit` / `enemy.isHit`)
   - Reset flag after animation completes

2. **Critical hit flash**
   - When type effectiveness ≥ 2.0 (super effective), apply a white flash overlay
   - Semi-transparent white rectangle over the SVG, 150ms fade-in then fade-out
   - Layer on top of the shake animation

3. **Faint animation**
   - When a Vibemon's HP reaches 0:
     - `translateY(30px)` + `opacity: 0` over 800ms with `ease-in`
     - After animation completes, transition battle phase to `'victory'` or `'defeat'`

4. **Move button press feedback**
   - Already using `Spring` from P4-T2, but ensure the visual feedback is snappy
   - Add a brief colour pulse on the button background matching the move's element

5. **Victory screen**
   - Displayed when `phase === 'victory'`
   - Player Vibemon scales up via `Spring` (1.0 → 1.2 → 1.0 bounce)
   - CSS particle burst effect (small coloured dots expanding outward)
   - Show "Victory!" text, player Vibemon name, and a summary:
     - Turns taken
     - Remaining HP
     - Most effective move used
   - "Play Again" button → navigate back to `/`

6. **Defeat screen**
   - Displayed when `phase === 'defeat'`
   - Subdued styling, enemy Vibemon remains visible
   - Show "Defeat" text and battle summary
   - "Try Again" button → navigate back to `/`

7. **Animation sequencing**
   - Ensure animations play in correct order: attack declared → damage calculated → hit animation → HP bar drain → KO check → faint animation → end screen
   - Use `await`-style delays or promise-based animation sequencing
   - Set `phase = 'animating'` during the sequence to prevent input

## Acceptance Criteria

- Hit shake is visible and correctly targets the damaged Vibemon
- Critical hits produce a white flash overlay
- Fainting Vibemon slides down and fades out before the end screen appears
- Victory screen shows with particle effect and spring-bounce on player Vibemon
- "Play Again" / "Try Again" buttons return to the landing page
- No input is accepted during animation sequences

## Files Modified

```
frontend/src/lib/components/VibemonRenderer.svelte  (add hit/faint props)
frontend/src/lib/stores/battle.ts  (animation flags, sequencing)
frontend/src/routes/battle/+page.svelte  (end screens, animation wiring)
```

## Files Created

```
frontend/src/lib/components/VictoryScreen.svelte
frontend/src/lib/components/DefeatScreen.svelte
```
