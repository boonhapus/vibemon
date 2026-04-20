import cattrs

from app import types

base_converter = cattrs.Converter()


# ── Inform cattrs about enum types ────────────────────────────────────────────────────

_must_restructure = (
    types.VibemonTypeT,
    types.StatusConditionT,
    types.MoveCategoryT,
    types.WeatherT,
    types.ActionType,
)


for enum_cls in _must_restructure:
    base_converter.register_structure_hook(enum_cls, lambda v, t: t(v))
    base_converter.register_unstructure_hook(enum_cls, lambda v: v.value)
