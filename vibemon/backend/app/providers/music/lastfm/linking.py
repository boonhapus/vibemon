"""Last.fm web-auth authorize URL and CSRF state helpers."""

from urllib.parse import urlencode, urlparse
import datetime as dt
import hashlib
import hmac
import json
import uuid

from app.settings import Settings

_STATE_TTL = dt.timedelta(minutes=10)


def _callback_url() -> str:
    return str(Settings.load().lastfm.callback)


def _state_secret() -> bytes:
    settings = Settings.load()
    return settings.secrets.lastfm_secret.get_secret_value().encode("utf-8")


def build_state(trainer_id: uuid.UUID, token: str, *, now: dt.datetime | None = None) -> str:
    """Build an HMAC-signed web-auth state token."""
    issued_at = now or dt.datetime.now(tz=dt.UTC)
    payload = {
        "trainer_id": str(trainer_id),
        "token": token,
        "exp": int((issued_at + _STATE_TTL).timestamp()),
    }
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(_state_secret(), body, hashlib.sha256).hexdigest()
    return f"{signature}.{body.decode('utf-8')}"


def parse_state(state: str) -> tuple[uuid.UUID, str]:
    """Validate web-auth state and return the trainer id and pending token."""
    try:
        signature, body_text = state.split(".", maxsplit=1)
        body = body_text.encode("utf-8")
    except ValueError as exc:
        raise ValueError("Invalid Last.fm auth state.") from exc

    expected = hmac.new(_state_secret(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid Last.fm auth state signature.")

    payload = json.loads(body)
    if int(payload["exp"]) < int(dt.datetime.now(tz=dt.UTC).timestamp()):
        raise ValueError("Last.fm auth state expired.")

    return uuid.UUID(str(payload["trainer_id"])), str(payload["token"])


def build_callback_url() -> str:
    """Return the Last.fm web-auth callback URL.

    Must match the callback URL registered on the Last.fm API account exactly.
    Do not append query parameters — trainer context lives in the signed cookie
    set by ``/lastfm/authorize``.
    """
    return _callback_url()


def build_local_authorize_url(trainer_id: uuid.UUID) -> str:
    """Return the local authorize entrypoint for browser linking."""
    parsed = urlparse(_callback_url())
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return f"{origin}/lastfm/authorize?trainer_id={trainer_id}"


def build_authorize_url(trainer_id: uuid.UUID, token: str) -> str:
    """Return the Last.fm browser authorization URL for a trainer."""
    settings = Settings.load()
    query = urlencode(
        {
            "api_key": settings.secrets.lastfm_key.get_secret_value(),
            "token": token,
            "cb": build_callback_url(),
        }
    )
    return f"https://www.last.fm/api/auth/?{query}"
