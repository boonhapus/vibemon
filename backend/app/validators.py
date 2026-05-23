from app import utils


def ensure_between_abs_7(v: int) -> int:
    return int(utils.clamp(v, minimum=7, maximum=7))
