"""Sprite presentation constants."""

from typing import NamedTuple


class SnapProfile(NamedTuple):
    """Pixel-grid snap settings for one display context.

    ``grid`` is the long-edge size in true pixels to downsample onto; ``None``
    disables snapping entirely (used for the model-input reference, which must
    stay at native resolution). ``colors`` is the adaptive median-cut palette
    size used to crisp gradients into flat pixel-art regions; ``None`` keeps the
    BOX-resampled colors as-is.
    """

    grid: int | None
    colors: int | None


SHOWCASE_SNAP = SnapProfile(grid=384, colors=64)
"""Mon showcase / emotes: large on screen, lightly snapped to stay on-style."""

EMOTE_SNAP = SHOWCASE_SNAP
"""Emotes follow the showcase treatment."""

BATTLE_SNAP = SnapProfile(grid=192, colors=40)
"""Mon battle sprites: moderately snapped."""

ICON_SNAP = SnapProfile(grid=96, colors=24)
"""Small UI icons / thumbnails: heavily snapped."""

TRAINER_REFERENCE_SNAP = SnapProfile(grid=128, colors=32)
"""Trainer standing reference shown in scenes: parity with the pre-profile look."""

REFERENCE_DISPLAY_GRID = 128
"""Long-edge size in true pixels for standing reference sprites shown in UI."""

REFERENCE_QUANTIZE_COLORS = 32
"""Adaptive color count for crisping generated reference sprites into flat pixel-art regions."""
