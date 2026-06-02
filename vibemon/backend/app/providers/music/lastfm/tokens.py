"""Last.fm auth token and session helpers."""

import hashlib

import niquests
import pydantic

from app.settings import Settings

# auth.getSession before the user approves in the browser (desktop-style flow).
_PENDING_SESSION_ERROR_CODES = frozenset({14, 16})


class LastFmApiError(RuntimeError):
    """Raised when the Last.fm JSON API returns an error object."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Last.fm API error {code}: {message}")


class LastFmTokenResponse(pydantic.BaseModel):
    token: str


class LastFmSessionResponse(pydantic.BaseModel):
    name: str
    key: str
    subscriber: int = 0


def _raise_api_error(payload: dict[str, object], *, context: str) -> None:
    if "error" not in payload:
        return
    code = int(str(payload["error"]))
    message = str(payload.get("message", context))
    raise LastFmApiError(code, message)


def api_signature(params: dict[str, str], *, api_secret: str) -> str:
    """Build the Last.fm api_sig parameter."""
    payload = "".join(f"{key}{value}" for key, value in sorted(params.items()))
    digest = hashlib.md5(f"{api_secret}{payload}{api_secret}".encode()).hexdigest()
    return digest


async def get_token() -> str:
    """Request a web-auth token for browser authorization."""
    settings = Settings.load()
    api_key = settings.secrets.lastfm_key.get_secret_value()
    api_secret = settings.secrets.lastfm_secret.get_secret_value()
    params = {
        "method": "auth.getToken",
        "api_key": api_key,
    }
    params["api_sig"] = api_signature(params, api_secret=api_secret)
    async with niquests.AsyncSession(base_url="https://ws.audioscrobbler.com/2.0/") as session:
        response = await session.get("/", params={**params, "format": "json"})
        response.raise_for_status()
        payload = response.json()
        _raise_api_error(payload, context="auth.getToken failed")
        return LastFmTokenResponse.model_validate(payload).token


async def get_session(token: str) -> LastFmSessionResponse:
    """Exchange an authorized web-auth token for a session key."""
    settings = Settings.load()
    api_key = settings.secrets.lastfm_key.get_secret_value()
    api_secret = settings.secrets.lastfm_secret.get_secret_value()
    params = {
        "method": "auth.getSession",
        "api_key": api_key,
        "token": token,
    }
    params["api_sig"] = api_signature(params, api_secret=api_secret)
    async with niquests.AsyncSession(base_url="https://ws.audioscrobbler.com/2.0/") as session:
        response = await session.get("/", params={**params, "format": "json"})
        response.raise_for_status()
        payload = response.json()
        _raise_api_error(payload, context="auth.getSession failed")
        return LastFmSessionResponse.model_validate(payload["session"])


async def try_get_session(token: str) -> LastFmSessionResponse | None:
    """Exchange a web-auth token once the user has approved in the browser.

    Returns ``None`` while Last.fm still reports the token as unauthorized
    (desktop-style flow where the callback redirect never fires).
    """
    try:
        return await get_session(token)
    except LastFmApiError as exc:
        if exc.code in _PENDING_SESSION_ERROR_CODES:
            return None
        raise
