"""Starlette routes for local Last.fm web-auth linking."""

from urllib.parse import urlparse
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route

from app.providers.music.lastfm import linking, tokens
from app.settings import Settings
from app.storage.database import engine as db_engine
from app.storage.database import models, trainer_links_repo

_STATE_COOKIE = "lastfm_auth_state"
_POLL_INTERVAL_S = 2.0
_POLL_ATTEMPTS = 300

_link_event = asyncio.Event()
_link_message: str | None = None
_link_poll_tasks: set[asyncio.Task[None]] = set()


def reset_link_waiter() -> None:
    """Clear completion state before starting a new browser link."""
    global _link_message
    _link_message = None
    _link_event.clear()


def signal_link_complete(message: str) -> None:
    """Notify ``wait_for_link`` that a trainer Last.fm session was stored."""
    global _link_message
    _link_message = message
    _link_event.set()


async def wait_for_link(*, timeout: float) -> str | None:
    """Block until linking completes or ``timeout`` seconds elapse."""
    try:
        await asyncio.wait_for(_link_event.wait(), timeout=timeout)
    except TimeoutError:
        return None
    return _link_message


def _database_url() -> str:
    return Settings.load().storage.database


async def _ensure_trainer(sess: AsyncSession, trainer_id: uuid.UUID) -> None:
    row = await sess.get(models.Trainer, trainer_id)
    if row is not None:
        return
    sess.add(models.Trainer(id=trainer_id, username=f"trainer-{str(trainer_id)[:8]}"))
    await sess.flush()


def _resolve_auth_context(request: Request) -> tuple[uuid.UUID, str]:
    token = request.query_params.get("token")
    trainer_id_raw = request.query_params.get("trainer_id")
    state = request.cookies.get(_STATE_COOKIE)

    if state is not None:
        trainer_id, state_token = linking.parse_state(state)
        return trainer_id, token or state_token

    if token is None or trainer_id_raw is None:
        raise ValueError("Missing Last.fm auth state. Start from /lastfm/authorize?trainer_id=...")

    return uuid.UUID(trainer_id_raw), token


async def _persist_lastfm_link(
    trainer_id: uuid.UUID,
    session: tokens.LastFmSessionResponse,
) -> str:
    engine = db_engine.create_async_database_engine(_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as sess:
            await _ensure_trainer(sess, trainer_id)
            await trainer_links_repo.set_trainer_lastfm_link(
                sess,
                trainer_id,
                session_key=session.key,
                username=session.name,
            )
            await sess.commit()
    finally:
        await engine.dispose()
    return f"Last.fm linked for trainer {trainer_id} as {session.name}."


async def _poll_until_linked(trainer_id: uuid.UUID, token: str) -> None:
    """Desktop-style completion when Last.fm does not redirect to the callback."""
    for _ in range(_POLL_ATTEMPTS):
        if _link_event.is_set():
            return
        session = await tokens.try_get_session(token)
        if session is None:
            await asyncio.sleep(_POLL_INTERVAL_S)
            continue
        message = await _persist_lastfm_link(trainer_id, session)
        signal_link_complete(message)
        return


async def authorize(request: Request) -> RedirectResponse | PlainTextResponse:
    trainer_id_raw = request.query_params.get("trainer_id")
    if trainer_id_raw is None:
        return PlainTextResponse("Missing trainer_id query parameter.", status_code=400)
    try:
        trainer_id = uuid.UUID(trainer_id_raw)
    except ValueError:
        return PlainTextResponse("trainer_id must be a UUID.", status_code=400)

    try:
        token = await tokens.get_token()
    except Exception as exc:
        return PlainTextResponse(f"Last.fm token request failed: {exc}", status_code=502)

    state = linking.build_state(trainer_id, token)
    response = RedirectResponse(linking.build_authorize_url(trainer_id, token))
    response.set_cookie(_STATE_COOKIE, state, max_age=600, httponly=True, samesite="lax")
    poll_task = asyncio.create_task(_poll_until_linked(trainer_id, token), name="lastfm-link-poll")
    _link_poll_tasks.add(poll_task)
    poll_task.add_done_callback(_link_poll_tasks.discard)
    return response


async def callback(request: Request) -> PlainTextResponse:
    try:
        trainer_id, token = _resolve_auth_context(request)
        session = await tokens.get_session(token)
    except ValueError as exc:
        return PlainTextResponse(str(exc), status_code=400)
    except Exception as exc:
        return PlainTextResponse(f"Last.fm session exchange failed: {exc}", status_code=502)

    message = await _persist_lastfm_link(trainer_id, session)
    response = PlainTextResponse(message)
    response.delete_cookie(_STATE_COOKIE)
    signal_link_complete(message)
    return response


async def finish(request: Request) -> HTMLResponse | PlainTextResponse:
    """Manual completion when Last.fm shows 'close your browser' without redirecting."""
    try:
        trainer_id, token = _resolve_auth_context(request)
    except ValueError as exc:
        return PlainTextResponse(str(exc), status_code=400)

    try:
        session = await tokens.try_get_session(token)
    except Exception as exc:
        return PlainTextResponse(f"Last.fm session exchange failed: {exc}", status_code=502)

    if session is None:
        parsed = urlparse(linking.build_callback_url())
        finish_url = f"{parsed.scheme}://{parsed.netloc}/lastfm/finish"
        return HTMLResponse(
            f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3">
  <title>Last.fm linking</title>
</head>
<body>
  <p>Waiting for Last.fm approval… This page refreshes every 3 seconds.</p>
  <p>If you have not started linking yet, open
    <a href="{linking.build_local_authorize_url(trainer_id)}">authorize</a> first.</p>
  <p>Keep this tab open after approving on Last.fm, or revisit <code>{finish_url}</code>.</p>
</body>
</html>"""
        )

    message = await _persist_lastfm_link(trainer_id, session)
    response = PlainTextResponse(message)
    response.delete_cookie(_STATE_COOKIE)
    signal_link_complete(message)
    return response


async def unlink(request: Request) -> JSONResponse:
    trainer_id_raw = request.query_params.get("trainer_id")
    if trainer_id_raw is None:
        return JSONResponse({"error": "Missing trainer_id."}, status_code=400)
    try:
        trainer_id = uuid.UUID(trainer_id_raw)
    except ValueError:
        return JSONResponse({"error": "trainer_id must be a UUID."}, status_code=400)

    engine = db_engine.create_async_database_engine(_database_url())
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as sess:
            await trainer_links_repo.set_trainer_lastfm_link(sess, trainer_id, session_key=None, username=None)
            await sess.commit()
    finally:
        await engine.dispose()

    return JSONResponse({"trainer_id": str(trainer_id), "lastfm_linked": False})


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/lastfm/authorize", authorize, methods=["GET"]),
            Route("/lastfm/callback", callback, methods=["GET"]),
            Route("/lastfm/finish", finish, methods=["GET"]),
            Route("/lastfm/unlink", unlink, methods=["POST"]),
        ]
    )
