import cattrs

from app import const, types, utils

base_converter = cattrs.Converter()


# ── Inform cattrs about enum types ────────────────────────────────────────────────────

_enum_restructure = (
    types.VibemonTypeT,
    types.StatusConditionT,
    types.MoveCategoryT,
    types.WeatherT,
    types.ActionType,
)

for enum_cls in _enum_restructure:
    base_converter.register_structure_hook(enum_cls, lambda v, t: t(v))
    base_converter.register_unstructure_hook(enum_cls, lambda v: v.value)

base_converter.register_structure_hook(
    types.BaseStat,
    lambda v, _: utils.clamp(v, minimum=const.BASE_STAT_MIN, maximum=const.BASE_STAT_MAX)
)
