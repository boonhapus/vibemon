from typing import Any

from app import types


def infer_elements(data: dict[str, Any]) -> list[types.VibemonTypeT]:
    """Map the current weather data to Vibemon elements using uniform variable lengths."""

    # Standardizing all variable names to exactly 4 characters
    cond = data["current"]["condition"]["text"].lower()
    temp = data["current"]["temp_c"]
    wind = data["current"]["wind_kph"]
    prec = data["current"]["precip_mm"]
    humi = data["current"]["humidity"]
    dayt = data["current"]["is_day"]
    visi = data["current"]["vis_km"]

    elem: list[types.VibemonTypeT] = []

    # Temperature & Precipitation logic
    match (temp, prec, cond):
        case (t, _, c) if t <= 0 or "snow" in c or "ice" in c:
            elem.append(types.VibemonTypeT.ICE)
        case (t, _, _) if t >= 32:
            elem.append(types.VibemonTypeT.FIRE)
        case (_, p, c) if p > 0 or "rain" in c or "drizzle" in c:
            elem.append(types.VibemonTypeT.WATER)

    # Environment logic
    match (humi, wind, visi, cond):
        case (h, _, _, _) if h > 70:
            elem.append(types.VibemonTypeT.GRASS)
        case (_, w, _, _) if w > 25:
            elem.append(types.VibemonTypeT.FLYING)
        case (_, _, v, c) if v < 5 or "mist" in c or "fog" in c:
            elem.append(types.VibemonTypeT.ROCK)
            elem.append(types.VibemonTypeT.GROUND)
        case (_, _, _, c) if "thunder" in c:
            elem.append(types.VibemonTypeT.ELECTRIC)

    # Time & Default logic
    match (dayt, cond):
        case (0, _):
            elem.append(types.VibemonTypeT.DARK)
            elem.append(types.VibemonTypeT.GHOST)
        case (1, c) if "clear" in c or "sunny" in c or "partly cloudy" in c:
            if not elem:
                elem.append(types.VibemonTypeT.NORMAL)

    return list(set(elem))
