"""Major aspect detection from ecliptic longitudes."""

from dataclasses import dataclass

from app.core.math import angular_distance
from app.providers.celestial.ephemeris.models import AspectObservation


@dataclass(frozen=True, slots=True)
class AspectRule:
    name: str
    angle: float
    orb: float


ASPECT_RULES: tuple[AspectRule, ...] = (
    AspectRule(name="conjunction", angle=0.0, orb=8.0),
    AspectRule(name="sextile", angle=60.0, orb=4.0),
    AspectRule(name="square", angle=90.0, orb=6.0),
    AspectRule(name="trine", angle=120.0, orb=6.0),
    AspectRule(name="opposition", angle=180.0, orb=8.0),
)


def detect_aspects(body_longitudes: dict[str, float]) -> tuple[AspectObservation, ...]:
    names = sorted(body_longitudes)
    aspects: list[AspectObservation] = []

    for index, body_a in enumerate(names):
        for body_b in names[index + 1 :]:
            separation = angular_distance(body_longitudes[body_a], body_longitudes[body_b])
            for rule in ASPECT_RULES:
                orb = abs(separation - rule.angle)
                if orb <= rule.orb:
                    aspects.append(
                        AspectObservation(
                            body_a=body_a,
                            body_b=body_b,
                            aspect=rule.name,
                            orb_deg=orb,
                        )
                    )
                    break

    return tuple(aspects)
