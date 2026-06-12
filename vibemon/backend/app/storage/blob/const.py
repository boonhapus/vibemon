"""Static lookup tables for Vibemon asset storage keys and MIME types."""

from app.domains.vibemon.assets import AssetKind
from app.domains.vibemon.types import PoseT

UNSIGNABLE_SCHEMES = frozenset({"file", "memory"})
"""URL schemes that cannot be presigned; we hand back direct locators instead."""


POSE_TO_ASSET: dict[PoseT, AssetKind] = {
    PoseT.BATTLE_BACK: AssetKind.POSE_BATTLE_BACK,
    PoseT.BATTLE_HERO: AssetKind.POSE_BATTLE_HERO,
    PoseT.BATTLE_OPPONENT: AssetKind.POSE_BATTLE_OPPONENT,
    PoseT.EMOTE_RESTING: AssetKind.POSE_EMOTE_RESTING,
    PoseT.EMOTE_HAPPY: AssetKind.POSE_EMOTE_HAPPY,
    PoseT.EMOTE_FRUSTRATED: AssetKind.POSE_EMOTE_FRUSTRATED,
    PoseT.EMOTE_PROUD: AssetKind.POSE_EMOTE_PROUD,
    PoseT.EMOTE_CONFUSED: AssetKind.POSE_EMOTE_CONFUSED,
    PoseT.EMOTE_SAD: AssetKind.POSE_EMOTE_SAD,
}


_PNG = "image/png"
_MP3 = "audio/mpeg"

CONTENT_TYPE_BY_EXTENSION: dict[str, str] = {
    "png": _PNG,
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "mp3": _MP3,
}

ASSET_CONTENT_TYPES: dict[AssetKind, str] = {
    AssetKind.REFERENCE: _PNG,
    AssetKind.REFERENCE_RAW: _PNG,
    AssetKind.SHEET: _PNG,
    AssetKind.POSE_BATTLE_BACK: _PNG,
    AssetKind.POSE_BATTLE_HERO: _PNG,
    AssetKind.POSE_BATTLE_OPPONENT: _PNG,
    AssetKind.POSE_EMOTE_RESTING: _PNG,
    AssetKind.POSE_EMOTE_HAPPY: _PNG,
    AssetKind.POSE_EMOTE_FRUSTRATED: _PNG,
    AssetKind.POSE_EMOTE_PROUD: _PNG,
    AssetKind.POSE_EMOTE_CONFUSED: _PNG,
    AssetKind.POSE_EMOTE_SAD: _PNG,
    AssetKind.CRY_BATTLE: _MP3,
    AssetKind.CRY_FAINT: _MP3,
    AssetKind.SOUND_EMOTE_RESTING: _MP3,
    AssetKind.SOUND_EMOTE_HAPPY: _MP3,
    AssetKind.SOUND_EMOTE_FRUSTRATED: _MP3,
    AssetKind.SOUND_EMOTE_PROUD: _MP3,
    AssetKind.SOUND_EMOTE_CONFUSED: _MP3,
    AssetKind.SOUND_EMOTE_SAD: _MP3,
}


REQUIRED_CHRISTEN_ASSETS: frozenset[AssetKind] = frozenset(
    {
        AssetKind.REFERENCE,
        AssetKind.CRY_BATTLE,
    }
)
"""Assets that must exist for a Vibemon to reach the ``CHRISTENED`` lifecycle."""


REQUIRED_MANIFEST_ASSETS: frozenset[AssetKind] = frozenset(
    {
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
    }
)
"""Assets that must exist for a Vibemon to reach the ``MANIFESTED`` lifecycle."""


assert set(ASSET_CONTENT_TYPES.keys()) == set(AssetKind), (
    f"ASSET_CONTENT_TYPES is out of sync with AssetKind. "
    f"Missing: {set(AssetKind) - set(ASSET_CONTENT_TYPES.keys())}, "
    f"Extra: {set(ASSET_CONTENT_TYPES.keys()) - set(AssetKind)}"
)
