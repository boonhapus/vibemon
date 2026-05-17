# /// script
# requires-python = ">=3.14"
# dependencies = ["vibemon-backend", "sqlalchemy"]
#
# [tool.uv.sources]
# vibemon-backend = { path = "../../../../../backend" , editable = true }
# ///

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Annotated, get_args, get_origin
import argparse
import asyncio
import datetime as dt
import inspect
import json
import random
import statistics
import uuid

import pydantic
import structlog

from app import const, models, schema, types
from app.balance import element_chart
from app.battle import actions
from app.battle import schema as battle_schema
from app.battle.engine import GameEngine
from app.plugins.climate import moves as climate_moves
from app.plugins.climate.const import WeatherCode
from app.plugins.climate.provider import ClimateProvider


type PolicyName = str

STAT_KEYS: tuple[types.BaseStatNameT, ...] = (
    "hp",
    "attack",
    "defense",
    "sp_attack",
    "sp_defense",
    "speed",
)

BASELINE_WEATHER: dict[str, float] = {
    "cape_mean": 80.0,
    "cloud_cover_mean": 45.0,
    "dew_point_2m_mean": 9.0,
    "dust_mean": 8.0,
    "et0_fao_evapotranspiration": 3.5,
    "pm2_5_mean": 8.0,
    "precipitation_sum": 0.2,
    "pressure_msl_mean": 1013.2,
    "pressure_msl_range": 8.0,
    "relative_humidity_2m_mean": 62.0,
    "shortwave_radiation_sum": 16.0,
    "snowfall_sum": 0.0,
    "soil_moisture_0_to_1cm_mean": 0.25,
    "temperature_2m_max": 21.0,
    "temperature_2m_min": 9.0,
    "uv_index_max": 5.0,
    "visibility_mean": 18000.0,
    "wind_gusts_10m_max": 24.0,
    "wind_speed_10m_max": 12.0,
    "elevation": 350.0,
}


class _Model(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", arbitrary_types_allowed=True)


class ScenarioSpec(_Model):
    name: str
    description: str
    weather_code: WeatherCode
    overrides: dict[str, float] = pydantic.Field(default_factory=dict)


class MoveCatalogReport(_Model):
    total_moves: int
    level_one_moves: int
    by_type: dict[str, int]
    by_category: dict[str, int]
    by_level: dict[str, int]
    power_by_category: dict[str, dict[str, float]]
    accuracy_counts: dict[str, int]
    priority_counts: dict[str, int]
    effect_kind_counts: dict[str, int]
    status_counts: dict[str, int]
    weather_set_counts: dict[str, int]
    move_targets: dict[str, int]
    moves_with_effects: int
    moves_with_conditions: int
    moves_with_script_ids: int
    findings: list[str]


class MoveSetReport(_Model):
    move_count: int
    damaging_count: int
    status_count: int
    stab_count: int
    priority_count: int
    average_power: float | None
    best_power: int | None
    offensive_coverage_types: int
    blocked_by_immunity_types: int


class ScenarioAffinityReport(_Model):
    name: str
    description: str
    weather_code: str
    elements: list[str]
    intensity: float
    tier: str
    battle_role: str
    bst: int
    stats: dict[str, int]
    defensive_profile: dict[str, int]
    moves: MoveSetReport


class ProviderContractReport(_Model):
    provider_name: str
    exposed_elements: dict[str, str]
    missing_exposed_elements: list[str]
    birth_seed_columns: list[str]
    birth_snapshot_columns: list[str]
    vibemon_columns: list[str]
    identity_columns: list[str]
    vibemon_move_columns: list[str]
    unseeded_replay_deterministic: bool
    seeded_replay_deterministic: bool
    synthesize_network_free: bool
    notes: list[str]


class GeneratedAffinityReport(_Model):
    scenario_count: int
    dual_type_rate: float
    element_frequency: dict[str, int]
    tier_frequency: dict[str, int]
    battle_role_frequency: dict[str, int]
    intensity: dict[str, float]
    stats: dict[str, dict[str, float]]
    scenarios: list[ScenarioAffinityReport]
    findings: list[str]


class BattleScenarioSummary(_Model):
    scenario: str
    wins: int
    losses: int
    draws: int
    win_rate: float
    average_turns: float


class BattlePolicySummary(_Model):
    policy: str
    wins_by_scenario: dict[str, int]
    draws: int


class BattleReport(_Model):
    policies: list[str]
    simulations: int
    max_turns: int
    by_scenario: list[BattleScenarioSummary]
    by_policy: list[BattlePolicySummary]
    dominant_scenarios: list[str]
    weak_scenarios: list[str]
    findings: list[str]


class ScorecardItem(_Model):
    axis: str
    status: str
    summary: str


class ProviderBalanceReport(_Model):
    generated_at: str
    benchmark: list[str]
    contract: ProviderContractReport
    move_catalog: MoveCatalogReport
    generated_affinities: GeneratedAffinityReport
    battle: BattleReport
    scorecard: list[ScorecardItem]
    pokemon_benchmark_differences: list[str]
    top_findings: list[str]


SCENARIOS: tuple[ScenarioSpec, ...] = (
    ScenarioSpec(
        name="average_suburban",
        description="A calm, partly cloudy inhabited baseline.",
        weather_code=WeatherCode.PARTLY_CLOUDY,
        overrides={},
    ),
    ScenarioSpec(
        name="clear_pristine",
        description="Clean air, strong sun, and moderate moisture.",
        weather_code=WeatherCode.CLEAR_SKY,
        overrides={
            "cloud_cover_mean": 5.0,
            "shortwave_radiation_sum": 28.0,
            "uv_index_max": 9.0,
            "pm2_5_mean": 2.0,
            "relative_humidity_2m_mean": 55.0,
        },
    ),
    ScenarioSpec(
        name="overcast",
        description="Heavy cloud cover with low light and no major precipitation.",
        weather_code=WeatherCode.OVERCAST,
        overrides={
            "cloud_cover_mean": 98.0,
            "uv_index_max": 0.8,
            "shortwave_radiation_sum": 5.0,
            "visibility_mean": 12000.0,
        },
    ),
    ScenarioSpec(
        name="fog_low_uv",
        description="Dense low-UV fog with cold, still air.",
        weather_code=WeatherCode.FOG,
        overrides={
            "cloud_cover_mean": 100.0,
            "uv_index_max": 0.2,
            "visibility_mean": 1800.0,
            "temperature_2m_min": 3.0,
            "wind_speed_10m_max": 4.0,
            "wind_gusts_10m_max": 7.0,
        },
    ),
    ScenarioSpec(
        name="heavy_rain",
        description="Saturated warm rain with high humidity.",
        weather_code=WeatherCode.RAIN_HEAVY,
        overrides={
            "cloud_cover_mean": 100.0,
            "precipitation_sum": 60.0,
            "relative_humidity_2m_mean": 96.0,
            "dew_point_2m_mean": 22.0,
            "soil_moisture_0_to_1cm_mean": 0.50,
            "visibility_mean": 6000.0,
        },
    ),
    ScenarioSpec(
        name="snowstorm",
        description="Heavy snow with sub-freezing temperatures.",
        weather_code=WeatherCode.SNOW_FALL_HEAVY,
        overrides={
            "cloud_cover_mean": 100.0,
            "precipitation_sum": 18.0,
            "snowfall_sum": 25.0,
            "temperature_2m_max": -5.0,
            "temperature_2m_min": -16.0,
            "wind_speed_10m_max": 30.0,
            "wind_gusts_10m_max": 55.0,
            "visibility_mean": 2500.0,
        },
    ),
    ScenarioSpec(
        name="thunderstorm",
        description="Convective storm with heavy rain and violent gusts.",
        weather_code=WeatherCode.THUNDERSTORM,
        overrides={
            "cape_mean": 3500.0,
            "cloud_cover_mean": 100.0,
            "precipitation_sum": 28.0,
            "wind_speed_10m_max": 38.0,
            "wind_gusts_10m_max": 95.0,
            "visibility_mean": 5000.0,
        },
    ),
    ScenarioSpec(
        name="heatwave_desert",
        description="Scorching arid heat with exposed dry topsoil.",
        weather_code=WeatherCode.CLEAR_SKY,
        overrides={
            "dust_mean": 85.0,
            "relative_humidity_2m_mean": 12.0,
            "shortwave_radiation_sum": 34.0,
            "soil_moisture_0_to_1cm_mean": 0.04,
            "temperature_2m_max": 49.0,
            "temperature_2m_min": 31.0,
            "uv_index_max": 12.0,
            "elevation": 120.0,
        },
    ),
    ScenarioSpec(
        name="high_mountain",
        description="Cold high-altitude wind over exposed rock and snow.",
        weather_code=WeatherCode.PARTLY_CLOUDY,
        overrides={
            "elevation": 3400.0,
            "snowfall_sum": 1.5,
            "temperature_2m_max": 4.0,
            "temperature_2m_min": -9.0,
            "wind_speed_10m_max": 58.0,
            "wind_gusts_10m_max": 98.0,
            "shortwave_radiation_sum": 24.0,
            "uv_index_max": 10.0,
        },
    ),
    ScenarioSpec(
        name="polluted_city",
        description="Smoggy, overcast, stagnant urban air.",
        weather_code=WeatherCode.OVERCAST,
        overrides={
            "cloud_cover_mean": 92.0,
            "pm2_5_mean": 185.0,
            "relative_humidity_2m_mean": 72.0,
            "uv_index_max": 1.0,
            "wind_speed_10m_max": 3.0,
            "wind_gusts_10m_max": 6.0,
            "visibility_mean": 7000.0,
        },
    ),
    ScenarioSpec(
        name="dust_basin",
        description="Dry basin with airborne mineral dust and strong gusts.",
        weather_code=WeatherCode.MAINLY_CLEAR,
        overrides={
            "dust_mean": 450.0,
            "relative_humidity_2m_mean": 16.0,
            "soil_moisture_0_to_1cm_mean": 0.05,
            "wind_speed_10m_max": 42.0,
            "wind_gusts_10m_max": 88.0,
            "temperature_2m_max": 34.0,
            "visibility_mean": 9000.0,
        },
    ),
    ScenarioSpec(
        name="tropical_farm",
        description="Warm, wet, verdant conditions with active soil moisture.",
        weather_code=WeatherCode.RAIN_SHOWERS_SLIGHT,
        overrides={
            "dew_point_2m_mean": 24.0,
            "et0_fao_evapotranspiration": 7.0,
            "precipitation_sum": 3.0,
            "relative_humidity_2m_mean": 93.0,
            "soil_moisture_0_to_1cm_mean": 0.47,
            "temperature_2m_max": 31.0,
            "temperature_2m_min": 24.0,
        },
    ),
    ScenarioSpec(
        name="pressure_swing",
        description="Large barometric swings without a decisive weather event.",
        weather_code=WeatherCode.PARTLY_CLOUDY,
        overrides={
            "pressure_msl_mean": 1000.0,
            "pressure_msl_range": 36.0,
            "wind_gusts_10m_max": 48.0,
            "wind_speed_10m_max": 22.0,
        },
    ),
    ScenarioSpec(
        name="stable_high_pressure",
        description="Dry stable high pressure with sparse precipitation.",
        weather_code=WeatherCode.CLEAR_SKY,
        overrides={
            "pressure_msl_mean": 1040.0,
            "pressure_msl_range": 2.0,
            "precipitation_sum": 0.0,
            "relative_humidity_2m_mean": 24.0,
            "cloud_cover_mean": 2.0,
            "uv_index_max": 7.0,
        },
    ),
    ScenarioSpec(
        name="fetch_defaults_dry",
        description="The dry fallback path for provider-injected air and soil defaults.",
        weather_code=WeatherCode.MAINLY_CLEAR,
        overrides={
            "dust_mean": 0.0,
            "pm2_5_mean": 0.0,
            "soil_moisture_0_to_1cm_mean": 0.18,
            "precipitation_sum": 0.0,
        },
    ),
)


def _safe_average(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def _stats(values: Sequence[float]) -> dict[str, float]:
    if not values:
        return {"min": 0.0, "avg": 0.0, "median": 0.0, "max": 0.0}
    return {
        "min": round(min(values), 4),
        "avg": round(_safe_average(values), 4),
        "median": round(statistics.median(values), 4),
        "max": round(max(values), 4),
    }


def _stable_seed(label: str) -> str:
    return f"provider-balance:{label}"


def _with_random_seed[T](label: str, fn) -> T:
    state = random.getstate()
    random.seed(_stable_seed(label))
    try:
        return fn()
    finally:
        random.setstate(state)


async def _with_random_seed_async[T](label: str, fn) -> T:
    state = random.getstate()
    random.seed(_stable_seed(label))
    try:
        return await fn()
    finally:
        random.setstate(state)


def build_climate_payload(spec: ScenarioSpec, *, days: int = 44) -> dict[str, object]:
    final = {**BASELINE_WEATHER, **spec.overrides}
    baseline = dict(BASELINE_WEATHER)

    def series(key: str) -> list[float]:
        return [float(baseline[key])] * (days - 1) + [float(final[key])]

    def pressure_max(values: dict[str, float]) -> float:
        return float(values["pressure_msl_mean"] + values["pressure_msl_range"] / 2)

    def pressure_min(values: dict[str, float]) -> float:
        return float(values["pressure_msl_mean"] - values["pressure_msl_range"] / 2)

    daily: dict[str, list[float] | list[int] | list[str]] = {
        "time": [(dt.date(2026, 1, 1) + dt.timedelta(days=i)).isoformat() for i in range(days)],
        "weather_code": [int(WeatherCode.PARTLY_CLOUDY)] * (days - 1) + [int(spec.weather_code)],
        "uv_index_max": series("uv_index_max"),
        "shortwave_radiation_sum": series("shortwave_radiation_sum"),
        "relative_humidity_2m_mean": series("relative_humidity_2m_mean"),
        "temperature_2m_max": series("temperature_2m_max"),
        "temperature_2m_min": series("temperature_2m_min"),
        "apparent_temperature_mean": series("temperature_2m_max"),
        "visibility_mean": series("visibility_mean"),
        "pressure_msl_mean": series("pressure_msl_mean"),
        "pressure_msl_max": [pressure_max(baseline)] * (days - 1) + [pressure_max(final)],
        "pressure_msl_min": [pressure_min(baseline)] * (days - 1) + [pressure_min(final)],
        "cloud_cover_mean": series("cloud_cover_mean"),
        "precipitation_sum": series("precipitation_sum"),
        "et0_fao_evapotranspiration": series("et0_fao_evapotranspiration"),
        "dew_point_2m_mean": series("dew_point_2m_mean"),
        "wind_speed_10m_max": series("wind_speed_10m_max"),
        "wind_gusts_10m_max": series("wind_gusts_10m_max"),
        "cape_mean": series("cape_mean"),
        "snowfall_sum": series("snowfall_sum"),
        "pm2_5_mean": series("pm2_5_mean"),
        "dust_mean": series("dust_mean"),
        "soil_moisture_0_to_1cm_mean": series("soil_moisture_0_to_1cm_mean"),
    }

    return {
        "start_date": str(daily["time"][0]),
        "end_date": str(daily["time"][-1]),
        "weather_augmented": {
            "elevation": float(final["elevation"]),
            "daily": daily,
        },
    }


def _seed_for(spec: ScenarioSpec, provider: ClimateProvider) -> schema.BirthSeed:
    return schema.BirthSeed(
        timestamp=dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc),
        geo_coords=(0.0, 0.0),
        providers=[provider],
    )


async def synthesize_scenario(provider: ClimateProvider, spec: ScenarioSpec) -> schema.Affinity:
    payload = build_climate_payload(spec)
    seed = _seed_for(spec, provider)

    async def run() -> schema.Affinity:
        affinity = await provider.synthesize(seed, payload)
        identity = affinity.identity.model_copy(update={"name": spec.name})
        return affinity.model_copy(update={"identity": identity})

    return await _with_random_seed_async(spec.name, run)


def _affinity_signature(affinity: schema.Affinity) -> tuple[object, ...]:
    identity = affinity.identity
    return (
        tuple(element.value for element in identity.elements),
        identity.base_hp,
        identity.base_attack,
        identity.base_defense,
        identity.base_sp_attack,
        identity.base_sp_defense,
        identity.base_speed,
        identity.evo_seed.name,
        identity.is_radiant,
        round(affinity.intensity, 4),
        tuple(move.name for move in affinity.moves),
    )


async def _check_replay_determinism(provider: ClimateProvider, spec: ScenarioSpec) -> tuple[bool, bool]:
    payload = build_climate_payload(spec)
    seed = _seed_for(spec, provider)

    state = random.getstate()
    try:
        unseeded = []
        for idx in range(10):
            random.seed(_stable_seed(f"determinism-variant-{idx}"))
            unseeded.append(_affinity_signature(await provider.synthesize(seed, payload)))

        seeded = []
        for _ in range(3):
            random.seed(_stable_seed("determinism-probe"))
            seeded.append(_affinity_signature(await provider.synthesize(seed, payload)))
    finally:
        random.setstate(state)

    return len(set(unseeded)) == 1, len(set(seeded)) == 1


class _NoNetworkClient:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"synthesize accessed client.{name}")


async def _check_synthesize_network_free(spec: ScenarioSpec) -> bool:
    provider = ClimateProvider()
    original_client = provider.client
    provider.client = _NoNetworkClient()
    try:
        await synthesize_scenario(provider, spec)
        return True
    except AssertionError:
        return False
    finally:
        provider.client = original_client
        await provider.teardown()


def _safe_exposed_elements(provider: ClimateProvider) -> tuple[dict[types.VibemonTypeT, str], str | None]:
    try:
        return provider.get_exposed_elements(), None
    except Exception as exc:
        exposed: dict[types.VibemonTypeT, str] = {}
        for annotated_type in provider.exposed_elements:
            if get_origin(annotated_type) is not Annotated:
                continue
            args = get_args(annotated_type)
            if len(args) < 2:
                continue
            element, description = args[0], args[1]
            if not isinstance(element, types.VibemonTypeT) and hasattr(element, "__forward_arg__"):
                try:
                    element = types.VibemonTypeT(getattr(element, "__forward_arg__"))
                except ValueError:
                    pass
            if isinstance(element, types.VibemonTypeT) and isinstance(description, str):
                exposed[element] = description
        return exposed, f"get_exposed_elements() raised {type(exc).__name__}: {exc}"


async def analyze_provider_contract(provider: ClimateProvider, specs: Sequence[ScenarioSpec]) -> ProviderContractReport:
    exposed, exposed_error = _safe_exposed_elements(provider)
    all_types = {element for element in types.VibemonTypeT}
    unseeded_deterministic, seeded_deterministic = await _check_replay_determinism(provider, specs[0])
    synthesize_network_free = await _check_synthesize_network_free(specs[0])

    notes: list[str] = []
    if exposed_error is not None:
        notes.append(exposed_error)
    if not unseeded_deterministic:
        notes.append("synthesize() uses global RNG for moves, evolution seed, and radiant rolls unless callers seed it.")
    if seeded_deterministic:
        notes.append("Replay can be made deterministic by controlling Python's random state around synthesize().")
    if synthesize_network_free:
        notes.append("synthesize() completed against a captured payload without accessing the provider HTTP client.")

    return ProviderContractReport(
        provider_name=provider.name,
        exposed_elements={element.value: description for element, description in exposed.items()},
        missing_exposed_elements=sorted(element.value for element in all_types - set(exposed)),
        birth_seed_columns=list(models.BirthSeed.__table__.columns.keys()),
        birth_snapshot_columns=list(models.BirthSnapshot.__table__.columns.keys()),
        vibemon_columns=list(models.Vibemon.__table__.columns.keys()),
        identity_columns=list(models.Identity.__table__.columns.keys()),
        vibemon_move_columns=list(models.VibemonMove.__table__.columns.keys()),
        unseeded_replay_deterministic=unseeded_deterministic,
        seeded_replay_deterministic=seeded_deterministic,
        synthesize_network_free=synthesize_network_free,
        notes=notes,
    )


def _counter_values(counter: Counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def analyze_move_catalog() -> MoveCatalogReport:
    moves = tuple(climate_moves.MOVES)
    by_type = Counter(move.type.value for move in moves)
    by_category = Counter(move.category.value for move in moves)
    by_level = Counter(str(move.level_requirement) for move in moves)
    accuracy = Counter("never_miss" if move.accuracy is None else f"{move.accuracy:g}" for move in moves)
    priority = Counter(str(move.priority) for move in moves)
    targets = Counter(move.target.value for move in moves)
    effect_kinds: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    weather_sets: Counter[str] = Counter()

    for move in moves:
        for group in move.effects:
            for effect in group.effects:
                effect_kinds[effect.kind] += 1
                if isinstance(effect, schema.StatusInflict):
                    statuses[effect.status.value] += 1
                elif isinstance(effect, schema.WeatherSet):
                    weather_sets[effect.weather.value] += 1

    power_by_category: dict[str, dict[str, float]] = {}
    for category in types.MoveCategoryT:
        powers = [float(move.power) for move in moves if move.category == category and move.power is not None]
        if powers:
            power_by_category[category.value] = _stats(powers)

    condition_count = sum(len(move.behavior.conditions) for move in moves)
    script_count = sum(1 for move in moves if move.behavior.script_id)
    moves_with_effects = sum(1 for move in moves if move.effects)

    findings: list[str] = []
    if len(by_type) == len(types.VibemonTypeT):
        findings.append("Climate moves cover every Vibemon type.")
    if by_level.get("1", 0) > len(moves) * 0.5:
        findings.append("Most climate moves are available at level 1, so starter move pools carry late-game breadth.")
    if max(by_type.values(), default=0) > min(by_type.values(), default=0) * 1.5:
        findings.append("Ground and Psychic currently have larger move catalogs than most other types.")
    if weather_sets:
        findings.append("Weather-setting moves exist, but battle weather mechanics are currently only field state.")
    if condition_count == 0:
        findings.append("Climate moves do not currently exercise declarative conditional move behavior.")
    if script_count == 0:
        findings.append("Climate moves do not use first-party move scripts.")

    return MoveCatalogReport(
        total_moves=len(moves),
        level_one_moves=by_level.get("1", 0),
        by_type=_counter_values(by_type),
        by_category=_counter_values(by_category),
        by_level=_counter_values(by_level),
        power_by_category=power_by_category,
        accuracy_counts=_counter_values(accuracy),
        priority_counts=_counter_values(priority),
        effect_kind_counts=_counter_values(effect_kinds),
        status_counts=_counter_values(statuses),
        weather_set_counts=_counter_values(weather_sets),
        move_targets=_counter_values(targets),
        moves_with_effects=moves_with_effects,
        moves_with_conditions=condition_count,
        moves_with_script_ids=script_count,
        findings=findings,
    )


def _defensive_profile(elements: Sequence[types.VibemonTypeT]) -> dict[str, int]:
    modifiers = [
        element_chart.get_element_effectiveness(attack_type, list(elements))
        for attack_type in types.VibemonTypeT
    ]
    return {
        "weaknesses": sum(1 for modifier in modifiers if modifier > 1.0),
        "double_weaknesses": sum(1 for modifier in modifiers if modifier >= 4.0),
        "resistances": sum(1 for modifier in modifiers if 0.0 < modifier < 1.0),
        "immunities": sum(1 for modifier in modifiers if modifier == 0.0),
    }


def _move_set_report(affinity: schema.Affinity) -> MoveSetReport:
    elements = affinity.identity.elements
    moves = affinity.moves
    damaging = [move for move in moves if move.power is not None and move.category != types.MoveCategoryT.STATUS]
    status = [move for move in moves if move.power is None or move.category == types.MoveCategoryT.STATUS]
    powers = [move.power for move in damaging if move.power is not None]
    coverage_types = 0
    blocked_by_immunity = 0

    for defender_type in types.VibemonTypeT:
        effectiveness = [
            element_chart.get_element_effectiveness(move.type, [defender_type])
            for move in damaging
        ]
        if effectiveness and max(effectiveness) > 1.0:
            coverage_types += 1
        if effectiveness and max(effectiveness) == 0.0:
            blocked_by_immunity += 1

    return MoveSetReport(
        move_count=len(moves),
        damaging_count=len(damaging),
        status_count=len(status),
        stab_count=sum(1 for move in moves if move.type in elements),
        priority_count=sum(1 for move in moves if move.priority > 0),
        average_power=round(_safe_average([float(power) for power in powers]), 4) if powers else None,
        best_power=max(powers) if powers else None,
        offensive_coverage_types=coverage_types,
        blocked_by_immunity_types=blocked_by_immunity,
    )


def _scenario_affinity_report(spec: ScenarioSpec, affinity: schema.Affinity) -> ScenarioAffinityReport:
    identity = affinity.identity
    stats = {
        "hp": identity.base_hp,
        "attack": identity.base_attack,
        "defense": identity.base_defense,
        "sp_attack": identity.base_sp_attack,
        "sp_defense": identity.base_sp_defense,
        "speed": identity.base_speed,
    }
    return ScenarioAffinityReport(
        name=spec.name,
        description=spec.description,
        weather_code=spec.weather_code.name,
        elements=[element.value for element in identity.elements],
        intensity=round(affinity.intensity, 4),
        tier=identity.tier.value,
        battle_role=identity.battle_role.name,
        bst=identity.bst,
        stats=stats,
        defensive_profile=_defensive_profile(identity.elements),
        moves=_move_set_report(affinity),
    )


def analyze_generated_affinities(
    specs: Sequence[ScenarioSpec],
    affinities: Sequence[schema.Affinity],
) -> GeneratedAffinityReport:
    scenario_reports = [
        _scenario_affinity_report(spec, affinity)
        for spec, affinity in zip(specs, affinities, strict=True)
    ]

    element_frequency: Counter[str] = Counter()
    for report in scenario_reports:
        element_frequency.update(report.elements)

    tier_frequency = Counter(report.tier for report in scenario_reports)
    role_frequency = Counter(report.battle_role for report in scenario_reports)
    stat_values = {
        stat: [float(report.stats[stat]) for report in scenario_reports]
        for stat in STAT_KEYS
    }
    intensity_values = [report.intensity for report in scenario_reports]
    dual_type_rate = sum(1 for report in scenario_reports if len(report.elements) == 2) / len(scenario_reports)

    findings: list[str] = []
    max_element_count = max(element_frequency.values(), default=0)
    if max_element_count / max(1, sum(element_frequency.values())) > 0.25:
        most_common = element_frequency.most_common(1)[0][0]
        findings.append(f"{most_common} appears in more than a quarter of generated type slots.")
    missing_types = sorted(set(element.value for element in types.VibemonTypeT) - set(element_frequency))
    if missing_types:
        findings.append("Synthetic climate corpus did not produce: " + ", ".join(missing_types) + ".")
    if dual_type_rate > 0.8:
        findings.append("Dual typing is very common in the synthetic corpus.")
    if max(role_frequency.values(), default=0) / max(1, len(scenario_reports)) > 0.5:
        role = role_frequency.most_common(1)[0][0]
        findings.append(f"Battle role distribution is concentrated around {role}.")
    if max(report.moves.move_count for report in scenario_reports) > 4:
        findings.append("Generated battle move lists exceed Pokemon's four-move benchmark.")

    return GeneratedAffinityReport(
        scenario_count=len(scenario_reports),
        dual_type_rate=round(dual_type_rate, 4),
        element_frequency=_counter_values(element_frequency),
        tier_frequency=_counter_values(tier_frequency),
        battle_role_frequency=_counter_values(role_frequency),
        intensity=_stats(intensity_values),
        stats={stat: _stats(values) for stat, values in stat_values.items()},
        scenarios=scenario_reports,
        findings=findings,
    )


def _vibemon_from_affinity(affinity: schema.Affinity, *, level: int) -> schema.Vibemon:
    moves = tuple(affinity.moves[:4])
    return schema.Vibemon(
        nickname=affinity.identity.name,
        identity=affinity.identity,
        moves=moves,
        level=level,
    )


def _battle_vibemon(vibemon: schema.Vibemon) -> battle_schema.BattleVibemon:
    return battle_schema.BattleVibemon(**vibemon.model_dump())


def _estimated_damage_score(
    user: battle_schema.BattleVibemon,
    target: battle_schema.BattleVibemon,
    move: battle_schema.BattleMove,
) -> float:
    if move.power is None or move.category == types.MoveCategoryT.STATUS:
        return 0.0

    if move.category == types.MoveCategoryT.PHYSICAL:
        attack = user.attack
        defense = target.defense
    else:
        attack = user.sp_attack
        defense = target.sp_defense

    stab = const.STAB_MULTIPLIER if move.type in user.elements else 1.0
    type_effect = element_chart.get_element_effectiveness(move.type, list(target.elements))
    accuracy = 1.0 if move.accuracy is None else move.accuracy
    priority_bonus = 1.05 if move.priority > 0 else 1.0

    return move.power * (attack / max(1, defense)) * stab * type_effect * accuracy * priority_bonus


def _status_effect_score(
    user: battle_schema.BattleVibemon,
    target: battle_schema.BattleVibemon,
    move: battle_schema.BattleMove,
) -> float:
    score = 0.0
    for group in move.effects:
        chance = group.chance
        for effect in group.effects:
            if isinstance(effect, schema.StatusInflict) and target.status == types.StatusConditionT.NONE:
                weights = {
                    types.StatusConditionT.BURN: 18.0,
                    types.StatusConditionT.PARALYSIS: 16.0,
                    types.StatusConditionT.FREEZE: 20.0,
                    types.StatusConditionT.SLEEP: 10.0,
                    types.StatusConditionT.POISON: 12.0,
                    types.StatusConditionT.BAD_POISON: 18.0,
                }
                score += weights.get(effect.status, 0.0) * chance
            elif isinstance(effect, schema.StatChange):
                magnitude = sum(abs(delta) for delta in effect.changes.values())
                if effect.target == "self":
                    score += 8.0 * magnitude * chance
                elif effect.target == "target":
                    score += 7.0 * magnitude * chance
            elif isinstance(effect, schema.Heal) and user.current_hp < user.max_hp * 0.66:
                score += 20.0 * effect.ratio * chance
            elif isinstance(effect, schema.WeatherSet):
                score += 4.0 * chance

    if move.category == types.MoveCategoryT.STATUS and move.accuracy is not None:
        score *= move.accuracy
    return score


def _choose_move(
    policy: PolicyName,
    user: battle_schema.BattleVibemon,
    target: battle_schema.BattleVibemon,
    rng: random.Random,
) -> battle_schema.BattleMove | None:
    usable = [move for move in user.battle_moves if move.pp_current > 0]
    if not usable:
        return None

    damaging = [move for move in usable if move.power is not None and move.category != types.MoveCategoryT.STATUS]
    if policy == "random":
        return rng.choice(usable)

    if policy == "stab_first":
        stab = [move for move in damaging if move.type in user.elements]
        if stab:
            return max(stab, key=lambda move: (_estimated_damage_score(user, target, move), move.power or 0))
        if damaging:
            return max(damaging, key=lambda move: (_estimated_damage_score(user, target, move), move.power or 0))
        return usable[0]

    best_damage = max(damaging, key=lambda move: _estimated_damage_score(user, target, move), default=None)

    if policy == "status_aware":
        best_status = max(usable, key=lambda move: _status_effect_score(user, target, move), default=None)
        best_status_score = _status_effect_score(user, target, best_status) if best_status is not None else 0.0
        best_damage_score = _estimated_damage_score(user, target, best_damage) if best_damage is not None else 0.0
        if best_status is not None and best_status_score >= max(10.0, best_damage_score * 0.6):
            return best_status

    if best_damage is not None:
        return best_damage
    return usable[0]


def _run_battle(
    left: schema.Vibemon,
    right: schema.Vibemon,
    *,
    policy: PolicyName,
    seed: int,
    max_turns: int,
) -> tuple[str | None, int]:
    trainer_a = uuid.uuid5(uuid.NAMESPACE_URL, f"provider-balance:{left.name}:a:{seed}")
    trainer_b = uuid.uuid5(uuid.NAMESPACE_URL, f"provider-balance:{right.name}:b:{seed}")
    battle_rng = random.Random(seed)
    policy_rng = random.Random(f"{policy}:{left.name}:{right.name}:{seed}")
    engine = GameEngine(
        trainer_a=battle_schema.BattleTrainer(
            id=trainer_a,
            username="left",
            team=[_battle_vibemon(left)],
        ),
        trainer_b=battle_schema.BattleTrainer(
            id=trainer_b,
            username="right",
            team=[_battle_vibemon(right)],
        ),
        rng=battle_rng,
    )

    for turn_number in range(1, max_turns + 1):
        left_active = engine.battle.trainer_a.active_vibemon
        right_active = engine.battle.trainer_b.active_vibemon
        left_move = _choose_move(policy, left_active, right_active, policy_rng)
        right_move = _choose_move(policy, right_active, left_active, policy_rng)
        if left_move is None or right_move is None:
            return None, turn_number

        engine.submit_actions(
            [
                actions.MoveAction(trainer=trainer_a, move_name=left_move.name),
                actions.MoveAction(trainer=trainer_b, move_name=right_move.name),
            ]
        )
        if engine.battle.concluded:
            if engine.battle.winner is engine.battle.trainer_a:
                return left.name, turn_number
            if engine.battle.winner is engine.battle.trainer_b:
                return right.name, turn_number
            return None, turn_number

    return None, max_turns


def analyze_battles(
    affinities: Sequence[schema.Affinity],
    *,
    policies: Sequence[PolicyName],
    battle_rounds: int,
    max_turns: int,
    level: int,
) -> BattleReport:
    vibemon = [_vibemon_from_affinity(affinity, level=level) for affinity in affinities]
    records: list[tuple[str, str, str, str | None, int]] = []

    for policy in policies:
        for i, left in enumerate(vibemon):
            for right in vibemon[i + 1:]:
                for round_idx in range(battle_rounds):
                    seed = 10_000 * round_idx + i * 101 + len(records)
                    winner, turns = _run_battle(left, right, policy=policy, seed=seed, max_turns=max_turns)
                    records.append((policy, left.name, right.name, winner, turns))
                    winner, turns = _run_battle(right, left, policy=policy, seed=seed + 1, max_turns=max_turns)
                    records.append((policy, right.name, left.name, winner, turns))

    stats_by_scenario = {
        vibemon_instance.name: {"wins": 0, "losses": 0, "draws": 0, "turns": []}
        for vibemon_instance in vibemon
    }
    by_policy: dict[str, Counter[str]] = {policy: Counter() for policy in policies}
    draws_by_policy: Counter[str] = Counter()

    for policy, left, right, winner, turns in records:
        stats_by_scenario[left]["turns"].append(turns)
        stats_by_scenario[right]["turns"].append(turns)
        if winner is None:
            stats_by_scenario[left]["draws"] += 1
            stats_by_scenario[right]["draws"] += 1
            draws_by_policy[policy] += 1
        else:
            loser = right if winner == left else left
            stats_by_scenario[winner]["wins"] += 1
            stats_by_scenario[loser]["losses"] += 1
            by_policy[policy][winner] += 1

    scenario_summaries: list[BattleScenarioSummary] = []
    for scenario_name, values in stats_by_scenario.items():
        total = values["wins"] + values["losses"] + values["draws"]
        scenario_summaries.append(
            BattleScenarioSummary(
                scenario=scenario_name,
                wins=values["wins"],
                losses=values["losses"],
                draws=values["draws"],
                win_rate=round(values["wins"] / total, 4) if total else 0.0,
                average_turns=round(_safe_average(values["turns"]), 4),
            )
        )

    scenario_summaries.sort(key=lambda item: item.win_rate, reverse=True)
    dominant = [item.scenario for item in scenario_summaries if item.win_rate >= 0.7]
    weak = [item.scenario for item in scenario_summaries if item.win_rate <= 0.3]

    findings: list[str] = []
    if dominant:
        findings.append("Dominant synthetic scenarios: " + ", ".join(dominant) + ".")
    if weak:
        findings.append("Underperforming synthetic scenarios: " + ", ".join(weak) + ".")
    if any(summary.draws for summary in scenario_summaries):
        findings.append("Some simulations hit the turn limit or ran out of usable PP.")

    return BattleReport(
        policies=list(policies),
        simulations=len(records),
        max_turns=max_turns,
        by_scenario=scenario_summaries,
        by_policy=[
            BattlePolicySummary(
                policy=policy,
                wins_by_scenario=_counter_values(by_policy[policy]),
                draws=draws_by_policy[policy],
            )
            for policy in policies
        ],
        dominant_scenarios=dominant,
        weak_scenarios=weak,
        findings=findings,
    )


def _detect_engine_gaps() -> list[str]:
    from app.battle.rules import turn_order
    from app.battle import mechanics

    gaps: list[str] = []
    turn_order_source = inspect.getsource(turn_order._priority)
    if "priority_delta" not in turn_order_source:
        gaps.append("Declarative conditional priority exists but is not applied by turn order.")

    weather_module = getattr(mechanics, "weather", None)
    if weather_module is None or "placeholder" in (weather_module.__doc__ or "").lower():
        gaps.append("Weather mechanics are placeholders, so weather-setting moves do not yet modify damage or speed.")

    return gaps


def _scorecard(
    contract: ProviderContractReport,
    move_catalog: MoveCatalogReport,
    generated: GeneratedAffinityReport,
    battle: BattleReport,
) -> list[ScorecardItem]:
    contract_status = "pass"
    contract_summary = "Provider exposes all types and synthesize replays from captured payloads."
    if not contract.seeded_replay_deterministic or not contract.synthesize_network_free:
        contract_status = "fail"
        contract_summary = "Provider replay contract has deterministic or network-purity failures."
    elif not contract.unseeded_replay_deterministic:
        contract_status = "watch"
        contract_summary = "Replay purity is good, but synthesize depends on caller-controlled RNG."

    element_status = "pass"
    element_summary = "Synthetic corpus produces a broad type mix."
    if generated.dual_type_rate > 0.85:
        element_status = "watch"
        element_summary = "Dual typing is high enough to compress defensive identity."
    if len(generated.element_frequency) < len(types.VibemonTypeT) * 0.6:
        element_status = "watch"
        element_summary = "Weather-only signals leave several Pokemon-style habitat types underrepresented."

    stat_status = "pass"
    stat_summary = "Stat generation stays inside schema bounds and produces multiple roles."
    if generated.battle_role_frequency:
        top_role_count = max(generated.battle_role_frequency.values())
        if top_role_count / generated.scenario_count > 0.5:
            stat_status = "watch"
            stat_summary = "Role output is concentrated; provider may not create enough battle shapes."

    move_status = "pass"
    move_summary = "Move catalog covers all types and has physical, special, and status choices."
    if move_catalog.level_one_moves / move_catalog.total_moves > 0.5:
        move_status = "watch"
        move_summary = "Level 1 access is very broad, making provider-assigned starters feel late-game."

    battle_status = "pass"
    battle_summary = "No synthetic scenario dominates the battle simulation band."
    if battle.dominant_scenarios or battle.weak_scenarios:
        battle_status = "watch"
        battle_summary = "Simulations expose dominant or weak generated archetypes."

    return [
        ScorecardItem(axis="provider_contract", status=contract_status, summary=contract_summary),
        ScorecardItem(axis="element_ecology", status=element_status, summary=element_summary),
        ScorecardItem(axis="stat_economy", status=stat_status, summary=stat_summary),
        ScorecardItem(axis="move_ecology", status=move_status, summary=move_summary),
        ScorecardItem(axis="battle_impact", status=battle_status, summary=battle_summary),
    ]


def _top_findings(
    contract: ProviderContractReport,
    move_catalog: MoveCatalogReport,
    generated: GeneratedAffinityReport,
    battle: BattleReport,
) -> list[str]:
    findings = [
        *contract.notes,
        *move_catalog.findings,
        *generated.findings,
        *battle.findings,
        *_detect_engine_gaps(),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for finding in findings:
        if finding not in seen:
            unique.append(finding)
            seen.add(finding)
    return unique


async def build_report(
    *,
    scenario_limit: int | None = None,
    battle_rounds: int = 1,
    max_turns: int = 30,
    level: int = 50,
    policies: Sequence[PolicyName] = ("best_damage", "stab_first", "status_aware", "random"),
) -> ProviderBalanceReport:
    specs = SCENARIOS[:scenario_limit] if scenario_limit is not None else SCENARIOS
    provider = ClimateProvider()
    try:
        contract = await analyze_provider_contract(provider, specs)
        move_catalog = analyze_move_catalog()
        affinities = [await synthesize_scenario(provider, spec) for spec in specs]
        generated = analyze_generated_affinities(specs, affinities)
        battle = analyze_battles(
            affinities,
            policies=policies,
            battle_rounds=battle_rounds,
            max_turns=max_turns,
            level=level,
        )
        scorecard = _scorecard(contract, move_catalog, generated, battle)
        top_findings = _top_findings(contract, move_catalog, generated, battle)

        return ProviderBalanceReport(
            generated_at=dt.datetime.now(tz=dt.timezone.utc).isoformat(),
            benchmark=[
                "Pokemon Scarlet/Violet style: curated type roles, strong type chart counterplay, four active moves.",
                "Gen IX inspiration: powerful special mechanics are constrained by explicit battle rules and counterplay.",
                "Pokemon Champions framing: battles are shaped by Pokemon, types, abilities, moves, and items.",
            ],
            contract=contract,
            move_catalog=move_catalog,
            generated_affinities=generated,
            battle=battle,
            scorecard=scorecard,
            pokemon_benchmark_differences=[
                "Vibemon providers generate species identity from real-world signals instead of selecting curated species.",
                "No abilities, held items, natures, EVs, IVs, or Terastal equivalent are currently modeled.",
                "Battle weather can be set as field state, but first-party weather mechanics are placeholders.",
                f"Provider-assigned move lists can exceed Pokemon's four-move battle limit; climate samples return up to "
                f"{max(report.moves.move_count for report in generated.scenarios)} moves.",
                "Status and stat-stage effects exist, but some Pokemon-like durations and immunities are simplified.",
            ],
            top_findings=top_findings,
        )
    finally:
        await provider.teardown()


def _format_counter(counter: dict[str, int], *, limit: int | None = None) -> str:
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    if limit is not None:
        items = items[:limit]
    return ", ".join(f"{key}={value}" for key, value in items)


def print_text_report(report: ProviderBalanceReport) -> None:
    print("Provider Balance Analysis")
    print("=" * 80)
    print(f"Generated: {report.generated_at}")
    print()

    print("Scorecard")
    for item in report.scorecard:
        print(f"- {item.axis}: {item.status.upper()} - {item.summary}")
    print()

    print("Top Findings")
    for finding in report.top_findings:
        print(f"- {finding}")
    print()

    print("Provider Contract")
    print(f"- provider: {report.contract.provider_name}")
    print(f"- exposed elements: {len(report.contract.exposed_elements)}")
    print(f"- missing exposed elements: {', '.join(report.contract.missing_exposed_elements) or 'none'}")
    print(f"- unseeded replay deterministic: {report.contract.unseeded_replay_deterministic}")
    print(f"- seeded replay deterministic: {report.contract.seeded_replay_deterministic}")
    print(f"- synthesize network-free: {report.contract.synthesize_network_free}")
    print()

    print("Move Catalog")
    print(f"- total moves: {report.move_catalog.total_moves}")
    print(f"- level 1 moves: {report.move_catalog.level_one_moves}")
    print(f"- by category: {_format_counter(report.move_catalog.by_category)}")
    print(f"- top type counts: {_format_counter(report.move_catalog.by_type, limit=8)}")
    print(f"- effects: {_format_counter(report.move_catalog.effect_kind_counts)}")
    print(f"- statuses: {_format_counter(report.move_catalog.status_counts)}")
    print()

    print("Generated Affinities")
    print(f"- scenarios: {report.generated_affinities.scenario_count}")
    print(f"- dual type rate: {report.generated_affinities.dual_type_rate:.2%}")
    print(f"- elements: {_format_counter(report.generated_affinities.element_frequency)}")
    print(f"- tiers: {_format_counter(report.generated_affinities.tier_frequency)}")
    print(f"- roles: {_format_counter(report.generated_affinities.battle_role_frequency)}")
    for stat_name, stat_report in report.generated_affinities.stats.items():
        print(
            f"- {stat_name}: min={stat_report['min']:.0f}, avg={stat_report['avg']:.1f}, "
            f"median={stat_report['median']:.0f}, max={stat_report['max']:.0f}"
        )
    print()

    print("Scenario Outputs")
    for scenario in report.generated_affinities.scenarios:
        print(
            f"- {scenario.name}: {'/'.join(scenario.elements)} "
            f"BST={scenario.bst} role={scenario.battle_role} "
            f"intensity={scenario.intensity:.2f} moves={scenario.moves.move_count} "
            f"STAB={scenario.moves.stab_count}"
        )
    print()

    print("Battle Simulation")
    print(f"- simulations: {report.battle.simulations}")
    print(f"- policies: {', '.join(report.battle.policies)}")
    print(f"- dominant: {', '.join(report.battle.dominant_scenarios) or 'none'}")
    print(f"- weak: {', '.join(report.battle.weak_scenarios) or 'none'}")
    for scenario in report.battle.by_scenario:
        print(
            f"- {scenario.scenario}: win_rate={scenario.win_rate:.2%}, "
            f"W-L-D={scenario.wins}-{scenario.losses}-{scenario.draws}, "
            f"avg_turns={scenario.average_turns:.1f}"
        )
    print()

    print("Pokemon Benchmark Differences")
    for difference in report.pokemon_benchmark_differences:
        print(f"- {difference}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze provider contribution to Vibemon balance.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", type=str, default=None, help="Optional path for the generated report.")
    parser.add_argument("--scenario-limit", type=int, default=None)
    parser.add_argument("--battle-rounds", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=30)
    parser.add_argument("--level", type=int, default=50)
    parser.add_argument(
        "--policies",
        nargs="+",
        default=["best_damage", "stab_first", "status_aware", "random"],
        choices=("best_damage", "stab_first", "status_aware", "random"),
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(30))
    report = await build_report(
        scenario_limit=args.scenario_limit,
        battle_rounds=args.battle_rounds,
        max_turns=args.max_turns,
        level=args.level,
        policies=args.policies,
    )

    if args.format == "json":
        rendered = json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True)
    else:
        from io import StringIO
        from contextlib import redirect_stdout

        buffer = StringIO()
        with redirect_stdout(buffer):
            print_text_report(report)
        rendered = buffer.getvalue()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(rendered)
            if not rendered.endswith("\n"):
                fh.write("\n")
    else:
        print(rendered)


if __name__ == "__main__":
    asyncio.run(main())
