"""Solar phase bands and twilight prevalence from birth instant."""

from dataclasses import dataclass
import datetime as dt

from astral import Observer
from astral.sun import sun

from app.domains.generation import types as generation_types


@dataclass(frozen=True, slots=True)
class SolarBand:
    phase: generation_types.SolarPhase
    twilight_prevalence: float


def solar_band(
    *,
    timestamp: dt.datetime,
    latitude: float,
    longitude: float,
    timezone: dt.timezone,
) -> SolarBand:
    """Return local solar phase and how deep into dawn/dusk twilight the birth sits."""
    observer = Observer(latitude=latitude, longitude=longitude)
    local_time = timestamp.astimezone(timezone)

    try:
        solar = sun(observer, date=local_time.date(), tzinfo=timezone)
    except ValueError:
        phase = generation_types.SolarPhase.NIGHT if abs(latitude) > 66.0 else generation_types.SolarPhase.DAY
        return SolarBand(phase=phase, twilight_prevalence=1.0 if phase is generation_types.SolarPhase.NIGHT else 0.0)

    if local_time < solar["dawn"]:
        return SolarBand(phase=generation_types.SolarPhase.NIGHT, twilight_prevalence=1.0)

    if local_time < solar["sunrise"]:
        span = (solar["sunrise"] - solar["dawn"]).total_seconds()
        elapsed = (local_time - solar["dawn"]).total_seconds()
        return SolarBand(
            phase=generation_types.SolarPhase.DAWN,
            twilight_prevalence=_twilight_prevalence(elapsed, span),
        )

    if local_time < solar["sunset"]:
        return SolarBand(phase=generation_types.SolarPhase.DAY, twilight_prevalence=1.0)

    if local_time < solar["dusk"]:
        span = (solar["dusk"] - solar["sunset"]).total_seconds()
        elapsed = (local_time - solar["sunset"]).total_seconds()
        return SolarBand(
            phase=generation_types.SolarPhase.DUSK,
            twilight_prevalence=_twilight_prevalence(elapsed, span),
        )

    return SolarBand(phase=generation_types.SolarPhase.NIGHT, twilight_prevalence=1.0)


def _twilight_prevalence(elapsed_seconds: float, span_seconds: float) -> float:
    if span_seconds <= 0:
        return 1.0
    center = span_seconds / 2.0
    distance = abs(elapsed_seconds - center)
    return max(0.0, 1.0 - distance / center)
