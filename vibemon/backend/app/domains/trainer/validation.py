"""Trainer username validation shared by HTTP and future interfaces."""

TRAINER_USERNAME_MIN = 2
TRAINER_USERNAME_MAX = 16


def normalize_username(value: str) -> str:
    """Canonical trainer name for storage and lookup (case-insensitive identity)."""
    return value.strip().casefold()


def validate_username(value: str) -> str:
    """Return a normalized username or raise ``ValueError`` with a user-facing message."""
    normalized = normalize_username(value)
    if not normalized:
        raise ValueError("Enter a name other Trainers can call you.")
    if len(normalized) < TRAINER_USERNAME_MIN or len(normalized) > TRAINER_USERNAME_MAX:
        raise ValueError(f"Use {TRAINER_USERNAME_MIN}-{TRAINER_USERNAME_MAX} characters.")
    return normalized
