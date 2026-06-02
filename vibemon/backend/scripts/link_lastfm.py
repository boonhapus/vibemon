"""Store a trainer Last.fm session for local music birth rehearsal."""

from typing import Annotated
from urllib.parse import urlparse
import asyncio
import uuid
import webbrowser

import cyclopts
import uvicorn

from app.providers.music.lastfm import linking
from app.providers.music.lastfm import routes as lastfm_routes
from app.settings import Settings
from app.storage.database import repositories
from scripts import _common

COMMON_OPTIONS = cyclopts.Group("Common options", sort_key=0)
ADVANCED_OPTIONS = cyclopts.Group("Advanced options", sort_key=1)
_BROWSER_LINK_TIMEOUT_S = 600.0

app = cyclopts.App(
    help=(
        "Link a trainer Last.fm account for MusicProvider births.\n\n"
        "Examples:\n"
        "  link_lastfm.py --trainer <uuid> --session-key <key> --username <name>\n"
        "  link_lastfm.py --trainer <uuid> --browser\n"
        "  link_lastfm.py --trainer <uuid> --unlink"
    )
)


@app.default
def link_lastfm(
    *,
    trainer: Annotated[
        uuid.UUID,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Trainer UUID to link."),
    ],
    session_key: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Paste a Last.fm session key."),
    ] = None,
    username: Annotated[
        str | None,
        cyclopts.Parameter(group=COMMON_OPTIONS, help="Last.fm username for the session key."),
    ] = None,
    browser: Annotated[
        bool,
        cyclopts.Parameter(
            group=COMMON_OPTIONS,
            negative="",
            help="Run the local callback server and open the authorize URL in a browser.",
        ),
    ] = False,
    unlink: Annotated[
        bool,
        cyclopts.Parameter(group=COMMON_OPTIONS, negative="", help="Clear the stored Last.fm link."),
    ] = False,
    database_url: Annotated[
        str | None,
        cyclopts.Parameter(
            group=ADVANCED_OPTIONS,
            help="Database URL override; defaults to VIBEMON_STORAGE__DATABASE.",
        ),
    ] = None,
) -> None:
    storage = _common.load_script_settings(database_url=database_url)
    if sum(option is True for option in (browser, unlink)) + (session_key is not None) != 1:
        raise SystemExit("Choose exactly one of --session-key, --browser, or --unlink.")
    if session_key is not None and not username:
        raise SystemExit("--session-key requires --username.")

    if browser:
        asyncio.run(_browser_link(trainer_id=trainer))
        return

    asyncio.run(
        _persist_link(
            database_url=storage.storage.database,
            trainer_id=trainer,
            session_key=None if unlink else session_key,
            username=None if unlink else username,
        )
    )


async def _browser_link(*, trainer_id: uuid.UUID) -> None:
    callback = str(Settings.load().lastfm.callback)
    parsed = urlparse(callback)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8765
    authorize_url = linking.build_local_authorize_url(trainer_id)
    finish_url = f"{parsed.scheme}://{parsed.netloc}/lastfm/finish"

    print("Last.fm browser linking")
    print(f"  Callback registered on your API account must be exactly:\n    {callback}")
    print(f"  Authorize URL:\n    {authorize_url}")
    print(f"  If Last.fm shows 'Application authenticated' without redirecting, open:\n    {finish_url}")
    print("  (background polling also runs after you hit authorize — no action needed if that succeeds)")

    lastfm_routes.reset_link_waiter()
    config = uvicorn.Config(
        lastfm_routes.create_app(),
        host=host,
        port=port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    serve_task = asyncio.create_task(server.serve())
    try:
        await asyncio.sleep(0.3)
        webbrowser.open(authorize_url)
        message = await lastfm_routes.wait_for_link(timeout=_BROWSER_LINK_TIMEOUT_S)
        if message is None:
            raise SystemExit(
                "Timed out waiting for Last.fm approval. "
                f"After approving on Last.fm, open {finish_url} or re-run --browser."
            )
        print(message)
    finally:
        server.should_exit = True
        await serve_task


async def _persist_link(
    *,
    database_url: str,
    trainer_id: uuid.UUID,
    session_key: str | None,
    username: str | None,
) -> None:
    async with _common.session_scope(database_url=database_url) as sess:
        await _common.ensure_trainer(sess, trainer_id)
        await repositories.set_trainer_lastfm_link(
            sess,
            trainer_id,
            session_key=session_key,
            username=username,
        )
    action = "cleared" if session_key is None else "stored"
    print(f"Last.fm link {action} for trainer {trainer_id}.")


if __name__ == "__main__":
    app()
