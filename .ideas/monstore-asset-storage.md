# Monstore: Asset Storage + Sprite Lifecycle Refactor

> Pickup doc. Self-contained. Read top-to-bottom and you have everything.

---

## Why this work exists

`backend/app/sprite_store.py` was built for one thing: persist a single
sprite-sheet PNG per Vibemon. That assumption now blocks three things:

1. **Cost**: `generate_vibemon_sprite` makes two image-model calls
   (reference → sheet) in one shot. Users who reject the preview pay for
   the sheet anyway. We want reference-only at preview, sheet only at
   adoption.
2. **Asset diversity**: We're adding many MP3 assets — battle cry, faint,
   six emote sounds matching the six emote sprites. The current store
   API and `Aesthetic` shape have no room for them.
3. **Aesthetic shape**: `Aesthetic.battle_cry: bytes` lives inline on the
   model alongside `sprite_sheet_key: str` (a key) and `sprites:
   SpriteLayout` (in-memory derived). Three ways to address one thing.

**Goal**: one asset store keyed by `<vibemon_uuid>/v1/<asset>`, a sprite
pipeline split across `christen()` (reference) + `render_aesthetic()`
(sheet → pose split → cry), and an `Aesthetic` that holds *only*
references.

---

## Current state — what exists today

### `backend/app/sprite_store.py`

```python
SHEET_FILENAME = "sprite-sheet.png"
_UNSIGNABLE_SCHEMES = frozenset({"file", "memory"})

@lru_cache(maxsize=1)
def _store() -> ObjectStore:
    return from_url(settings.sprite_store_url)

def sheet_key(vibemon_slug: str) -> str:
    return f"{vibemon_slug}/{SHEET_FILENAME}"

async def put_sheet(vibemon_slug: str, data: bytes) -> str: ...
async def get_sheet(key: str) -> bytes: ...
async def sheet_url(key, *, expires_in=dt.timedelta(hours=1)) -> str: ...
```

Hardcoded "sheet". Slug-keyed, not UUID-keyed.

### `backend/app/genai/client.py:39-63`

```python
async def generate_vibemon_sprite(vibemon: schema.Vibemon) -> bytes:
    p = utils.load_prompt("sprite-reference.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run(p)
    d = app_utils.normalize_sprite_matte(r.output.data, bg_color=..., rows=1, cols=1)

    p = utils.load_prompt("sprite-sheet.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run([pydantic_ai.BinaryImage(data=d, ...), p])
    d = app_utils.normalize_sprite_matte(r.output.data, bg_color=...)

    if issues := app_utils.validate_sprite_sheet(d):
        raise RuntimeError(...)
    return d
```

Two model calls glued together. Caller can't intercept after reference.

### `backend/app/schema.py:399-458` — `Aesthetic`

```python
class Aesthetic(_Transient):
    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color

    sprite_sheet_key: str | None = None     # ← obstore key
    sprites: SpriteLayout | None = ...      # ← in-memory dict, derived
    battle_cry: bytes | None = None         # ← inline bytes!

    _vibemon: Vibemon | None = None

    async def regenerate(self) -> Self:
        async with asyncio.TaskGroup() as g:
            sprite_task = g.create_task(generate_vibemon_sprite(...))
            cry_task = g.create_task(generate_battle_cry(...))
        sheet_bytes = sprite_task.result()
        self.sprite_sheet_key = await sprite_store.put_sheet(self._vibemon.name, sheet_bytes)
        self.sprites = utils.extract_sprites(image=sheet_bytes)
        self.battle_cry = cry_task.result()
        return self
```

### `backend/app/types.py:153-172` — `SpriteLayout`

TypedDict with literal `sheet` plus 9 named poses. Returned by
`utils.extract_sprites`. Going away.

### `backend/app/schema.py:682-700` — Vibemon lifecycle

```python
async def christen(self) -> Self:           # LLM-name only
    name = await generate_vibemon_name(...)
    self.affinity = ...model_copy(update={"identity": ...})
    return self

async def render_aesthetic(self) -> Self:   # sprites + cry concurrent
    self._aesthetic = Aesthetic.from_vibemon(self)
    await self._aesthetic.regenerate()
    return self
```

`Vibemon` has **no `id` field today** (the SQLAlchemy `models.Vibemon` does
— `models.py:124`). We need to add one to `schema.Vibemon` so
in-memory and persisted ids match for path keying.

### `.scripts/vibemon_generator.py:122-130`

```python
def write_aesthetic_to_disk(vibemon):
    aesthetic = vibemon.aesthetic
    assert aesthetic.battle_cry is not None and aesthetic.sprites is not None
    directory = pathlib.Path(__file__).parent / "generated" / vibemon.name.lower()
    directory.mkdir(parents=True, exist_ok=True)
    directory.joinpath("battle_cry.mp3").write_bytes(aesthetic.battle_cry)
    for key, sprite in aesthetic.sprites.items():
        sprite.save(directory.joinpath(f"{key}.png"))
```

Reads inline `battle_cry` bytes + iterates `sprites` dict. Both gone after
refactor → must `await aesthetic.bytes_for(kind)`.

---

## Decisions (already locked in with user)

| # | Question | Answer |
|---|---|---|
| 1 | Reference image — store or ephemeral? | **Store it.** Reused by sheet stage. |
| 2 | When does reference get generated? | **In `christen()`** — uses identity name. |
| 3 | Keep `SpriteLayout` TypedDict? | **Drop.** Per-pose PNGs persisted individually. |
| 4 | Asset path scheme? | `<vibemon_uuid>/v1/<asset>.<ext>` — UUID, not slug. |
| 5 | `Aesthetic.battle_cry: bytes` stays? | **No.** Only keys persisted. |
| 6 | Module name? | **`monstore`** (Vibemon + obstore). |
| 7 | Audio scope now? | Enum reserves all kinds; only `CRY_BATTLE` wired. |

---

## Target architecture

### `backend/app/monstore.py` (new — replaces `sprite_store.py`)

```python
from enum import StrEnum
from functools import lru_cache
from urllib.parse import urlsplit
import datetime as dt
import uuid

import obstore
from obstore.store import ObjectStore, from_url

from app.settings import settings


class AssetKind(StrEnum):
    REFERENCE = "sprite/reference.png"
    SHEET     = "sprite/sheet.png"

    POSE_BATTLE_BACK      = "pose/battle-back.png"
    POSE_BATTLE_HERO      = "pose/battle-hero.png"
    POSE_BATTLE_OPPONENT  = "pose/battle-opponent.png"
    POSE_EMOTE_RESTING    = "pose/emote-resting.png"
    POSE_EMOTE_HAPPY      = "pose/emote-happy.png"
    POSE_EMOTE_FRUSTRATED = "pose/emote-frustrated.png"
    POSE_EMOTE_PROUD      = "pose/emote-proud.png"
    POSE_EMOTE_CONFUSED   = "pose/emote-confused.png"
    POSE_EMOTE_SAD        = "pose/emote-sad.png"

    CRY_BATTLE = "audio/cry-battle.mp3"
    CRY_FAINT  = "audio/cry-faint.mp3"

    SOUND_EMOTE_RESTING    = "audio/emote-resting.mp3"
    SOUND_EMOTE_HAPPY      = "audio/emote-happy.mp3"
    SOUND_EMOTE_FRUSTRATED = "audio/emote-frustrated.mp3"
    SOUND_EMOTE_PROUD      = "audio/emote-proud.mp3"
    SOUND_EMOTE_CONFUSED   = "audio/emote-confused.mp3"
    SOUND_EMOTE_SAD        = "audio/emote-sad.mp3"


SCHEMA_PREFIX = "v1"
_UNSIGNABLE_SCHEMES = frozenset({"file", "memory"})


@lru_cache(maxsize=1)
def _store() -> ObjectStore:
    return from_url(settings.asset_store_url)


def _scheme() -> str:
    return urlsplit(settings.asset_store_url).scheme


def asset_key(vibemon_id: uuid.UUID, kind: AssetKind) -> str:
    return f"{vibemon_id}/{SCHEMA_PREFIX}/{kind.value}"


async def put(vibemon_id: uuid.UUID, kind: AssetKind, data: bytes) -> str:
    key = asset_key(vibemon_id, kind)
    await obstore.put_async(_store(), key, data)
    return key


async def get(key: str) -> bytes:
    result = await obstore.get_async(_store(), key)
    return bytes(await result.bytes_async())


async def url(key: str, *, expires_in: dt.timedelta = dt.timedelta(hours=1)) -> str:
    if _scheme() in _UNSIGNABLE_SCHEMES:
        base = settings.asset_store_url.rstrip("/")
        return f"{base}/{key}"
    return await obstore.sign_async(_store(), "GET", key, expires_in)
```

### `backend/app/settings.py` — rename

```python
# old
sprite_store_url: str = "file://./.generated/sprites"
# new
asset_store_url: str = "file://./.generated/monstore"
```

Update validator name + reference. Behavior unchanged.

### `backend/app/types.py` — pose enum, drop layout

Drop `SpriteLayout` TypedDict (lines 153-172). Add:

```python
class PoseT(StrEnum):
    BATTLE_BACK      = "battle_back"
    BATTLE_HERO      = "battle_hero"
    BATTLE_OPPONENT  = "battle_opponent"
    EMOTE_RESTING    = "emote_resting"
    EMOTE_HAPPY      = "emote_happy"
    EMOTE_FRUSTRATED = "emote_frustrated"
    EMOTE_PROUD      = "emote_proud"
    EMOTE_CONFUSED   = "emote_confused"
    EMOTE_SAD        = "emote_sad"
```

`POSE_TO_ASSET: dict[PoseT, AssetKind]` lookup near `AssetKind` so callers
have one source of truth mapping pose → asset slot.

### `backend/app/utils.py:568-628` — `extract_sprites` returns dict

```python
def extract_sprites(
    image: bytes | Image.Image,
    rows: int = 3, cols: int = 3, padding: int = 8,
    *, strict_matte: bool = False,
) -> dict[types.PoseT, Image.Image]:
    ...
    bb, bh, bo, er, eh, ef, ep, ec, es = aligned
    return {
        types.PoseT.BATTLE_BACK: bb,
        types.PoseT.BATTLE_HERO: bh,
        types.PoseT.BATTLE_OPPONENT: bo,
        types.PoseT.EMOTE_RESTING: er,
        types.PoseT.EMOTE_HAPPY: eh,
        types.PoseT.EMOTE_FRUSTRATED: ef,
        types.PoseT.EMOTE_PROUD: ep,
        types.PoseT.EMOTE_CONFUSED: ec,
        types.PoseT.EMOTE_SAD: es,
    }
```

The `sheet` key in the old layout is gone — sheet has its own
`AssetKind.SHEET` slot.

### `backend/app/genai/client.py` — split

```python
async def generate_sprite_reference(vibemon: schema.Vibemon) -> bytes:
    p = utils.load_prompt("sprite-reference.mdc", vibemon=vibemon)
    r = await FAST_IMG_AGENT.run(p)
    return app_utils.normalize_sprite_matte(
        r.output.data, bg_color=vibemon.aesthetic.background_color,
        rows=1, cols=1,
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


# generate_battle_cry unchanged
```

Delete the old combined `generate_vibemon_sprite`.

### `backend/app/schema.py` — Vibemon id + Aesthetic shape

`Vibemon` (line 615):
```python
class Vibemon(_Transient):
    id: uuid.UUID = pydantic.Field(default_factory=uuid.uuid7)
    nickname: str | None = None
    affinity: Affinity
    ...
```

`Aesthetic` (line 399) becomes:
```python
class Aesthetic(_Transient):
    primary_color: brand.Color
    secondary_color: brand.Color | None = None
    background_color: brand.Color
    assets: dict[types.AssetKind, str] = pydantic.Field(default_factory=dict)

    _vibemon: Vibemon | None = pydantic.PrivateAttr(default=None)

    def has(self, kind: types.AssetKind) -> bool:
        return kind in self.assets

    async def url_for(self, kind: types.AssetKind, *, expires_in=dt.timedelta(hours=1)) -> str | None:
        key = self.assets.get(kind)
        return await monstore.url(key, expires_in=expires_in) if key else None

    async def bytes_for(self, kind: types.AssetKind) -> bytes | None:
        key = self.assets.get(kind)
        return await monstore.get(key) if key else None

    @classmethod
    def from_vibemon(cls, vibemon: Vibemon) -> Self:
        # color derivation unchanged
        ins = cls(**colors)
        ins._vibemon = vibemon
        return ins
```

Drop `_unwrap_sprite_sheet` validator, `sprites`, `battle_cry`,
`sprite_sheet_key`, and the old `regenerate()`.

`Vibemon.christen()`:
```python
async def christen(self) -> Self:
    from app.genai.client import generate_vibemon_name, generate_sprite_reference

    name = await generate_vibemon_name(...)
    self.affinity = ...model_copy(update={"identity": ...with name})

    if not hasattr(self, "_aesthetic"):
        self._aesthetic = Aesthetic.from_vibemon(self)

    ref_bytes = await generate_sprite_reference(self)
    key = await monstore.put(self.id, AssetKind.REFERENCE, ref_bytes)
    self._aesthetic.assets[AssetKind.REFERENCE] = key
    return self
```

`Vibemon.render_aesthetic()`:
```python
async def render_aesthetic(self) -> Self:
    if not hasattr(self, "_aesthetic"):
        raise RuntimeError("call christen() first — no reference image to base sheet on")

    ref_key = self._aesthetic.assets.get(AssetKind.REFERENCE)
    if ref_key is None:
        raise RuntimeError("missing REFERENCE asset; christen() must run first")
    reference_bytes = await monstore.get(ref_key)

    async with asyncio.TaskGroup() as g:
        sheet_task = g.create_task(generate_sprite_sheet(self, reference_bytes))
        cry_task = g.create_task(generate_battle_cry(self))

    sheet_bytes = sheet_task.result()
    cry_bytes = cry_task.result()

    sheet_key = await monstore.put(self.id, AssetKind.SHEET, sheet_bytes)
    self._aesthetic.assets[AssetKind.SHEET] = sheet_key

    poses = utils.extract_sprites(image=sheet_bytes)
    pose_kinds = {
        types.PoseT.BATTLE_BACK:      AssetKind.POSE_BATTLE_BACK,
        types.PoseT.BATTLE_HERO:      AssetKind.POSE_BATTLE_HERO,
        types.PoseT.BATTLE_OPPONENT:  AssetKind.POSE_BATTLE_OPPONENT,
        types.PoseT.EMOTE_RESTING:    AssetKind.POSE_EMOTE_RESTING,
        types.PoseT.EMOTE_HAPPY:      AssetKind.POSE_EMOTE_HAPPY,
        types.PoseT.EMOTE_FRUSTRATED: AssetKind.POSE_EMOTE_FRUSTRATED,
        types.PoseT.EMOTE_PROUD:      AssetKind.POSE_EMOTE_PROUD,
        types.PoseT.EMOTE_CONFUSED:   AssetKind.POSE_EMOTE_CONFUSED,
        types.PoseT.EMOTE_SAD:        AssetKind.POSE_EMOTE_SAD,
    }
    for pose, image in poses.items():
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        kind = pose_kinds[pose]
        self._aesthetic.assets[kind] = await monstore.put(self.id, kind, buf.getvalue())

    cry_key = await monstore.put(self.id, AssetKind.CRY_BATTLE, cry_bytes)
    self._aesthetic.assets[AssetKind.CRY_BATTLE] = cry_key
    return self
```

### `.scripts/vibemon_generator.py:122-130` — async dump

```python
async def write_aesthetic_to_disk(vibemon: schema.Vibemon) -> None:
    aesthetic = vibemon.aesthetic
    directory = pathlib.Path(__file__).parent / "generated" / vibemon.name.lower()
    directory.mkdir(parents=True, exist_ok=True)
    for kind in aesthetic.assets:
        data = await aesthetic.bytes_for(kind)
        if data is None:
            continue
        ext = pathlib.Path(kind.value).suffix
        stem = pathlib.Path(kind.value).stem
        directory.joinpath(f"{stem}{ext}").write_bytes(data)
```

Caller in `generate_vibemon_in_world` (line 154) becomes
`await write_aesthetic_to_disk(vibemon)`.

---

## Files at a glance

| File | Action |
|---|---|
| `backend/app/monstore.py` | **NEW** — generic asset store |
| `backend/app/sprite_store.py` | **DELETE** |
| `backend/app/settings.py` | rename `sprite_store_url` → `asset_store_url` |
| `backend/app/types.py` | drop `SpriteLayout`, add `PoseT` |
| `backend/app/utils.py` | `extract_sprites` returns `dict[PoseT, Image]` |
| `backend/app/genai/client.py` | split sprite gen into reference + sheet |
| `backend/app/schema.py` | `Vibemon.id` field; new `Aesthetic` shape; christen+render split |
| `.scripts/vibemon_generator.py` | async asset dump via `bytes_for` |
| `.agents/skills/development/frontend-design/SKILL.md` | update `sprite_store` references |
| `backend/tests/test_determinism.py` | adapt if it asserts old Aesthetic fields |

---

## Reused functions (don't reinvent)

- `obstore.put_async` / `get_async` / `sign_async` — same primitives as
  `sprite_store.py:46,52,68`.
- `app.utils.normalize_sprite_matte` (`utils.py:380`) — both reference
  and sheet stages.
- `app.utils.validate_sprite_sheet` (`utils.py:466`) — sheet-stage check.
- `app.utils.extract_sprites` (`utils.py:568`) — slicing math intact;
  return type changes.
- `_UNSIGNABLE_SCHEMES` + presigning fallback (`sprite_store.py:26,
  64-66`) — port verbatim into monstore.
- `uuid.uuid7` — already used in `models.py` for DB ids; reuse for the
  new `schema.Vibemon.id` so in-memory and DB ids align.

---

## Lifecycle: before vs after

```
BEFORE:
  birth() → christen() [name only]   → render_aesthetic() [ref + sheet + cry]
                                       └─ pays for sheet even on rejected previews

AFTER:
  birth() → christen() [name + REFERENCE]   → render_aesthetic() [SHEET + 9 POSES + CRY_BATTLE]
            └─ cheap; reference shown in UI    └─ runs only after user adopts
```

---

## Verification

1. **Determinism harness** — `cd backend && uv run pytest tests/test_determinism.py`.
   Update only if it asserts old `Aesthetic` field shape.
2. **End-to-end gen** — `uv run .scripts/vibemon_generator.py` for one
   non-headless run. Confirm `.generated/monstore/<uuid>/v1/sprite/...`,
   `.../pose/...`, `.../audio/cry-battle.mp3` all exist.
   `.scripts/generated/<name>/` dump should still contain sheet + 9
   poses + battle_cry.mp3 sourced via `bytes_for`.
3. **Stage-by-stage** — manually stop after `christen()`. Only
   `sprite/reference.png` should exist for that UUID. Then run
   `render_aesthetic()`. Sheet, poses, cry fill in.
4. **Memory backend smoke** — set `ASSET_STORE_URL=memory:///` and run
   one gen. All `monstore.put` / `get` calls succeed; `url_for` returns
   the appended-key form (per `_UNSIGNABLE_SCHEMES`).
5. **Cleanup grep** — `rg "sprite_store|SpriteLayout|battle_cry: bytes|sprite_sheet_key"`
   must return zero hits across the live codebase.

---

## Out of scope (intentionally)

- Faint + emote sound generators — `AssetKind` reserves the slots, no
  ElevenLabs prompts wired yet. Follow-up task.
- Frontend client wiring — backend already exposes `url_for(kind)` and
  the URL contract is unchanged in spirit.
- Re-roll versioning beyond static `v1`. If we need overwrite-safe
  re-rolls, bump to a per-Vibemon counter (e.g. `v1` → generation
  attempt N) — easy to add later.
- DB persistence of `Aesthetic.assets` map — separate concern; DB
  schema currently doesn't store any aesthetic state.

---

## Open questions when resuming

- **`Aesthetic.from_vibemon` access pattern**: currently sets
  `_vibemon` private attr. After the refactor, christen must be able to
  construct it before render_aesthetic — confirm there's no caller that
  relies on aesthetic existing only post-render.
- **Reference normalization**: keep `rows=1, cols=1` matte normalization
  on the reference? Yes for now (parity), but it's cheap to drop later
  if reference doesn't need the matte cleanup.
- **Path versioning**: `v1` is a static literal. If a future change needs
  invalidation, plan for `v2` etc. — `SCHEMA_PREFIX` constant centralizes
  it.
