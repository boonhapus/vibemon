# Vibemon Context

Canonical vocabulary for Vibemon domain conversations. This file defines meaning and boundaries for domain terms; implementation choices, tuning numbers, and rollout plans belong elsewhere.

## Language

**Vibemon**:
A generated creature with identity, progression, moves, lifecycle state, and ownership/disposition.

**Identity**:
The core species-level profile of a **Vibemon**.

**Generation**:
The end-to-end creation flow that produces a playable **Vibemon** candidate for review or encounter supply.
_Avoid_: Lifecycle

**Candidate**:
A generated **Vibemon** currently presented to one **Trainer** for accept/reject decision.
_Home_: `domains/adoption`

**Candidate Review**:
The temporary decision state for a shown **Candidate** before it resolves to **Owned** or **Wild**. May include **Provider Warnings** surfaced by the birth workflow.

**Provider Warning**:
A non-fatal signal from a **Provider** that birth completed but some inputs were thin or partial (for example low audio-analysis coverage for the **Music Provider**).
_Avoid_: Error, failure

**Candidate Review Timeout**:
The review deadline after which an unresolved shown **Candidate** resolves to **Wild**.

**Generation Credit**:
A trainer allowance consumed when a candidate is successfully shown.

**Generation Credit Hold**:
A temporary reservation preventing concurrent candidate generation for the same trainer.

**Trainer**:
A player entity that can own and battle with **Vibemon**.

**Party**:
The trainer's active roster of **Owned** **Vibemon** used in battle.
_Avoid_: Storage, box

**Battle Slot**:
A position in a trainer's **Party**.

**Owned**:
Disposition where a **Vibemon** is assigned to a **Trainer**.

**Wild**:
Disposition where a **Vibemon** has no owning trainer and is encounter-eligible.
_Avoid_: Released

**Expired**:
Non-playable disposition for a **Wild** **Vibemon** removed from normal encounter play.

**Disposition**:
The ownership-availability state of a **Vibemon**.
_Avoid_: Lifecycle

**Adoption**:
Ownership assignment of a **Vibemon** to a **Trainer**.
_Avoid_: Lifecycle state
_Home_: `domains/adoption`

**Adoption Source**:
The origin path that led to **Adoption** (for example candidate acceptance or wild catch flow).

**Release**:
The action that removes trainer ownership and returns a **Vibemon** to **Wild**.

**Catch**:
A battle-time wild encounter action that attempts **Adoption**.
_Status_: Deferred

**Wild Pool**:
The global population of encounter-eligible **Wild** **Vibemon**.

**Wild Expiration**:
The process that transitions stale encounter-inactive **Wild** **Vibemon** to **Expired**.

**Actual Encounter**:
A real player encounter event with a **Wild** **Vibemon**.

**Birth Context**:
The shared inputs every birth reproduces from: birth instant, place, and **Trainer** identity.
_Avoid_: Provider payloads, listening history, weather readings

**Wild Geography Bucket**:
A coarse geographic grouping used to select relevant **Wild** encounters.

**Encounter Preparation**:
Service work that makes a selected **Wild** **Vibemon** ready for player-facing battle presentation.

**Encounter Reveal**:
The pre-battle presentation moment introducing a **Wild** **Vibemon**.

**Encounter Weight**:
Relative likelihood that a **Wild** **Vibemon** is selected for a trainer encounter.

**Encounter Tuning Constant**:
A named balancing value used in encounter selection and matching.

**Member Strength**:
A single-**Vibemon** battle-readiness estimate.

**Party Strength**:
A roster-level battle-readiness estimate derived from a trainer's **Party**.

**Lifecycle**:
The asset/presentation realization state of a **Vibemon**.
_Avoid_: Workflow, orchestration, generation
_Home_: state and transition rules in `domains/vibemon`; christen/manifest realization in `vibemon/scripts`

**Birth**:
Deterministic creation of a schema-ready **Vibemon** from **Birth Context** and opted-in **Provider** contributions.
_Avoid_: Soundtrack of birth (evocative phrase, not a domain object)

**Provider**:
An opt-in birth-time signal source that captures a **Provider Observation** and synthesizes an **Affinity**.
_Home_: `app/providers`

**Music Provider**:
The personal-listening **Provider** (`provider_id="music"`) that derives an **Affinity** from a **Trainer**'s music taste at birth time.
_Avoid_: Sound provider, Spotify provider, soundtrack of birth

**Provider Observation**:
One **Provider**'s reduced capture at birth time, persisted for replay and dev tuning.
_Avoid_: Raw API response, snapshot payload

**Affinity**:
One **Provider**'s synthesized birth contribution—element leanings, stat signals, intensity, moves, and flavor—before merge into a **Vibemon** **Identity**.
_Home_: `domains/generation`

**Birth Snapshot**:
The persisted set of **Provider Observations** for one **Birth**.

**Christen**:
Lifecycle transition that finalizes name and preview presentation.

**Manifest**:
Lifecycle transition that produces full battle/presentation assets.

**Asset**:
A generated media artifact associated with a **Vibemon**.

**Asset Kind**:
A named asset slot (for example reference sprite, sheet sprite, pose, cry).

**Asset Ref**:
A metadata handle to stored asset bytes.

**Storage**:
Adapter code that persists or retrieves domain state and asset bytes. Storage is not a domain rule owner.

**Database Storage**:
ORM models, mappers, and repositories for durable gameplay state.
_Home_: `storage/database`

**Blob Storage**:
Object storage for media bytes and asset payloads.
_Home_: `storage/blob`

**Aesthetic**:
The visual/audio identity derived for a **Vibemon**.

**Pose**:
An extracted sprite image used for battle or emote presentation.

**Monstore**:
The object-store abstraction for **Vibemon** asset bytes.

**Solar Phase**:
The local time-of-day phase (dawn, day, dusk, night) derived from birth coordinates and timestamp.
_Avoid_: Time phase (ambiguous with battle turns or lifecycle)

**Element**:
A Vibemon type label (for example fire, water, ghost).

**Move**:
A battle action definition available to a **Vibemon**.

**Move Catalog**:
The persisted set of published, human-approved **Move** definitions.

**Effect**:
A declarative unit of move behavior.

**Battle Action**:
A typed command submitted for turn resolution.

**Battle Event**:
A frontend-consumable event emitted during battle resolution.

**Battle Outcome**:
The final result of a battle.

**Defeat**:
A **Battle Outcome** where the trainer neither wins nor runs.
_Avoid_: Loss, default

**Transition Policy**:
The explicit rules that define valid domain state transitions.

**Service**:
Application orchestration that coordinates domain rules, persistence, external generation, and presentation.
_Avoid_: Lifecycle
_Status_: Replaced by explicit workflow modules under `app/`

**Script Frontend**:
The near-term user-facing surface under `vibemon/scripts`; scripts are thin adapters over workflows or script-owned lifecycle realization.

## Relationships

- **Generation** may include **Birth**, **Christen**, **Manifest**, and initial **Disposition** assignment.
- **Candidate Review** is separate from **Disposition** and resolves to **Owned** or **Wild**.
- A **Vibemon** may have no gameplay **Disposition** only while an active **Candidate Review** exists.
- **Adoption** assigns ownership; **Release** removes ownership.
- **Catch** is an encounter-path action whose success results in **Adoption**.
- **Wild Pool** contains encounter-eligible **Wild** **Vibemon**; **Wild Expiration** transitions stale entries to **Expired**.
- **Party** is a trainer's battle roster composed of **Battle Slots**.
- **Party Strength** is derived from per-member **Member Strength**.
- **Lifecycle** states describe presentation readiness; **Service** describes orchestration.
- **Move Catalog** stores approved **Move** definitions composed of **Effect** primitives.
- **Birth** starts from **Birth Context**; each opted-in **Provider** adds a **Provider Observation** that synthesizes to an **Affinity**.
- **Birth Snapshot** holds all **Provider Observations** for one **Birth**; replay re-synthesizes **Affinities** without re-fetching upstream sources.
- **Provider Warnings** on an **Affinity** are non-fatal; the birth workflow may surface them during **Candidate Review**.

## Flagged ambiguities

- "Soundtrack of birth" is evocative marketing for the **Music Provider**, not a domain object—the listening fingerprint is a **Provider Observation**, not part of **Birth Context**.
- **Biome Provider** is the ground/place **Provider** (formerly referred to as geography in early plans); **Music Provider** is the taste/culture axis, not place or sky.
