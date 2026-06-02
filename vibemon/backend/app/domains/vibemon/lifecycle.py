"""Pure lifecycle transition policy for Vibemon presentation readiness."""

from app.domains.vibemon.entity import Vibemon
from app.domains.vibemon.types import VibemonLifecycleT

ALLOWED_CHRISTEN_LIFECYCLES: frozenset[VibemonLifecycleT] = frozenset(
    {
        VibemonLifecycleT.BORN,
        VibemonLifecycleT.CHRISTENED,
        VibemonLifecycleT.MANIFESTED,
    }
)

ALLOWED_MANIFEST_LIFECYCLES: frozenset[VibemonLifecycleT] = frozenset(
    {
        VibemonLifecycleT.CHRISTENED,
        VibemonLifecycleT.MANIFESTED,
    }
)


def require_can_manifest(vibemon: Vibemon) -> None:
    if vibemon.lifecycle not in ALLOWED_MANIFEST_LIFECYCLES:
        raise ValueError(f"Cannot manifest Vibemon {vibemon.id} from {vibemon.lifecycle}; must be CHRISTENED first.")
