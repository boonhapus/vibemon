# Vibemon

This document defines project-specific terms used in Vibemon code, docs, and product discussion.
It should only include terms whose meaning is not obvious from general software vocabulary.

## Language

**Vibemon**:
A generated creature with identity, stats, moves, lifecycle state, generated assets, and optional trainer ownership.

**Generation**:
The end-to-end process of creating a **Vibemon** from raw inputs, naming it, creating its assets, and assigning its initial disposition.
_Avoid_: Lifecycle

**Candidate**:
A generated **Vibemon** being reviewed by a **Trainer** before disposition is chosen.

**Generation Credit**:
A daily trainer allowance used to request candidate generation.

**Generation Credit Hold**:
A temporary reservation that prevents a trainer from running candidate generation in parallel.

**Candidate Review Timeout**:
The 24-hour limit after which an unresolved shown **Candidate** becomes **Wild**.

**Candidate Review**:
The temporary decision state for a shown **Candidate** before it resolves to **Owned** or **Wild**.

**Identity**:
The core species-level profile of a **Vibemon**.

**Element**:
A **Vibemon** type such as `fire`, `water`, or `ghost`.

**Provider**:
A module that captures raw external or user-context data and translates it into Vibemon-domain data.

**Birth**:
The deterministic creation of a schema-ready **Vibemon** from one or more provider affinities and a birth seed.

**Birth Seed**:
The reproducible input used to fetch provider payloads and seed deterministic birth subsystems.

**Birth Snapshot**:
Captured provider payloads from a birth seed.

**Lineage**:
An internal/debug view of the replayed provider affinities that contributed to a **Vibemon**.

**Affinity**:
A provider's synthesized contribution to a **Vibemon** birth.

**Intensity**:
A provider-supplied weight describing how strongly that provider's current payload should steer the merged **Vibemon**.

**Signal**:
A normalized real-world measurement used by a provider to score elements, stats, or intensity.

**Move**:
A battle action available to a **Vibemon**.

**Move Catalog**:
The persisted set of known moves.

**Effect**:
A declarative piece of move behavior such as status infliction, stat change, drain, recoil, weather, or healing.

**Battle Action**:
A typed command submitted to the battle engine for a turn.

**Christen**:
The lifecycle transition that gives a born **Vibemon** its finalized name and preview presentation.

**Manifest**:
The lifecycle transition that gives a christened **Vibemon** its full presentation.

**Adoption**:
The ownership assignment of a **Vibemon** to a **Trainer**.
_Avoid_: Lifecycle state

**Adoption Source**:
The origin of an **Adoption**, such as generated candidate acceptance or future wild catching.

**Catch**:
The wild-encounter action that attempts **Adoption** of a **Wild** **Vibemon**.
_Status_: Deferred for later design

**Owned**:
The disposition where a **Vibemon** is assigned to a **Trainer**.

**Release**:
The act of giving up trainer ownership of a **Vibemon**.
_Avoid_: Wild

**Wild**:
The disposition where a **Vibemon** is available outside trainer ownership.
_Avoid_: Released

**Wild Pool**:
The population of **Wild** **Vibemon** available for future encounters.

**Birth Context**:
The raw context used to generate a **Vibemon**, including its birth latitude and longitude.

**Wild Geography Bucket**:
A coarse geospatial grouping used to match trainers with geographically relevant **Wild** **Vibemon**.

**Wild Expiration**:
The removal of a **Wild** **Vibemon** from the game after it remains unencountered long enough.
_Avoid_: Lifecycle

**Expired**:
The non-playable disposition for a **Wild** **Vibemon** that left the game through **Wild Expiration**.

**Disposition**:
The ownership availability state of a **Vibemon**.
_Avoid_: Lifecycle

**Lifecycle**:
The asset-realization state of a **Vibemon**.
_Avoid_: Workflow, orchestration, generation

**Asset**:
A generated blob associated with a **Vibemon**, such as a sprite reference, sprite sheet, pose image, or battle cry.

**Asset Kind**:
The named slot for a **Vibemon** asset, such as `sprite/reference.png`, `sprite/sheet.png`, a pose image, or an audio cry.

**Asset Ref**:
The metadata handle for a stored asset blob.

**Pose**:
An extracted sprite image used for battle or emote presentation.

**Monstore**:
The object-store abstraction for **Vibemon** asset bytes.
_Avoid_: Provider

**Aesthetic**:
The visual and audio identity attached to a **Vibemon**, including derived colors and asset references.

**Trainer**:
A person or player entity that can own **Vibemon**.

**Party**:
The set of **Owned** **Vibemon** a **Trainer** can use in battle.
_Avoid_: Storage, box

**Battle Slot**:
One of the six positions in a **Trainer**'s **Party**.

**Battle Event**:
A typed event emitted by the battle engine while processing submitted battle actions.

**Battle Outcome**:
The final result of a battle.

**Defeat**:
The battle outcome where the trainer does not win and does not run.
_Avoid_: Loss, default

**Battle-Ready**:
The presentation readiness of a **Vibemon** that has the sprite assets needed for battle.

**Encounter Preparation**:
The service work that readies a **Wild** **Vibemon** for an encounter before battle presentation begins.

**Actual Encounter**:
A real player encounter with a **Wild** **Vibemon**.

**Encounter Weight**:
The relative likelihood that a **Wild** **Vibemon** is selected for a trainer encounter.

**Encounter Tuning Constant**:
A named numeric value used by encounter matching that is expected to change as balance data improves.

**Party Strength**:
The battle-readiness estimate derived from a **Trainer**'s full **Party**, including individual power and roster depth.

**Member Strength**:
The battle-readiness estimate for one **Vibemon**, derived from progression and stats.

**Encounter Reveal**:
The pre-battle presentation moment that introduces a **Wild** **Vibemon** before battle starts.

**Service**:
Application orchestration that coordinates use cases crossing domain rules, persistence, external generation, and presentation.
_Avoid_: Lifecycle

## Relationships

- **Generation** may include **Birth**, **Christen**, **Manifest**, and an initial **Disposition** such as **Owned** or **Wild**.
- A **Candidate** should be cheap enough to review before full manifestation cost is incurred.
- **Birth** produces a born **Vibemon** from provider **Affinities** and a **Birth Seed**.
- **Birth Context** anchors where a **Wild** **Vibemon** belongs geographically.
- A **Birth Snapshot** captures provider payloads used to derive **Affinities**.
- **Lineage** is derived from a **Birth Snapshot** and **Birth Seed**.
- A **Vibemon** has exactly one **Lifecycle** state.
- Current **Lifecycle** states are `born`, `christened`, and `manifested`.
- **Christen** transitions a born **Vibemon** toward preview presentation.
- **Manifest** transitions a christened **Vibemon** toward full presentation.
- A **Vibemon** is fully realized when it is manifested and all required generated assets exist.
- **Adoption** assigns at most one **Trainer** to a **Vibemon**, makes it **Owned**, and may trigger **Manifest**.
- **Adoption Source** distinguishes trainer acceptance of a generated **Candidate** from future wild catching.
- **Adoption** preserves existing core manifestation assets and does not regenerate them.
- **Adoption** clears or ignores trainer-specific encounter adjustments for the adopted **Vibemon**.
- **Adoption** removes a **Wild** **Vibemon** from global wild encounter eligibility immediately.
- Concurrent **Adoption** attempts for the same **Wild** **Vibemon** resolve first-success-wins.
- Losing a concurrent wild **Adoption** attempt is presented to the player as the Vibemon getting away.
- **Catch** is valid only during battle and only against **Wild** **Vibemon**.
- **Catch** mechanics are deferred for later design.
- The first implementation slice reserves **Catch** language only; it does not add catch APIs or service placeholders.
- Current **Battle Outcomes** are win, defeat, and run.
- Adopting one unresolved **Candidate** does not resolve any other unresolved **Candidates** for that trainer.
- A **Trainer**'s **Party** has six **Battle Slots**.
- A **Trainer** may own at most six **Vibemon** at this stage.
- There is no storage or box concept at this stage.
- If **Adoption** would exceed six **Battle Slots**, the trainer must **Release** one party **Vibemon**.
- Full-party **Adoption** is an atomic swap: **Release** one party **Vibemon**, adopt the new **Vibemon**, and assign the freed **Battle Slot** together.
- **Adoption** is not itself a **Lifecycle** state.
- **Release** removes trainer ownership from a **Vibemon** and makes it **Wild**.
- **Release** resets the **Wild Expiration** clock to the release time.
- **Release** starts fresh wild encounter weighting for the releasing trainer.
- **Release** preserves existing core manifestation assets.
- **Release** preserves progression, learned moves, and history.
- An **Owned** **Vibemon** has exactly one owning **Trainer**.
- A **Wild** **Vibemon** has no owning **Trainer**.
- The owning **Trainer** is assigned only by **Adoption**.
- A trainer may review multiple christened **Candidates** at the same time, up to their available daily **Generation Credits**.
- A **Candidate** under review is visible only to the reviewing trainer.
- **Candidate Review** is separate from **Disposition**.
- A shown **Candidate** is a real **Vibemon** row with identity and preview assets.
- **Candidate Review** metadata may live separately from the **Vibemon** row.
- **Candidate Review** records the reviewing **Trainer** without assigning ownership.
- A trainer has three **Generation Credits** per day.
- Trainer candidate generation is sequential; candidates are not generated in parallel.
- A trainer may have multiple unresolved **Candidates** under review.
- A trainer cannot run more than one candidate generation job at a time.
- A **Generation Credit Hold** is placed while candidate generation is running.
- A **Generation Credit** is consumed only when a christened **Candidate** is successfully shown.
- Failed candidate generation releases its **Generation Credit Hold** without consuming a **Generation Credit**.
- **Adoption** of a shown **Candidate** is free and does not consume another **Generation Credit**.
- A rejected **Candidate** becomes **Wild** rather than being discarded.
- An unresolved shown **Candidate** becomes **Wild** after the 24-hour **Candidate Review Timeout**.
- **Candidate Review Timeout** starts when the **Candidate** is successfully shown.
- **Candidate Review Timeout** is authoritative even if cleanup runs late.
- **Adoption** of a timed-out **Candidate** is rejected and first resolves the **Candidate** to **Wild**.
- The player-facing explanation for **Candidate Review Timeout** is that the Vibemon ran away.
- A **Candidate** enters the **Wild Pool** only after rejection or **Candidate Review Timeout**.
- A rejected **Candidate** may later be encountered by the rejecting trainer, but not immediately.
- Candidate rejection applies a trainer-specific encounter adjustment for the resulting **Wild** **Vibemon**.
- **Candidate Review Timeout** applies the same trainer-specific encounter adjustment as rejection.
- Candidate rejection and timeout start at `0.00x` encounter weight and continuously decay back to normal over a randomly assigned 1-3 day window.
- **Battle-Ready** **Vibemon** require battle sprite assets from the manifested sprite sheet.
- **Wild** can include trainer-rejected candidates whose birth and preview generation costs were already incurred.
- The **Wild Pool** is scoped by birth latitude and longitude.
- Wild encounter queries exclude **Candidate** review records and **Expired** Vibemon.
- Encounter services revalidate **Disposition** before final selection.
- **Wild Geography Buckets** are the primary eligibility mechanism for matching trainers to **Wild** **Vibemon**.
- Initial **Wild Geography Buckets** use geohash precision 5.
- Sparse areas may expand eligibility to neighboring **Wild Geography Buckets**.
- Encounter selection uses local bucket inventory first, then neighboring buckets, then new generation if supply remains thin.
- Encounter supply generation creates **Wild** **Vibemon** directly.
- Encounter supply generation creates christened **Wild** inventory by default.
- Encounter supply generation does not enter trainer **Candidate** review.
- Distance may influence **Encounter Weight** inside a **Wild Geography Bucket**.
- **Party Strength** influences wild encounter eligibility or **Encounter Weight**.
- **Party Strength** should be useful for both wild encounters and trainer-vs-trainer battles.
- **Party Strength** is derived from the **Member Strength** of all party **Vibemon**.
- **Member Strength** accounts for both level/progression and base-stat strength.
- Initial **Member Strength** is the sum of actual level-scaled HP, attack, defense, special attack, special defense, and speed.
- Initial **Party Strength** is average **Member Strength**, plus 25% of the highest **Member Strength**, plus 10% of total **Member Strength**.
- Wild 6v1 encounter matching compares a wild **Member Strength** against an initial target of 45% of the trainer's **Party Strength**.
- PvP matching compares **Party Strength** directly between trainers.
- The 45% wild target reduction applies only to wild 6v1 encounter matching.
- Wild encounter matching initially allows candidates from 70% to 140% of the wild target strength, weighted toward the target.
- Strength formula coefficients and variance bands are **Encounter Tuning Constants** and should be centralized as code constants for easy adjustment.
- Strength matching allows variance, including wild encounters the trainer may lose.
- Non-geographic provider context does not gate **Wild Pool** eligibility.
- **Wild Expiration** removes **Wild** **Vibemon** whose last actual encounter is older than 30 days.
- Any **Actual Encounter** resets the **Wild Expiration** clock, regardless of whether the **Vibemon** is adopted.
- **Wild Expiration** uses global **Actual Encounters**, not trainer-specific encounter adjustments.
- Losing to or running from a normal **Wild** encounter downweights that trainer's future **Encounter Weight** for the encountered **Vibemon**.
- Winning a normal **Wild** battle without adoption also downweights future encounter weight, but less than defeat or run.
- Normal **Wild** battle defeat or run uses the same trainer-specific encounter adjustment system as candidate rejection, with a higher starting multiplier.
- Initial wild encounter outcome multipliers are `0.30x` for run, `0.50x` for defeat, and `0.75x` for win without adoption.
- Wild encounter outcome downweights continuously decay back to normal over a randomly assigned 1-3 day window.
- For the same trainer/**Vibemon** pair, a new encounter adjustment replaces any previous active adjustment.
- Encounter adjustments are trainer-specific and do not affect other trainers.
- Wild encounter outcome downweights are **Encounter Tuning Constants**.
- **Wild Expiration** applies uniformly regardless of whether a **Wild** **Vibemon** came from candidate rejection or prior trainer ownership.
- A newly wild **Vibemon** uses its **Wild Pool** entry time as the initial encounter timestamp until its first actual encounter.
- **Wild Expiration** marks a **Vibemon** as **Expired** rather than immediately deleting its rows and assets.
- Asset cleanup after **Wild Expiration** is separate retention work.
- **Wild Expiration** is not a **Lifecycle** state.
- A **Wild** **Vibemon** may enter the **Wild Pool** while christened and become manifested lazily during **Encounter Preparation**.
- Background prewarming may opportunistically manifest likely **Wild** encounter candidates.
- **Encounter Preparation** must hide cold manifestation latency before the player-facing battle start.
- **Encounter Reveal** may hide manifestation latency with a silhouette slide-in or similar pre-battle animation.
- **Disposition** is a first-class domain fact, not just the absence of a **Trainer**.
- Playable **Disposition** is exactly **Owned** or **Wild**.
- **Expired** is a non-playable tombstone disposition.
- **Expired** is terminal for normal gameplay transitions.
- Under-review candidates do not use **Disposition** to represent review state.
- A **Vibemon** may have no gameplay **Disposition** only while an active **Candidate Review** exists.
- Resolving **Candidate Review** assigns **Owned** or **Wild**.
- Generation-in-progress is service/workflow state, not a **Disposition**.
- A **Service** may orchestrate **Generation**, **Birth**, **Christen**, **Manifest**, and **Adoption**, but it is not itself the **Lifecycle**.
- **Providers** do not own persistence, blob storage, trainer ownership, adoption, lifecycle orchestration, or frontend-facing API behavior.
- **Monstore** stores and retrieves asset bytes; it is not a **Provider**.
- Providers can publish **Moves** into the **Move Catalog**; battle code executes moves through the shared move/effect language rather than provider-specific logic.
- **Battle Events** are the battle system's frontend-consumable narration and state-change stream.

## Example dialogue

> **Dev:** "Does adoption make the Vibemon manifested?"
> **Domain expert:** "No. **Adoption** assigns a **Trainer**. A service may choose to trigger **Manifest**, but **Adoption** is not a **Lifecycle** state."

> **Dev:** "Is birth the whole generation process?"
> **Domain expert:** "No. **Birth** creates the schema-ready **Vibemon** from provider data. **Generation** is broader: it can include naming, asset creation, and the initial disposition."

> **Dev:** "Is a released Vibemon's state called released?"
> **Domain expert:** "No. **Release** is the action. The resulting disposition is **Wild**."

> **Dev:** "Why not manifest every generated Vibemon immediately?"
> **Domain expert:** "Because trainers review **Candidates** first. **Manifest** waits until a Vibemon needs to become battle-ready or fully presented."

> **Dev:** "Can we discard generated candidates the trainer rejects?"
> **Domain expert:** "No. A rejected **Candidate** becomes **Wild** because the system already paid to generate a known-good Vibemon from real user data."

> **Dev:** "Can trainer candidate generation run in parallel?"
> **Domain expert:** "No. The trainer may have multiple unresolved **Candidates**, but generation jobs run one at a time."

> **Dev:** "Can a trainer spend all daily generation credits in parallel?"
> **Domain expert:** "No. The trainer has three **Generation Credits** per day, but candidate generation runs sequentially."

> **Dev:** "Does a failed candidate generation consume a daily credit?"
> **Domain expert:** "No. Hold the credit while generation runs, then consume it only when a christened **Candidate** is shown."

> **Dev:** "What if the trainer leaves a shown candidate unresolved?"
> **Domain expert:** "After **Candidate Review Timeout**, the candidate becomes **Wild**; player-facing copy can say it ran away."

> **Dev:** "Does review timeout start when generation starts?"
> **Domain expert:** "No. The 24-hour **Candidate Review Timeout** starts when the **Candidate** is successfully shown."

> **Dev:** "Can a trainer adopt after the 24-hour deadline if cleanup has not run?"
> **Domain expert:** "No. The deadline is authoritative; late cleanup does not extend review."

> **Dev:** "Can other trainers encounter a candidate during its review timeout?"
> **Domain expert:** "No. A **Candidate** is private to the reviewing trainer until adoption, rejection, or timeout resolves it."

> **Dev:** "Can a trainer generate another candidate while one is still unresolved?"
> **Domain expert:** "Yes, up to their available daily **Generation Credits**, as long as candidate generation jobs do not run in parallel."

> **Dev:** "Does adopting a shown candidate spend another credit?"
> **Domain expert:** "No. **Adoption** of a shown **Candidate** is free."

> **Dev:** "Do encounter adjustments matter after the trainer adopts that Vibemon?"
> **Domain expert:** "No. **Adoption** clears or ignores trainer-specific encounter adjustments for that pair."

> **Dev:** "Can other trainers keep encountering a wild Vibemon after someone adopts it?"
> **Domain expert:** "No. **Adoption** makes it **Owned** and removes it from global wild encounter eligibility."

> **Dev:** "What if two trainers try to catch the same wild Vibemon?"
> **Domain expert:** "The first successful **Adoption** wins; other attempts fail because it got away."

> **Dev:** "If a trainer adopts one of several unresolved candidates, what happens to the others?"
> **Domain expert:** "Nothing automatically. Each **Candidate** remains unresolved until the trainer adopts it, rejects it, or it times out."

> **Dev:** "Can a trainer adopt a seventh battle Vibemon?"
> **Domain expert:** "Only by choosing one of their six party Vibemon to **Release**."

> **Dev:** "Can a trainer keep extra Vibemon in storage?"
> **Domain expert:** "No. At this stage, the six-slot **Party** is the trainer's full owned roster."

> **Dev:** "What happens if adoption requires releasing a current party Vibemon?"
> **Domain expert:** "The service performs an atomic swap so the trainer never owns seven Vibemon and never loses one without adopting the new one."

> **Dev:** "Can a christened wild Vibemon be selected for battle?"
> **Domain expert:** "Yes, but **Encounter Preparation** must manifest it before battle presentation starts."

> **Dev:** "What does the player see if a wild Vibemon needs cold manifestation?"
> **Domain expert:** "An **Encounter Reveal**, such as a silhouette slide-in, while the system prepares the battle-ready assets."

> **Dev:** "When does a wild Vibemon leave the game?"
> **Domain expert:** "Through **Wild Expiration** after 30 days without an actual encounter."

> **Dev:** "Do we delete an expired wild Vibemon immediately?"
> **Domain expert:** "No. **Wild Expiration** marks it **Expired**; asset cleanup happens separately."

> **Dev:** "Can a just-released Vibemon expire immediately because it had an old encounter timestamp?"
> **Domain expert:** "No. **Release** resets the **Wild Expiration** clock."

> **Dev:** "Can an expired Vibemon be encountered or adopted later?"
> **Domain expert:** "No. **Expired** is terminal for normal gameplay."

> **Dev:** "Is catching a wild Vibemon different from adopting a generated candidate?"
> **Domain expert:** "Both result in **Adoption**. The future **Catch** mechanic is only valid during battle against **Wild** Vibemon."

> **Dev:** "Should the first implementation add placeholder catch APIs?"
> **Domain expert:** "No. Reserve the language only until the **Catch** mechanic is designed."

> **Dev:** "Do we regenerate a wild Vibemon's assets when it is adopted?"
> **Domain expert:** "No. **Adoption** keeps existing core manifestation assets."

> **Dev:** "Do released Vibemon lose their manifested battle assets?"
> **Domain expert:** "No. **Release** keeps core manifestation assets and returns the Vibemon to the **Wild Pool** battle-ready if it was already manifested."

> **Dev:** "Does release reset a Vibemon's level or moves?"
> **Domain expert:** "No. **Release** preserves progression, learned moves, and history."

> **Dev:** "Can a new trainer encounter a released high-level wild Vibemon?"
> **Domain expert:** "Encounter matching accounts for **Party Strength**, with enough variance that stronger wild Vibemon can still appear."

> **Dev:** "Is party strength just average level?"
> **Domain expert:** "No. **Member Strength** should account for both level/progression and base-stat strength."

> **Dev:** "What is the first party strength formula?"
> **Domain expert:** "**Member Strength** is actual stat total; **Party Strength** is average member strength plus 25% of the strongest member plus 10% of total member strength."

> **Dev:** "Does one wild Vibemon need to equal the trainer's whole party strength?"
> **Domain expert:** "No. Wild 6v1 matching starts from a target of 45% of the trainer's **Party Strength**, with variance."

> **Dev:** "Does PvP use the wild encounter reduction?"
> **Domain expert:** "No. PvP compares **Party Strength** directly between trainers."

> **Dev:** "Can encounter selection query candidates or expired Vibemon and filter later?"
> **Domain expert:** "No. Query only eligible **Wild** Vibemon, then revalidate disposition before final selection."

> **Dev:** "Is under-review a Vibemon disposition?"
> **Domain expert:** "No. **Candidate Review** is separate state that resolves into **Owned** or **Wild**."

> **Dev:** "Is a shown candidate just a draft object?"
> **Domain expert:** "No. A shown **Candidate** is already a real **Vibemon** row; review metadata tracks the pending decision."

> **Dev:** "What disposition does an under-review candidate have?"
> **Domain expert:** "None yet. A missing gameplay **Disposition** is valid only while an active **Candidate Review** exists."

> **Dev:** "Does a candidate under review have trainer ownership?"
> **Domain expert:** "No. **Candidate Review** records the reviewing **Trainer**, but ownership is assigned only by **Adoption**."

> **Dev:** "Are the strength matching numbers permanent?"
> **Domain expert:** "No. Treat them as **Encounter Tuning Constants** so balance work can change them easily."

> **Dev:** "Do encounter tuning constants need admin-configurable storage now?"
> **Domain expert:** "No. Start with centralized code constants and move to config or admin data only when balance operations need it."

> **Dev:** "Does a wild encounter reset expiration if the player does not adopt the Vibemon?"
> **Domain expert:** "Yes. Any **Actual Encounter** resets the **Wild Expiration** clock."

> **Dev:** "Can trainer-specific downweighting make a wild Vibemon expire?"
> **Domain expert:** "No. **Wild Expiration** is based on global **Actual Encounters**."

> **Dev:** "Can a trainer encounter a candidate they rejected?"
> **Domain expert:** "Yes, but rejection should reduce or cool down that trainer's **Encounter Weight** for that Vibemon."

> **Dev:** "Does timeout get the same encounter cooldown as rejection?"
> **Domain expert:** "Yes. Timeout is a passive rejection for trainer-specific encounter weighting."

> **Dev:** "How long before a rejected candidate can reappear for that trainer?"
> **Domain expert:** "Use a trainer-specific cooldown of 1-3 days."

> **Dev:** "Is the rejection cooldown deterministic?"
> **Domain expert:** "No. Assign a random 1-3 day cooldown at rejection or timeout time and persist it."

> **Dev:** "Can a rejected candidate appear before the 1-3 day window finishes?"
> **Domain expert:** "Yes, but it starts at `0.00x` encounter weight and continuously decays back toward normal."

> **Dev:** "Does running from a wild encounter apply the rejection cooldown?"
> **Domain expert:** "It uses the same encounter adjustment system, but with a nonzero starting multiplier."

> **Dev:** "Should we call the non-winning battle outcome loss or default?"
> **Domain expert:** "No. Use **Defeat**."

> **Dev:** "Does winning against a wild Vibemon reduce repeat encounters?"
> **Domain expert:** "Yes, but less than defeat or run; the relative downweights are tuning constants."

> **Dev:** "What are the first wild encounter outcome multipliers?"
> **Domain expert:** "Start with `0.30x` for run, `0.50x` for defeat, and `0.75x` for win without adoption."

> **Dev:** "How long do normal wild encounter downweights last?"
> **Domain expert:** "Decay them back to normal over a randomly assigned 1-3 day window."

> **Dev:** "Do repeated encounter adjustments compound?"
> **Domain expert:** "No. The latest outcome replaces the previous active adjustment for that trainer and Vibemon."

> **Dev:** "Does one trainer rejecting or being defeated by a Vibemon affect everyone else's encounter odds?"
> **Domain expert:** "No. Encounter adjustments are trainer-specific."

> **Dev:** "Does the wild pool depend on all provider context?"
> **Domain expert:** "No. **Wild Pool** eligibility is geographically anchored by birth latitude and longitude; other provider context shaped the Vibemon but does not gate encounter eligibility."

> **Dev:** "Do wild encounters require an exact distance radius?"
> **Domain expert:** "No. **Wild Geography Buckets** provide the primary eligibility gate; distance can tune weighting inside the bucket."

> **Dev:** "How big is the first wild geography bucket?"
> **Domain expert:** "Start with geohash precision 5, expanding to neighboring buckets when local density is too low."

> **Dev:** "What happens if a local bucket has too few wild Vibemon?"
> **Domain expert:** "Search neighboring buckets first, then generate new candidates if wild supply is still thin."

> **Dev:** "Does encounter supply generation ask the trainer to review candidates?"
> **Domain expert:** "No. It creates **Wild** Vibemon directly for the encounter path."

> **Dev:** "Does encounter supply generation manifest every new wild Vibemon?"
> **Domain expert:** "No. It creates christened **Wild** inventory; manifestation waits for prewarm or **Encounter Preparation**."

## Flagged ambiguities

- "Lifecycle" previously referred both to asset-realization states and side-effecting generation workflows; resolved: **Lifecycle** is the state model, while **Service** owns orchestration.
- "Birth" was proposed for the end-to-end creation workflow; resolved: **Birth** is the deterministic creation step, while **Generation** is the broader end-to-end process.
- "Release" was proposed as the first-class non-owned disposition; resolved: **Wild** is the disposition, while **Release** is the action that gives up trainer ownership.
