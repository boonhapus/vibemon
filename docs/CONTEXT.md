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

**Candidate Review**:
The temporary decision state for a shown **Candidate** before it resolves to **Owned** or **Wild**.

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
The raw context captured at generation time, including geography used for wild eligibility.

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

**Birth**:
Deterministic creation of a schema-ready **Vibemon** from provider-derived inputs.

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

**Aesthetic**:
The visual/audio identity derived for a **Vibemon**.

**Pose**:
An extracted sprite image used for battle or emote presentation.

**Monstore**:
The object-store abstraction for **Vibemon** asset bytes.
_Avoid_: Provider

**Provider**:
A module that translates external or user-context signals into domain inputs.

**Signal**:
A normalized input measurement consumed by a **Provider**.

**Affinity**:
A provider-synthesized contribution used during **Birth**.

**Intensity**:
A provider-supplied strength indicator for how strongly its contribution should influence **Birth**.

**Birth Seed**:
A reproducible input used to derive deterministic birth outputs.

**Birth Snapshot**:
Captured provider payloads associated with a birth run.

**Lineage**:
An internal/debug view of provider contributions behind a generated **Vibemon**.

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

## Relationships

- **Generation** may include **Birth**, **Christen**, **Manifest**, and initial **Disposition** assignment.
- **Candidate Review** is separate from **Disposition** and resolves to **Owned** or **Wild**.
- A **Vibemon** may have no gameplay **Disposition** only while an active **Candidate Review** exists.
- **Adoption** assigns ownership; **Release** removes ownership.
- **Catch** is an encounter-path action whose success results in **Adoption**.
- **Wild Pool** contains encounter-eligible **Wild** **Vibemon**; **Wild Expiration** transitions stale entries to **Expired**.
- **Party** is a trainer's battle roster composed of **Battle Slots**.
- **Party Strength** is derived from per-member **Member Strength**.
- **Birth Seed**, **Birth Snapshot**, **Signal**, **Affinity**, and **Intensity** describe how **Providers** influence **Birth**.
- **Lifecycle** states describe presentation readiness; **Service** describes orchestration.
- **Move Catalog** stores approved **Move** definitions composed of **Effect** primitives.
