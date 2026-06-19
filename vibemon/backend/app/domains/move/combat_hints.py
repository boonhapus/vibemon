"""Human-readable combat hints derived from move data."""

from app.domains.move import entity as move_entity


def effect_hint(effect: object, *, chance: float) -> str | None:
    lead = f"{int(chance * 100)}% chance to " if chance < 1.0 else ""
    match effect:
        case move_entity.StatusInflict(status=status):
            label = status.value.replace("_", " ")
            return f"{lead}inflict {label}."
        case move_entity.StatChange(changes=changes):
            parts = [f"{'+' if delta > 0 else ''}{delta} {stat.replace('_', ' ')}" for stat, delta in changes.items()]
            return f"{lead}{', '.join(parts)}."
        case move_entity.Drain(ratio=ratio):
            return f"{lead}drain {int(ratio * 100)}% of damage as HP."
        case move_entity.Recoil(ratio=ratio, basis="max_hp"):
            return f"{lead}recoil {int(ratio * 100)}% max HP."
        case move_entity.Recoil(ratio=ratio):
            return f"{lead}recoil {int(ratio * 100)}% of damage."
        case move_entity.WeatherSet(weather=weather):
            return f"{lead}set {weather.value.replace('_', ' ')} weather."
        case move_entity.Heal(ratio=ratio):
            return f"{lead}heal {int(ratio * 100)}% max HP."
        case _:
            return None


def move_combat_hints(move: move_entity.Move) -> tuple[str, ...]:
    hints: list[str] = []
    if move.accuracy is None:
        hints.append("Never misses.")
    elif move.accuracy < 1.0:
        hints.append(f"Accuracy {round(move.accuracy * 100)}%.")
    if move.priority != 0:
        sign = "+" if move.priority > 0 else ""
        hints.append(f"Priority {sign}{move.priority}.")
    for group in move.effects:
        for effect in group.effects:
            text = effect_hint(effect, chance=group.chance)
            if text:
                hints.append(text)
    return tuple(hints)
