# Language

This document defines project-specific terms used in Vibemon code, docs, and product discussion.
It should only include terms whose meaning is not obvious from general software vocabulary.

## Vibemon

A generated creature with identity, stats, moves, lifecycle state, generated assets, and optional trainer ownership.

## Identity

The core species-level profile of a Vibemon.
Identity includes the generated name, elemental typing, base stats, evolution seed, radiant flag, visual notes, and generation metadata.

Identity is species-level even though Vibemon species are generated from birth seeds and may be near-unique.

## Element

A Vibemon type such as `fire`, `water`, or `ghost`.
Elements influence identity, move assignment, battle effectiveness, aesthetic colors, and provider affinity.

## Provider

A module that captures raw external or user-context data and translates it into Vibemon-domain data.
Providers produce affinities and may expose provider-authored moves for catalog seeding.

Providers do not own persistence, blob storage, trainer ownership, adoption, lifecycle orchestration, or frontend-facing API behavior.

Use "provider" for this role unless a more precise project term is introduced.

## Birth

The deterministic creation of a schema-ready Vibemon from one or more provider affinities and a birth seed.
Birth creates the creature's core identity, elements, stats, moves, evolution seed, and initial aesthetic colors.

Birth does not require generated media assets.

## Birth Seed

The reproducible input used to fetch provider payloads and seed deterministic birth subsystems.
Current seed material includes timestamp, geographic coordinates, and the selected providers.

## Birth Snapshot

Captured provider payloads from a birth seed.
A birth snapshot allows provider synthesis to be replayed without making new external API calls.

## Lineage

An internal/debug view of the replayed provider affinities that contributed to a Vibemon.
Lineage is derived from a birth snapshot and birth seed, and should not require fresh provider fetches.

## Affinity

A provider's synthesized contribution to a Vibemon birth.
An affinity can contribute identity, elements, stats, moves, visual notes, provider identity, and intensity.

## Intensity

A provider-supplied weight describing how strongly that provider's current payload should steer the merged Vibemon.
Intensity is clamped to the unit interval before merge.

## Signal

A normalized real-world measurement used by a provider to score elements, stats, or intensity.
Signals define raw, minimum, median, and maximum values so provider logic can map external data into Vibemon-domain ranges.

Signals are the standard design mechanism for constraining and translating raw provider data into the Vibemon data system.

## Move

A battle action available to a Vibemon.
Moves are authored as data: name, flavor text, type, category, power, accuracy, PP, priority, target, level requirement, effects, and optional behavior references.

## Move Catalog

The persisted set of known moves.
Providers can publish moves into the catalog; battle code executes moves through the shared move/effect language rather than provider-specific logic.

## Effect

A declarative piece of move behavior such as status infliction, stat change, drain, recoil, weather, or healing.
Effects describe what a move can do; battle rules interpret and apply them.

## Battle Action

A typed command submitted to the battle engine for a turn.
Current battle actions include move, switch, item, and run.

## Christen

The lifecycle step that finalizes a Vibemon's generated name and preview assets.
Current required christen assets are the sprite reference and battle cry.

## Manifest

The lifecycle step that realizes the full generated asset set from christened preview assets.
Current manifestation produces the sprite sheet and extracted pose assets.

## Adopt

The application action that assigns trainer ownership to a Vibemon.
Adoption signals that the system needs the additional owned/presentation assets to be created.

Adoption is not itself an asset lifecycle state.

## Lifecycle

The asset-realization state of a Vibemon.
Current lifecycle states are `born`, `christened`, and `manifested`.

## Asset

A generated blob associated with a Vibemon, such as a sprite reference, sprite sheet, pose image, or battle cry.
Asset metadata is represented separately from the stored bytes.

## Asset Kind

The named slot for a Vibemon asset, such as `sprite/reference.png`, `sprite/sheet.png`, a pose image, or an audio cry.
Asset kinds determine canonical object-store keys and content types.

## Asset Ref

The metadata handle for a stored asset blob.
An asset ref records the Vibemon id, asset kind, object key, content type, byte size, checksum, and asset version.

## Pose

An extracted sprite image used for battle or emote presentation.
Current poses are derived from the generated sprite sheet.

## Monstore

The object-store abstraction for Vibemon asset bytes.
Monstore stores and retrieves blobs; it is not a provider.

## Aesthetic

The visual and audio identity attached to a Vibemon, including derived colors and asset references.

## Trainer

A person or player entity that can own Vibemon.
Trainer semantics are project-specific and are not assumed to match map/exploration-centered monster-catching games.

## Battle Event

A typed event emitted by the battle engine while processing submitted battle actions.
Battle events are the battle system's frontend-consumable narration and state-change stream.

## Service

Application orchestration code that owns use-case boundaries.
Services coordinate persistence, transactions, providers, lifecycle workflows, generated assets, battle execution, and API-ready results.
