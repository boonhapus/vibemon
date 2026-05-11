# Monstore: Asset Storage + Vibemon Lifecycle Refactor

> Pickup doc. Self-contained. This supersedes the older sprite-store-only plan.

---

## Why this work exists

`backend/app/sprite_store.py` was built for one thing: persist a single
sprite-sheet PNG per Vibemon. That assumption now blocks the intended product
flow:

1. **Cost control**: preview should generate only the assets needed for a
   trainer to evaluate a Vibemon. The sprite sheet and pose split should happen
   only when the trainer adopts the Vibemon.
2. **Asset diversity**: Vibemon now needs multiple image and audio assets:
   reference art, sprite sheet, per-pose PNGs, battle cry, and reserved future
   faint/emote sounds.
3. **Production storage shape**: asset bytes belong in object storage, while
   the database should store stable object keys and metadata. Do not store
   inline bytes or presigned URLs in relational rows.
4. **Lifecycle clarity**: naming, preview asset generation, adoption, full
   manifestation, future evolution, trainer ownership, and wilderness state
   should live in explicit lifecycle orchestration rather than hidden Pydantic
   methods.

**Goal**: one asset store keyed by `<vibemon_uuid>/v1/<asset>`, a persisted
`vibemon_asset` metadata table, lifecycle functions for `christen()` and
`adopt()`, and an `Aesthetic` that holds only asset references.

---

## Current state

### `backend/app/sprite_store.py`

The current store is sheet-only, slug-keyed, and configured by
`settings.sprite_store_url`.

```python
SHEET_FILENAME = "sprite-sheet.png"

def sheet_key(vibemon_slug: str) -> str:
    return f"{vibemon_slug}/{SHEET_FILENAME}"

async def put_sheet(vibemon_slug: str, data: bytes) -> str: ...
async def get_sheet(key: str) -> bytes: ...
async def sheet_url(key, *, expires_in=dt.timedelta(hours=1)) -> str: ...
```

### `backend/app/genai/client.py`

`generate_vibemon_sprite()` currently performs the reference generation and
sheet generation in one call, so callers cannot stop after preview.

### `backend/app/schema.py`

`Aesthetic` currently mixes three storage shapes:

- `sprite_sheet_key: str | None`
- `sprites: SpriteLayout | None`
- `battle_cry: bytes | None`

`Vibemon` currently has no schema-level id, even though `models.Vibemon` has a
UUID primary key. That means generated asset keys cannot reliably align with DB
rows unless schema owns the canonical id first.

### `.scripts/vibemon_generator.py`

The generator currently uses `--headless` to skip full aesthetic rendering and
writes debug assets under `.scripts/generated/<name>/`, which can collide across
duplicate names or renamed Vibemon.

---

## Locked decisions

| Topic | Decision |
|---|---|
| Blob storage | Store bytes in object storage, not the DB. |
| DB metadata | Add a `vibemon_asset` child table with key, content metadata, checksum, and timestamps. |
| Object key | `<vibemon_uuid>/v1/<asset-path>` using `str(uuid.UUID)`. |
| Asset URLs | Store object keys, not signed URLs. Generate URLs on demand. |
| Package boundary | Add `backend/app/data_store/` for object-store APIs and asset persistence helpers. |
| `types/schema/const/models` convention | Follow `.agents/AGENTS.md`: types are vocabularies, schema is Pydantic data, const is fixed values/lookups, models is SQLAlchemy shape. |
| `AssetKind` | Lives in `app.data_store.types`; values are relative paths with extensions. |
| Static lookup tables | Live in `app.data_store.const`. |
| `AssetRef` | Lives in `app.data_store.schema`; rich metadata object returned by `monstore.put()`. |
| Aesthetic assets | `dict[AssetKind, AssetRef]`, not inline bytes or bare strings. |
| `Aesthetic` ownership | Normal optional/field data object, no private `_vibemon` back-reference. |
| Schema base | Replace `_Static` / `_Transient` with public `Schema` and `FrozenSchema`. |
| Frozen value objects | Keep frozen only where value semantics matter: moves/effects/conditions, birth seed/snapshot, battle actions/events/results. |
| Move identity | `Move` remains effectively frozen and name-identified; `BattleMove` is the mutable runtime version. |
| Lifecycle package | Add `backend/app/lifecycle/`; no async I/O lifecycle methods on `schema.Vibemon`. |
| Lifecycle states | `born`, `christened`, `manifested`. |
| Preview contract | `christen()` finalizes name, then generates/stores `REFERENCE` and `CRY_BATTLE`. |
| Adoption contract | `adopt(trainer_id)` assigns trainer ownership and manifests full assets. |
| Manifested contract | Requires `REFERENCE`, `CRY_BATTLE`, `SHEET`, and all 9 pose assets. |
| Trainer ownership | Add nullable `trainer_id`; wild/owned is derived from `trainer_id is None`. |
| Trainer persistence | Add minimal `models.Trainer`; `models.Vibemon.trainer_id` is nullable FK with `SET NULL`. |
| Script stages | Replace `--headless` with `--stage preview|adopt`. |
| Cleanup | Add a conservative local cleanup script; dry-run by default, delete only with `--apply`. |

---

## Target package layout

```text
backend/app/
  data_store/
    __init__.py
    types.py      # AssetKind
    const.py      # ASSET_VERSION, POSE_TO_ASSET, required asset sets, MIME map
    schema.py     # AssetRef
    monstore.py   # object-store put/get/url helpers
    assets.py     # DB helper mapping AssetRef <-> models.VibemonAsset
  lifecycle/
    __init__.py
    vibemon.py    # christen, manifest, adopt; future evolution hooks
  models.py       # SQLAlchemy table declarations
  schema.py       # Pydantic domain data objects
  types.py        # domain enums/type aliases
  const.py        # domain fixed values/lookups
```

Do not move existing `app.models` into `data_store` during this refactor. Keep
SQLAlchemy declarations centralized to avoid broad import churn.

---

## Data-store contract

### `backend/app/data_store/types.py`

```python
import enum


class AssetKind(enum.StrEnum):
    REFERENCE = "sprite/reference.png"
    SHEET = "sprite/sheet.png"

    POSE_BATTLE_BACK = "pose/battle-back.png"
    POSE_BATTLE_HERO = "pose/battle-hero.png"
    POSE_BATTLE_OPPONENT = "pose/battle-opponent.png"
    POSE_EMOTE_RESTING = "pose/emote-resting.png"
    POSE_EMOTE_HAPPY = "pose/emote-happy.png"
    POSE_EMOTE_FRUSTRATED = "pose/emote-frustrated.png"
    POSE_EMOTE_PROUD = "pose/emote-proud.png"
    POSE_EMOTE_CONFUSED = "pose/emote-confused.png"
    POSE_EMOTE_SAD = "pose/emote-sad.png"

    CRY_BATTLE = "audio/cry-battle.mp3"
    CRY_FAINT = "audio/cry-faint.mp3"

    SOUND_EMOTE_RESTING = "audio/emote-resting.mp3"
    SOUND_EMOTE_HAPPY = "audio/emote-happy.mp3"
    SOUND_EMOTE_FRUSTRATED = "audio/emote-frustrated.mp3"
    SOUND_EMOTE_PROUD = "audio/emote-proud.mp3"
    SOUND_EMOTE_CONFUSED = "audio/emote-confused.mp3"
    SOUND_EMOTE_SAD = "audio/emote-sad.mp3"
```

Reserved faint/emote sound kinds are included now, but they are not required for
`manifested` until generators exist.

### `backend/app/data_store/const.py`

```python
ASSET_VERSION = "v1"
UNSIGNABLE_SCHEMES = frozenset({"file", "memory"})

POSE_TO_ASSET = {
    app_types.PoseT.BATTLE_BACK: AssetKind.POSE_BATTLE_BACK,
    app_types.PoseT.BATTLE_HERO: AssetKind.POSE_BATTLE_HERO,
    app_types.PoseT.BATTLE_OPPONENT: AssetKind.POSE_BATTLE_OPPONENT,
    app_types.PoseT.EMOTE_RESTING: AssetKind.POSE_EMOTE_RESTING,
    app_types.PoseT.EMOTE_HAPPY: AssetKind.POSE_EMOTE_HAPPY,
    app_types.PoseT.EMOTE_FRUSTRATED: AssetKind.POSE_EMOTE_FRUSTRATED,
    app_types.PoseT.EMOTE_PROUD: AssetKind.POSE_EMOTE_PROUD,
    app_types.PoseT.EMOTE_CONFUSED: AssetKind.POSE_EMOTE_CONFUSED,
    app_types.PoseT.EMOTE_SAD: AssetKind.POSE_EMOTE_SAD,
}

ASSET_CONTENT_TYPES = {
    AssetKind.REFERENCE: "image/png",
    AssetKind.SHEET: "image/png",
    # all pose kinds: "image/png"
    AssetKind.CRY_BATTLE: "audio/mpeg",
    # all MP3 kinds: "audio/mpeg"
}

REQUIRED_CHRISTEN_ASSETS = frozenset({
    AssetKind.REFERENCE,
    AssetKind.CRY_BATTLE,
})

REQUIRED_MANIFEST_ASSETS = frozenset({
    AssetKind.REFERENCE,
    AssetKind.CRY_BATTLE,
    AssetKind.SHEET,
    AssetKind.POSE_BATTLE_BACK,
    AssetKind.POSE_BATTLE_HERO,
    AssetKind.POSE_BATTLE_OPPONENT,
    AssetKind.POSE_EMOTE_RESTING,
    AssetKind.POSE_EMOTE_HAPPY,
    AssetKind.POSE_EMOTE_FRUSTRATED,
    AssetKind.POSE_EMOTE_PROUD,
    AssetKind.POSE_EMOTE_CONFUSED,
    AssetKind.POSE_EMOTE_SAD,
})
```

Use explicit MIME lookups instead of `mimetypes`; the enum is controlled and
small.

### `backend/app/data_store/schema.py`

```python
class AssetRef(pydantic.BaseModel):
    vibemon_id: uuid.UUID
    kind: types.AssetKind
    key: str
    content_type: str
    byte_size: int
    sha256: str
    version: str = const.ASSET_VERSION
```

Do not include DB timestamps in `AssetRef`. Blob write metadata and DB upsert
timestamps are related but not identical.

### `backend/app/data_store/monstore.py`

```python
@lru_cache(maxsize=1)
def _store() -> ObjectStore:
    return from_url(settings.asset_store_url)


def asset_key(vibemon_id: uuid.UUID, kind: types.AssetKind) -> str:
    return f"{vibemon_id}/{const.ASSET_VERSION}/{kind.value}"


async def put(
    vibemon_id: uuid.UUID,
    kind: types.AssetKind,
    data: bytes,
    *,
    content_type: str | None = None,
) -> schema.AssetRef:
    key = asset_key(vibemon_id, kind)
    await obstore.put_async(_store(), key, data)
    return schema.AssetRef(
        vibemon_id=vibemon_id,
        kind=kind,
        key=key,
        content_type=content_type or const.ASSET_CONTENT_TYPES[kind],
        byte_size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        version=const.ASSET_VERSION,
    )
```

Rules:

- `put()` accepts only `AssetKind`, not arbitrary paths.
- Do not read-after-write in the normal path. Trust successful
  `obstore.put_async`.
- `get(key)` returns bytes.
- `url(key)` returns a URL string: direct `file://.../<key>` for local stores,
  `memory:///.../<key>` for memory stores, signed URL for remote stores.

### `backend/app/data_store/assets.py`

DB helper responsibilities:

- Convert `AssetRef` objects to `models.VibemonAsset` rows.
- Upsert idempotently by `(vibemon_id, version, kind)`.
- Preserve `created_at` on update.
- Update `object_key`, `content_type`, `byte_size`, `sha256`, and `updated_at`.

The object blob is written before the DB row. If DB persistence fails, an
orphan blob is acceptable and retry-safe. A DB row pointing at a missing blob is
worse and should be reported by integrity checks.

---

## Settings

Rename:

```python
sprite_store_url: str = "file://./.generated/sprites"
```

to:

```python
asset_store_url: str = "file://./.generated/monstore"
```

Update the validator name and docs, but keep the behavior: relative `file://`
paths anchor at the repo root and are created if missing.

---

## Domain types

### `backend/app/types.py`

Drop `SpriteLayout`. Add:

```python
class PoseT(enum.StrEnum):
    BATTLE_BACK = "battle_back"
    BATTLE_HERO = "battle_hero"
    BATTLE_OPPONENT = "battle_opponent"
    EMOTE_RESTING = "emote_resting"
    EMOTE_HAPPY = "emote_happy"
    EMOTE_FRUSTRATED = "emote_frustrated"
    EMOTE_PROUD = "emote_proud"
    EMOTE_CONFUSED = "emote_confused"
    EMOTE_SAD = "emote_sad"


class VibemonLifecycleT(enum.StrEnum):
    BORN = "born"
    CHRISTENED = "christened"
    MANIFESTED = "manifested"
```

Use nullable `trainer_id` for ownership. Do not add an ownership enum now.
Wild/owned is derived:

```python
is_wild = trainer_id is None
is_owned = trainer_id is not None
```

---

## Schema model changes

### Base classes

Replace `_Static` and `_Transient` with:

```python
class Schema(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )


class FrozenSchema(Schema):
    model_config = pydantic.ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
        frozen=True,
    )
```

Use `Schema` by default. Use `FrozenSchema` only for stable value/definition
objects:

- `BirthSeed`
- `BirthSnapshot`
- `Move`
- `MoveBehavior`
- `EffectGroup`
- individual effect and condition objects
- battle action command objects
- battle event/result log objects

`Move` remains effectively frozen and name-identified. `BattleMove` remains the
mutable runtime version that layers battle state over a move definition.

### `Identity`

Update the docstring. It is not immutable anymore.

```python
class Identity(Schema):
    """Represents the core identity and battle profile of a Vibemon."""
```

Lifecycle code may finalize `identity.name` and future evolution may update
identity state. Do not infer christening from `identity.name`, because provider
merge already supplies a name before christening.

### `Affinity`

Keep mutable under `Schema`. Change:

```python
moves: list[Move]
```

to:

```python
moves: tuple[Move, ...]
```

The generated learnset is a snapshot. Providers may still build lists, but
schema boundaries should coerce to tuples.

### `Trainer`

Align schema with DB identity:

```python
class Trainer(Schema):
    id: types.TrainerIdT = pydantic.Field(default_factory=uuid.uuid7)
    username: str
    team: list[Vibemon] = pydantic.Field(default_factory=list)
```

### `Aesthetic`

Target shape:

```python
class Aesthetic(Schema):
    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color
    assets: dict[data_store_types.AssetKind, data_store_schema.AssetRef] = pydantic.Field(default_factory=dict)

    def has(self, kind: data_store_types.AssetKind) -> bool: ...
    async def url_for(self, kind: data_store_types.AssetKind, *, expires_in: dt.timedelta = dt.timedelta(hours=1)) -> str | None: ...
    async def bytes_for(self, kind: data_store_types.AssetKind) -> bytes | None: ...

    @classmethod
    def from_vibemon(cls, vibemon: Vibemon) -> Self:
        # derive colors only; no I/O
```

Rules:

- Drop `_vibemon`.
- Drop `_unwrap_sprite_sheet`.
- Drop `sprites`, `battle_cry`, and `sprite_sheet_key`.
- `url_for()` and `bytes_for()` use known `AssetRef`s only. Do not silently
  derive deterministic keys when refs are absent.

### `Vibemon`

Target additions:

```python
class Vibemon(Schema):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid7)
    trainer_id: types.TrainerIdT | None = None
    lifecycle: types.VibemonLifecycleT = types.VibemonLifecycleT.BORN
    aesthetic: Aesthetic | None = None
```

`Vibemon.birth()` should generate the canonical id and initialize
`aesthetic=Aesthetic.from_vibemon(instance)` because color derivation is pure and
cheap. The asset map remains empty until christening.

`Vibemon.rebirth()` should reset aesthetic assets and lifecycle. Current
no-network rebirth should leave the Vibemon `BORN` because it does not generate
new preview assets.

Remove `Vibemon.christen()` and `Vibemon.render_aesthetic()` methods. New code
uses lifecycle functions.

---

## SQLAlchemy model changes

### `models.Trainer`

Add:

```python
class Trainer(Base):
    __tablename__ = "trainer"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    username: Mapped[str] = mapped_column(unique=True)

    vibemons: Mapped[list["Vibemon"]] = relationship(back_populates="trainer")
```

### `models.Vibemon`

Add:

```python
trainer_id: Mapped[uuid.UUID | None]
lifecycle: Mapped[str]
```

Preserve schema id when persisting:

```python
models.Vibemon(id=vibemon.id, ...)
```

Add FK:

```python
ForeignKeyConstraint(
    ["trainer_id"],
    ["trainer.id"],
    name="fk_vibemon_trainer",
    ondelete="SET NULL",
)
```

Add relationships:

```python
trainer: Mapped["Trainer | None"] = relationship(back_populates="vibemons")
assets: Mapped[list["VibemonAsset"]] = relationship(
    back_populates="vibemon",
    cascade="all, delete-orphan",
    single_parent=True,
)
```

### `models.VibemonAsset`

Add:

```python
class VibemonAsset(Base):
    __tablename__ = "vibemon_asset"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid7)
    vibemon_id: Mapped[uuid.UUID]
    kind: Mapped[str]
    version: Mapped[str]
    object_key: Mapped[str] = mapped_column(unique=True)
    content_type: Mapped[str]
    byte_size: Mapped[int]
    sha256: Mapped[str]
    created_at: Mapped[dt.datetime]
    updated_at: Mapped[dt.datetime]

    __table_args__ = (
        ForeignKeyConstraint(["vibemon_id"], ["vibemon.id"], name="fk_vibemon_asset_vibemon", ondelete="CASCADE"),
        sa.UniqueConstraint("vibemon_id", "version", "kind", name="uq_vibemon_asset_slot"),
    )

    vibemon: Mapped["Vibemon"] = relationship(back_populates="assets")
```

Use UTC timestamps in Python when creating/updating rows. The repo currently
uses `metadata.create_all`, not migrations, so existing DB compatibility is a
separate concern.

---

## GenAI split

Replace `generate_vibemon_sprite()` with:

```python
async def generate_sprite_reference(vibemon: schema.Vibemon) -> bytes:
    p = utils.load_prompt("sprite-reference.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run(p)
    return app_utils.normalize_sprite_matte(
        r.output.data,
        bg_color=vibemon.aesthetic.background_color,
        rows=1,
        cols=1,
    )


async def generate_sprite_sheet(vibemon: schema.Vibemon, reference: bytes) -> bytes:
    p = utils.load_prompt("sprite-sheet.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run([
        pydantic_ai.BinaryImage(data=reference, media_type="image/png"),
        p,
    ])
    d = app_utils.normalize_sprite_matte(r.output.data, bg_color=vibemon.aesthetic.background_color)
    if issues := app_utils.validate_sprite_sheet(d):
        raise RuntimeError(f"Generated sprite sheet failed validation: {'; '.join(issues)}")
    return d
```

Keep `generate_battle_cry()` but move when it is called: christening now
generates battle cry for the preview contract.

---

## Sprite extraction

`utils.extract_sprites()` returns `dict[types.PoseT, Image.Image]`.

The old `"sheet"` key goes away. Sheet bytes are stored in
`AssetKind.SHEET`; poses are stored individually.

---

## Lifecycle

Create `backend/app/lifecycle/vibemon.py`.

### `christen(vibemon)`

Responsibilities:

1. If lifecycle is already `CHRISTENED` or `MANIFESTED` and required preview
   assets exist, return the same object.
2. Generate the final name first if lifecycle is `BORN`.
3. Ensure `vibemon.aesthetic` exists.
4. Generate `REFERENCE` and `CRY_BATTLE` concurrently.
5. Store both via `monstore.put()`.
6. Populate `vibemon.aesthetic.assets`.
7. Set lifecycle to `CHRISTENED` only after both required preview assets exist.

If name generation succeeds but asset generation fails, keep lifecycle `BORN`.
Retry should be safe and can overwrite/fill deterministic asset slots.

### `manifest(vibemon)`

Internal asset-realization primitive. It does not assign ownership.

Responsibilities:

1. Require lifecycle `CHRISTENED` or `MANIFESTED`.
2. Require `REFERENCE` and `CRY_BATTLE` refs.
3. Read reference bytes from monstore.
4. Generate `SHEET`.
5. Store `SHEET`.
6. Extract 9 poses from sheet.
7. Store each pose PNG using `const.POSE_TO_ASSET`.
8. Set lifecycle `MANIFESTED` only after `REQUIRED_MANIFEST_ASSETS` are present.

`manifested` means full required v1 assets exist. Partial generation is allowed
as recoverable state, but lifecycle stays `CHRISTENED` until complete.

### `adopt(vibemon, trainer_id)`

Public adoption transition:

```python
async def adopt(vibemon: schema.Vibemon, trainer_id: types.TrainerIdT) -> schema.Vibemon:
    # Future trainer ownership/workflow logic belongs here.
    vibemon.trainer_id = trainer_id
    await manifest(vibemon)
    return vibemon
```

Comment this function to signal future ownership intent: trainer persistence,
party/box placement, wilderness removal, and async manifestation can land here
without changing the call site.

---

## Persistence flow

Schema/lifecycle functions do not own database sessions.

When persisting a generated Vibemon:

1. Object blobs are already written by lifecycle functions.
2. The caller with an `AsyncSession` inserts/updates `models.Vibemon`.
3. The caller persists current `AssetRef`s to `models.VibemonAsset` rows through
   `data_store.assets`.
4. Commit the Vibemon row and current asset rows in one DB transaction.

For preview stage, persisted rows should have:

- `trainer_id=None`
- `lifecycle="christened"`
- asset rows for `REFERENCE` and `CRY_BATTLE`

For adopt stage, persisted rows should have:

- `trainer_id=<trainer id>`
- `lifecycle="manifested"`
- asset rows for all required manifest assets

During `rebirth_all_vibemon`:

- Delete existing `VibemonAsset` child rows.
- Reset lifecycle to `BORN` unless the script explicitly rechristens.
- Leave old blobs in object storage as cleanup-script candidates.

---

## Script updates

### `.scripts/vibemon_generator.py`

Replace `--headless` with:

```text
--stage preview
--stage adopt
--trainer-username "Script Trainer"
```

Default: `--stage preview`.

Behavior:

- `preview`: birth + christen, no trainer, no manifestation.
- `adopt`: birth + christen + query/create trainer by username + adopt/manifest.

Use one stable default trainer per DB:

```text
username = "Script Trainer"
```

### Asset dump

Rename the old `write_aesthetic_to_disk()` to `dump_vibemon_assets()`.

Write debug dumps under UUID folders, not names:

```text
.scripts/generated/<vibemon_uuid>/
  name.txt
  sprite/reference.png
  sprite/sheet.png
  pose/battle-back.png
  audio/cry-battle.mp3
```

`name.txt` should contain:

```text
id: <uuid>
name: <display name>
lifecycle: <born|christened|manifested>
```

Rules:

- Preserve asset subdirectories from `AssetKind.value`.
- Overwrite current files.
- Do not delete stale files by default.
- If `aesthetic` is missing, raise a clear error.
- If assets are empty, still write `name.txt`.

---

## Cleanup script

Add:

```text
.scripts/cleanup_monstore.py
```

Initial scope: local `file://` stores only.

Behavior:

- Dry-run by default.
- Require `--apply` to delete.
- Accept `--older-than-hours 24` to avoid deleting fresh previews.
- Compare top-level UUID folders against `models.Vibemon.id`.
- Report UUID folders with no DB Vibemon row as orphan preview/deleted-Vibemon
  candidates.
- Report blobs under valid Vibemon UUID folders with no matching
  `VibemonAsset.object_key` as stale asset candidates.
- Delete orphan/stale blobs only when `--apply` is passed.
- Report DB asset rows whose blobs are missing as integrity errors. Do not
  delete those DB rows automatically.

Remote store cleanup can be added later if/when listing/deletion behavior is
needed for S3/GCS/Azure.

---

## Files at a glance

| File | Action |
|---|---|
| `backend/app/data_store/__init__.py` | New package marker |
| `backend/app/data_store/types.py` | New `AssetKind` |
| `backend/app/data_store/const.py` | New asset version, mappings, required sets |
| `backend/app/data_store/schema.py` | New `AssetRef` |
| `backend/app/data_store/monstore.py` | New object-store API replacing `sprite_store.py` |
| `backend/app/data_store/assets.py` | New DB asset upsert helpers |
| `backend/app/lifecycle/__init__.py` | New lifecycle package marker |
| `backend/app/lifecycle/vibemon.py` | New `christen`, `manifest`, `adopt` |
| `backend/app/sprite_store.py` | Delete |
| `backend/app/settings.py` | Rename `sprite_store_url` to `asset_store_url` |
| `backend/app/types.py` | Drop `SpriteLayout`; add `PoseT`, `VibemonLifecycleT` |
| `backend/app/utils.py` | `extract_sprites` returns `dict[PoseT, Image]` |
| `backend/app/genai/client.py` | Split reference and sheet generation |
| `backend/app/schema.py` | Add `Schema`/`FrozenSchema`, ids, lifecycle, trainer_id, new `Aesthetic` |
| `backend/app/models.py` | Add `Trainer`, `VibemonAsset`, lifecycle/trainer fields |
| `.scripts/vibemon_generator.py` | New stages, trainer creation, asset persistence, UUID dump |
| `.scripts/cleanup_monstore.py` | New local cleanup script |
| `.agents/skills/development/frontend-design/SKILL.md` | Update stale `sprite_store` references if present |
| `backend/tests/test_determinism.py` | Update for schema base, tuple moves, lifecycle defaults if needed |

---

## Reused functions

- `obstore.put_async`, `get_async`, `sign_async`
- `app.utils.normalize_sprite_matte`
- `app.utils.validate_sprite_sheet`
- `app.utils.extract_sprites`
- Current local-store anchoring behavior from `settings.py`
- Current unsigned URL behavior from `sprite_store.py`
- `uuid.uuid7` for schema and DB ids

---

## Lifecycle: before vs after

```text
BEFORE:
  birth()
    -> christen()              # LLM name only
    -> render_aesthetic()      # reference + sheet + cry

AFTER:
  birth()
    -> lifecycle.christen()    # final name + REFERENCE + CRY_BATTLE
    -> lifecycle.adopt()       # trainer_id + manifest full assets
         -> manifest()         # SHEET + 9 POSES
```

Preview/adoption split:

```text
preview assets:
  sprite/reference.png
  audio/cry-battle.mp3

adoption/manifest assets:
  sprite/sheet.png
  pose/battle-back.png
  pose/battle-hero.png
  pose/battle-opponent.png
  pose/emote-resting.png
  pose/emote-happy.png
  pose/emote-frustrated.png
  pose/emote-proud.png
  pose/emote-confused.png
  pose/emote-sad.png
```

---

## Verification

1. **Determinism harness**

   ```text
   cd backend && uv run pytest tests/test_determinism.py
   ```

2. **Preview script smoke**

   ```text
   uv run .scripts/vibemon_generator.py --stage preview --count 1
   ```

   Confirm:

   - DB row has lifecycle `christened`.
   - `trainer_id` is null.
   - `vibemon_asset` has `REFERENCE` and `CRY_BATTLE`.
   - `.generated/monstore/<uuid>/v1/sprite/reference.png` exists.
   - `.generated/monstore/<uuid>/v1/audio/cry-battle.mp3` exists.

3. **Adopt script smoke**

   ```text
   uv run .scripts/vibemon_generator.py --stage adopt --count 1
   ```

   Confirm:

   - DB row has lifecycle `manifested`.
   - `trainer_id` points at `"Script Trainer"`.
   - all required manifest assets have DB rows.
   - monstore has sprite, pose, and audio files.
   - `.scripts/generated/<uuid>/name.txt` exists.

4. **Stage-by-stage manual**

   Stop after `lifecycle.christen(vibemon)`: only preview assets should exist.
   Then call `lifecycle.adopt(vibemon, trainer_id)`: sheet and poses should fill
   in.

5. **Memory backend smoke**

   Set `ASSET_STORE_URL=memory:///` and run lifecycle calls in-process.
   `monstore.put` / `get` should work and `url_for` should return appended-key
   memory URLs.

6. **Cleanup dry-run**

   ```text
   uv run .scripts/cleanup_monstore.py --db-path .scripts/vibemon.db
   ```

   Confirm it reports orphan folders/stale blobs/missing blob integrity errors
   without deleting anything.

7. **Grep cleanup**

   ```text
   rg "sprite_store|SpriteLayout|battle_cry: bytes|sprite_sheet_key|render_aesthetic|headless"
   ```

   Expected: no live-code hits except intentionally updated historical docs or
   migration notes.

---

## Out of scope

- Faint and emote sound generation.
- Frontend client wiring.
- Remote object-store cleanup.
- Full trainer gameplay/persistence beyond minimal trainer identity and
  `trainer_id`.
- Wilderness encounter state.
- Evolution behavior, except reserving lifecycle package space for it.
- Asset versioning beyond static `"v1"`.
- Provider proposal vs finalized identity split.
