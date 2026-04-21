# from typing import Protocol, runtime_checkable

# import attrs

# from app import utils


class Base:
    pass


# @attrs.define
# class ColorShift:
#     hue_rotation: float = 0.0
#     lightness_adjust: float = 0.0
#     hex_override: str | None = None

#     def __attrs_post_init__(self) -> None:
#         self.hue_rotation = max(-30.0, min(30.0, self.hue_rotation))
#         self.lightness_adjust = max(-0.15, min(0.15, self.lightness_adjust))


# @attrs.define
# class VisualDelta:
#     color_shifts: dict[str, ColorShift] = attrs.field(factory=dict)
#     glow_rule_override: str | None = None


# @attrs.define
# class Delta:
#     delta_stats: dict[str, int] = attrs.field(factory=dict)
#     delta_visual: VisualDelta = attrs.field(factory=VisualDelta)
#     delta_level: int = 0
#     delta_description: str | None = None


# @attrs.define
# class SourceData:
#     provider_id: str
#     payload: dict = attrs.field(factory=dict)
#     privacy_flags: dict = attrs.field(factory=dict)


# @attrs.define
# class Context:
#     birth_seed: str
#     timestamp: str
#     location: str = ""
#     weather: dict | None = None
#     source_data: dict[str, SourceData] = attrs.field(factory=dict)
#     enabled_providers: list[str] = attrs.field(factory=list)


# @runtime_checkable
# class DataProvider(Protocol):
#     @property
#     def name(self) -> str: ...

#     @property
#     def affinities(self) -> set[str]: ...

#     async def intensity(self, context: Context) -> float: ...

#     async def contribute(self, context: Context) -> Delta: ...


# STAT_NAMES = ("max_hp", "attack", "defense", "sp_attack", "sp_defense", "speed")


# def merge_deltas(
#     base_stats: dict[str, int],
#     deltas: list[tuple[float, Delta]],
# ) -> tuple[dict[str, int], VisualDelta, list[str]]:
#     final_stats = dict(base_stats)
#     merged_visual = VisualDelta()
#     description_fragments: list[str] = []

#     for intensity, delta in deltas:
#         for stat, value in delta.delta_stats.items():
#             if stat in final_stats:
#                 final_stats[stat] = utils.clamp(
#                     final_stats[stat] + int(value * intensity),
#                     minimum=0, maximum=255,
#                 )

#         for region, shift in delta.delta_visual.color_shifts.items():
#             if region not in merged_visual.color_shifts:
#                 merged_visual.color_shifts[region] = ColorShift()
#             existing = merged_visual.color_shifts[region]
#             if shift.hex_override is not None:
#                 existing.hex_override = shift.hex_override
#             else:
#                 existing.hue_rotation = max(
#                     -30.0, min(30.0, existing.hue_rotation + shift.hue_rotation)
#                 )
#                 existing.lightness_adjust = max(
#                     -0.15,
#                     min(0.15, existing.lightness_adjust + shift.lightness_adjust),
#                 )

#         if delta.delta_visual.glow_rule_override is not None:
#             merged_visual.glow_rule_override = delta.delta_visual.glow_rule_override

#         if delta.delta_description is not None:
#             description_fragments.append(delta.delta_description)

#     return final_stats, merged_visual, description_fragments
