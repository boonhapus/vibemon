from __future__ import annotations

from typing import Optional

from attrs import define, field


@define
class VibemonStats:
    hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    element: str
    element_secondary: Optional[str] = None


@define
class Move:
    name: str
    type: str
    category: str
    power: int
    accuracy: int
    is_signature: bool = False
    effect: Optional[str] = None


@define
class VisualDNA:
    n_points: int
    spikiness: float
    limb_count: int
    limb_style: str
    eye_count: int
    eye_size: float
    eye_shape: str
    mouth_style: str
    texture_pattern: str
    color_primary: tuple[float, float, float]
    color_secondary: tuple[float, float, float]
    color_accent: tuple[float, float, float]
    color_eye: tuple[float, float, float]
    outline_weight: float
    glow_intensity: float
    size_scale: float
    animation_speed: float


@define
class VibemonPayload:
    uid: str
    name: str
    source: str
    stats: VibemonStats
    moves: list[Move]
    visual_dna: VisualDNA
    flavour_text: str
    stat_origins: dict[str, str]
    fallback: bool = False


@define
class GenerateRequestBody:
    user_id: str
    latitude: float
    longitude: float
    auth_tokens: dict[str, str] = field(factory=dict)
    timestamp: Optional[str] = None
