from __future__ import annotations

from app.plugins.protocol import (
    ColorShift,
    Context,
    Delta,
    SourceData,
    VisualDelta,
)


class SpotifyProvider:
    name = "spotify"
    affinities = {"stat", "visual"}

    async def intensity(self, context: Context) -> float:
        return 0.0

    async def contribute(self, context: Context) -> Delta:
        source = context.source_data.get(self.name)
        if source is None:
            return Delta()

        payload = source.payload
        mood = payload.get("mood", "neutral")

        color_shifts: dict[str, ColorShift] = {}
        mood_hue = {"energetic": 10.0, "calm": -10.0, "melancholic": -5.0}.get(
            mood, 0.0
        )
        mood_lightness = {"energetic": 0.05, "calm": -0.03, "melancholic": -0.06}.get(
            mood, 0.0
        )
        color_shifts["primary"] = ColorShift(
            hue_rotation=mood_hue,
            lightness_adjust=mood_lightness,
        )

        minutes = payload.get("listening_minutes", 0)
        track_count = payload.get("track_count", 0)

        stat_deltas: dict[str, int] = {}
        if minutes > 0 or track_count > 0:
            energy = min(1.0, minutes / 120.0)
            stat_deltas["speed"] = int(energy * 30)
            stat_deltas["sp_attack"] = int(min(1.0, track_count / 20.0) * 25)

        return Delta(
            delta_stats=stat_deltas,
            delta_visual=VisualDelta(color_shifts=color_shifts),
            delta_level=0,
        )
