from __future__ import annotations

from datetime import datetime

from app.plugins.protocol import (
    ColorShift,
    Context,
    Delta,
    VisualDelta,
)


class ClimateProvider:
    name = "climate"
    affinities = {"stat", "visual"}

    async def intensity(self, context: Context) -> float:
        return 0.0

    async def contribute(self, context: Context) -> Delta:
        ts = datetime.fromisoformat(context.timestamp)
        hour_ratio = (ts.hour % 24) / 24.0
        is_night = ts.hour < 6 or ts.hour >= 20

        if is_night:
            hue = -15.0 + hour_ratio * 10.0
            lightness = -0.08
        else:
            hue = 5.0 + hour_ratio * 10.0
            lightness = 0.04

        color_shifts: dict[str, ColorShift] = {}
        color_shifts["primary"] = ColorShift(
            hue_rotation=hue,
            lightness_adjust=lightness,
        )

        stat_deltas = self._compute_stat_deltas(ts, context)

        return Delta(
            delta_stats=stat_deltas,
            delta_visual=VisualDelta(color_shifts=color_shifts),
            delta_level=0,
        )

    def _compute_stat_deltas(
        self, ts: datetime, context: Context
    ) -> dict[str, int]:
        hour_ratio = (ts.hour % 24) / 24.0
        weekday_ratio = (ts.weekday() + 1) / 7.0
        month_ratio = (ts.month % 12) / 12.0
        second_ratio = (ts.second % 60) / 60.0

        lat = 0.0
        lon = 0.0
        if context.location:
            parts = context.location.split(",")
            if len(parts) == 2:
                try:
                    lat = float(parts[0])
                    lon = float(parts[1])
                except ValueError:
                    pass

        factor_scale = 0.4
        base_offset = 0.3

        return {
            "max_hp": int((base_offset + factor_scale * hour_ratio) * 255),
            "attack": int((base_offset + factor_scale * weekday_ratio) * 255),
            "defense": int((base_offset + factor_scale * (abs(lat) / 90.0)) * 255),
            "sp_attack": int((base_offset + factor_scale * month_ratio) * 255),
            "sp_defense": int(
                (base_offset + factor_scale * ((abs(lon) % 180) / 180.0)) * 255
            ),
            "speed": int((base_offset + factor_scale * second_ratio) * 255),
        }
