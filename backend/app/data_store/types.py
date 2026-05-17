"""Asset vocabularies for the monstore.

Each ``AssetKind`` value is a relative path under ``<vibemon_uuid>/<version>/``.
"""

import enum


class AssetKind(enum.StrEnum):
    """Asset kinds stored per Vibemon."""

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
