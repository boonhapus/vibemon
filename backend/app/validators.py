from app import utils


def validate_unit_interval(v: float) -> float:
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"Value must be between 0.0 and 1.0, got {v}")
    return v


def ensure_between_5_255(v: int) -> int:
    return int(utils.clamp(v, minimum=5, maximum=255))


def ensure_between_abs_7(v: int) -> int:
    return int(utils.clamp(v, minimum=7, maximum=7))
