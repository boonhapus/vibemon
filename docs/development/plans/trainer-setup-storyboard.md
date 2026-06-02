# Trainer Setup Storyboard

## Goal

Design the first-run trainer setup and revisitable Vibemon generation screens.
The flow should echo Pokemon FireRed / LeafGreen trainer creation pacing without
requiring an opponent/rival. It should feel like a handheld-era ritual translated
through Vibemon's 1960s-70s analog design language.

This document is UX and wireframe scope only. No API work is assumed.

## Design Anchors

- **Structure:** FireRed / LeafGreen intro rhythm: title prompt, professor-style
  welcome, trainer identity, confirmation, first creature generation, review.
- **Aesthetic:** Mid-century analog game UI from `docs/development/DESIGN.md`:
  cream panels, tobacco-brown text and borders, mustard selection cursors,
  avocado/burnt-orange supporting surfaces, visible grain, stepped transitions.
- **Domain language:** Use `Trainer`, `Generation`, `Birth Context`,
  `Provider`, `Candidate Review`, `Adoption`, `Wild`, and `Wild Pool`.
- **Boundary:** First-time setup creates the trainer identity and routes into
  Generation. Generation is also a normal revisitable screen after onboarding.

## Global Shell

The app shell should always reserve room for a status bar. Prefer bottom
placement for the handheld feel, with top placement acceptable on cramped mobile
views if bottom controls would collide.

```text
+--------------------------------------------------+
|                                                  |
|                 Current screen                    |
|                                                  |
+--------------------------------------------------+
|  04:28 PM LOCAL        WILD NEARBY: 12     MENU  |
+--------------------------------------------------+
```

Status bar requirements:

- Shows local time in the trainer's current timezone.
- Shows number of nearby Wild Vibemon.
- Uses compact labels and fixed-height layout so it never shifts page content.
- Can display degraded states: `TIME --:--`, `WILD NEARBY: ...`, or
  `LOCATION NEEDED`.
- Should support one optional right-side command slot, such as menu/settings.

## Flow Map

```text
Start Screen
  -> Intro Dialog
  -> Trainer Name
  -> Trainer Confirmation
  -> Generation Entry
  -> Provider Selection
  -> Birth Context Preview
  -> Generation In Progress
  -> Candidate Review
      -> Adopt first Vibemon -> Home / Party
      -> Reject candidate -> Provider Selection

Later navigation:
Home / Party / Map
  -> Generation Entry
  -> Provider Selection
  -> Candidate Review
```

## Screen 1: Start Screen

Purpose: Give the player a clear first action and establish the tactile retro
tone immediately.

```text
+--------------------------------------------------+
|                                                  |
|                 VIBEMON                          |
|             [ PRESS START ]                      |
|                                                  |
|       small animated grass/noise band             |
|                                                  |
+--------------------------------------------------+
|  04:28 PM LOCAL        WILD NEARBY: ...          |
+--------------------------------------------------+
```

Primary action: Start.

States:

- First visit: Start begins trainer setup.
- Returning trainer: Start opens the last active game surface.
- Loading: Start button becomes a small stepped pulse.

Transition: stepped iris open into the intro dialog.

## Screen 2: Intro Dialog

Purpose: Replace the Professor Oak intro with a Vibemon-native welcome. This is
not a tutorial page; it is a short ceremonial setup moment.

```text
+--------------------------------------------------+
|  [Professor/Guide portrait]                       |
|                                                  |
|  +--------------------------------------------+  |
|  | Welcome to the world of Vibemon.           |  |
|  | These creatures are born from the place,   |  |
|  | weather, time, and signals around you.  v  |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
|  04:29 PM LOCAL        WILD NEARBY: ...          |
+--------------------------------------------------+
```

Copy should be brief, one dialog box at a time. Suggested beats:

1. Welcome to Vibemon.
2. Vibemon are born from real-world signals.
3. The player is asked to identify as a Trainer.

Primary action: Advance dialog.

Secondary action: Skip after the first line for returning/dev users.

## Screen 3: Trainer Name

Purpose: Capture the Trainer's display name with the same simple clarity as the
classic "Are you a boy or girl?" / "What is your name?" sequence, but without
gender selection unless a later product decision adds avatar customization.

```text
+--------------------------------------------------+
|  GUIDE                                           |
|  +--------------------------------------------+  |
|  | First, what should other trainers call you? |  |
|  +--------------------------------------------+  |
|                                                  |
|      TRAINER NAME                               |
|      +------------------------------+           |
|      | ADA                          |           |
|      +------------------------------+           |
|                                                  |
|        [ OK ]        [ RANDOM ]                 |
+--------------------------------------------------+
|  04:30 PM LOCAL        WILD NEARBY: ...          |
+--------------------------------------------------+
```

Validation:

- Required.
- Trim leading/trailing whitespace.
- Show inline error in dialog style, not as a modern toast.
- Keep the input width stable across mobile and desktop.

Optional future extension: avatar palette or trainer sprite selection can slot
between name and confirmation without changing the rest of the flow.

## Screen 4: Trainer Confirmation

Purpose: Recreate the classic "Right! So your name is..." confirmation beat.

```text
+--------------------------------------------------+
|  GUIDE                                           |
|  +--------------------------------------------+  |
|  | Right. So your name is ADA?                |  |
|  +--------------------------------------------+  |
|                                                  |
|        +------------------------------+          |
|        | TRAINER CARD                 |          |
|        | NAME: ADA                    |          |
|        | LOCAL TIME: 04:30 PM         |          |
|        +------------------------------+          |
|                                                  |
|        [ YES ]       [ NO ]                      |
+--------------------------------------------------+
|  04:30 PM LOCAL        WILD NEARBY: ...          |
+--------------------------------------------------+
```

Primary action: Yes, continue to Generation.

Secondary action: No, return to Trainer Name with existing text preserved.

## Screen 5: Generation Entry

Purpose: Bridge setup into the reusable Generation screen. First run positions
this as "choose the signals for your first Vibemon." Later visits position it as
"generate another Vibemon."

```text
+--------------------------------------------------+
|  GENERATION LAB                                  |
|                                                  |
|  +--------------------------------------------+  |
|  | A Vibemon can be born from the signals     |  |
|  | around you. Choose which providers to use. |  |
|  +--------------------------------------------+  |
|                                                  |
|        [ CHOOSE PROVIDERS ]                      |
+--------------------------------------------------+
|  04:31 PM LOCAL        WILD NEARBY: 12           |
+--------------------------------------------------+
```

First-run primary action: Choose providers.

Returning primary action: Generate new Vibemon.

## Screen 6: Provider Selection

Purpose: Let the Trainer opt into sources that shape the new Vibemon. The list
must make availability clear without exposing backend plumbing.

```text
+--------------------------------------------------+
|  CHOOSE PROVIDERS                                |
|                                                  |
|  > [x] SKY        climate, weather, air           |
|    [x] GROUND     biome, water, elevation         |
|    [ ] MUSIC      listening history               |
|        LOCKED - LINK LAST.FM                      |
|                                                  |
|  Birth context                                   |
|    Location: Near you                             |
|    Time: 04:31 PM local                           |
|                                                  |
|        [ GENERATE ]       [ BACK ]                |
+--------------------------------------------------+
|  04:31 PM LOCAL        WILD NEARBY: 12           |
+--------------------------------------------------+
```

Provider cards:

- Climate: label as `Sky`; enabled by default when location is available.
- Biome: label as `Ground`; enabled by default when location is available.
- Music: label as `Music`; disabled until Last.fm is linked.

Rules:

- At least one provider must be selected.
- If location is unavailable, climate and biome become blocked with a
  `Location needed` action.
- If music is unavailable, keep it visible but locked so the Trainer understands
  it is an optional future signal.
- Provider descriptions should say what fantasy they add, not only what API they
  call.

## Screen 7: Birth Context Preview

Purpose: Confirm the seed-like inputs before the expensive generation moment.
This can be collapsed into Provider Selection for the first implementation, but
the storyboard keeps it separate because it is an important mental model.

```text
+--------------------------------------------------+
|  READY TO GENERATE?                              |
|                                                  |
|  +--------------------------------------------+  |
|  | Trainer: ADA                               |  |
|  | Time:    04:32 PM local                    |  |
|  | Place:   Current location                  |  |
|  | Signals: Sky, Ground                       |  |
|  +--------------------------------------------+  |
|                                                  |
|       [ BEGIN BIRTH ]      [ EDIT ]              |
+--------------------------------------------------+
|  04:32 PM LOCAL        WILD NEARBY: 12           |
+--------------------------------------------------+
```

Primary action: Begin Birth.

Secondary action: Edit returns to Provider Selection.

## Screen 8: Generation In Progress

Purpose: Make waiting feel intentional. Use a theatrical, analog animation
instead of a generic spinner.

```text
+--------------------------------------------------+
|                                                  |
|           SIGNALS TUNING                         |
|                                                  |
|        [ stepped oscilloscope / grass band ]      |
|                                                  |
|  +--------------------------------------------+  |
|  | The sky crackles. The ground answers.      |  |
|  +--------------------------------------------+  |
+--------------------------------------------------+
|  04:33 PM LOCAL        WILD NEARBY: 12           |
+--------------------------------------------------+
```

Progress beats:

- Reading local time and place.
- Tuning selected providers.
- Forming identity.
- Preparing candidate.

Failure handling:

- Provider Warning: birth completes but the Candidate Review shows a small
  warning ribbon.
- Blocking failure: return to Provider Selection with the failed provider
  highlighted and user-action copy.

## Screen 9: Candidate Review

Purpose: Present the generated Vibemon for accept/reject, matching the domain's
Candidate Review concept. This is the setup equivalent of choosing a starter,
but only one candidate is shown at a time.

```text
+--------------------------------------------------+
|  A VIBEMON APPEARED                              |
|                                                  |
|       [ sprite / reference silhouette ]           |
|                                                  |
|  +--------------------------------------------+  |
|  | NAME: MORPH                                |  |
|  | TYPE: WATER / GHOST                        |  |
|  | FROM: Sky + Ground                         |  |
|  | NOTE: born under fog near the river        |  |
|  +--------------------------------------------+  |
|                                                  |
|        [ ADOPT ]        [ RELEASE WILD ]          |
+--------------------------------------------------+
|  04:34 PM LOCAL        WILD NEARBY: 12           |
+--------------------------------------------------+
```

Primary action on first run: Adopt.

Secondary action: Release Wild / Reject. Avoid "delete"; rejected candidates
resolve to Wild when appropriate.

States:

- Born: text-first candidate with placeholder silhouette.
- Christened: name and reference presentation ready.
- Manifested: full sprite/assets ready.
- Provider Warning: compact ribbon below source line.
- Party full: adopt action leads to a release/swap decision later.

After adoption:

- First run routes to Home or Party.
- Returning generation routes back to the previous surface or Candidate Review
  result summary.

## Navigation Model

Top-level frontend routes can remain minimal:

```text
/                 start or resume
/setup            trainer setup sequence
/generate         reusable generation flow
/party            owned Vibemon roster
/wild             nearby wild / encounter entry
```

The first implementation can use one Svelte route with internal scene state if
that is faster for prototyping. Keep the domain concepts separated in component
names so the later route split is mechanical.

## Component Boundary Draft

```text
app/shell/
  AppShell.svelte
  GlobalStatusBar.svelte

domains/trainer/
  TrainerNameScene.svelte
  TrainerConfirmationScene.svelte
  trainerStore.svelte.ts

domains/generation/
  GenerationEntryScene.svelte
  ProviderSelectionScene.svelte
  BirthContextPreviewScene.svelte
  GenerationProgressScene.svelte
  CandidateReviewScene.svelte
  generationStore.svelte.ts

domains/vibemon/
  VibemonSummaryPanel.svelte
  TypeBadge.svelte

lib/ui/
  DialogBox.svelte
  MenuButton.svelte
  SelectionCursor.svelte
  SceneFrame.svelte
```

## Open Product Questions

- Should first-run rejection be allowed before the trainer owns any Vibemon, or
  should the first candidate require adoption?
- Should `Music` be shown during first-run setup if Last.fm is not linked, or
  hidden until account settings exist?
- Should the Birth Context Preview be a distinct screen or a confirmation panel
  inside Provider Selection for the first build?
- Does the global Wild Nearby count include all Wild Pool entries in the current
  geography bucket or only encounter-ready entries?

