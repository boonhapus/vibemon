"""Fitness birth provider catalog stub."""

from typing import ClassVar

from app.domains.move.types import VibemonTypeT
from app.providers import catalog_schema as catalog
from app.providers.base import UnimplementedProvider


class FitnessProvider(UnimplementedProvider):
    """
    A Vibemon carries the rhythm your body was keeping before it hatched.

    One hatched after deep recovery weeks reads differently from one shaped by
    high-strain training blocks - same wrist, different rhythm, different
    creature.
    """

    name = "fitness"
    display_label = "FITNESS"
    tagline = "Sleep, strain, and the week before hatching."

    exposed_elements: ClassVar[list[tuple[VibemonTypeT, str]]] = [
        (VibemonTypeT.NORMAL, "balanced activity and steady recovery"),
        (VibemonTypeT.FIGHTING, "high strain and impact training blocks"),
        (VibemonTypeT.GRASS, "outdoor endurance and long steady sessions"),
        (VibemonTypeT.WATER, "fluid mobility and low-impact recovery"),
        (VibemonTypeT.ICE, "cold exposure and low resting trends"),
        (VibemonTypeT.BUG, "high-frequency short sessions"),
        (VibemonTypeT.STEEL, "strength blocks and disciplined routines"),
        (VibemonTypeT.PSYCHIC, "meditative recovery and sleep depth"),
    ]

    requirements = (
        catalog.SecretGroupRequirement(
            id="fitness.platform",
            label="Connect a health platform",
            description="Link at least one wearable or health app when this provider launches.",
            branches=(
                catalog.OAuth2LinkRequirement(
                    id="fitness.whoop",
                    label="Link Whoop",
                    description="Recovery, sleep, and strain from Whoop.",
                    service="whoop",
                    secret_kinds=("fitness.whoop.token",),
                    authorize_path="/fitness/whoop/authorize",
                ),
                catalog.OAuth2LinkRequirement(
                    id="fitness.oura",
                    label="Link Oura",
                    description="Sleep, readiness, and activity from Oura.",
                    service="oura",
                    secret_kinds=("fitness.oura.token",),
                    authorize_path="/fitness/oura/authorize",
                ),
                catalog.OAuth2LinkRequirement(
                    id="fitness.strava",
                    label="Link Strava",
                    description="Runs, rides, and movement load from Strava.",
                    service="strava",
                    secret_kinds=("fitness.strava.access_token",),
                    authorize_path="/fitness/strava/authorize",
                ),
            ),
        ),
    )
    data_sources = (
        catalog.DataSourceInfo(name="Wearables and health platforms", description="Whoop, Oura, Strava, and peers."),
    )
