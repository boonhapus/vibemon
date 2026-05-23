from __future__ import annotations

import pytest

from app import types
from app.domain.move import Move
from app.domain.vibemon import Aesthetic, Identity, Vibemon
from app.genai import client


def test_genai_client_is_lazy() -> None:
    calls = {"txt": 0, "img": 0, "el": 0}

    def txt_factory() -> object:
        calls["txt"] += 1
        return object()

    def img_factory() -> object:
        calls["img"] += 1
        return object()

    def el_factory() -> object:
        calls["el"] += 1
        return object()

    c = client.GenAIClient(
        txt_agent_factory=txt_factory,  # type: ignore[arg-type]
        img_agent_factory=img_factory,  # type: ignore[arg-type]
        elevenlabs_factory=el_factory,  # type: ignore[arg-type]
    )
    assert calls == {"txt": 0, "img": 0, "el": 0}
    _ = c.txt_agent
    _ = c.img_agent
    _ = c.elevenlabs
    assert calls == {"txt": 1, "img": 1, "el": 1}


@pytest.mark.asyncio
async def test_default_client_provider_can_be_injected(monkeypatch: pytest.MonkeyPatch) -> None:
    vibemon = Vibemon(
        identity=Identity(name="testmon", elements=(types.VibemonTypeT.FIRE,)),
    )
    vibemon.aesthetic = Aesthetic.from_vibemon(vibemon)

    class FakeClient:
        async def generate_vibemon_name(
            self,
            identity: Identity,
            moves: list[Move],
            visual_notes: str | None,
        ) -> str:
            return "InjectedName"

        async def generate_sprite_reference(self, vibemon: Vibemon) -> bytes:
            return b"ref"

        async def generate_sprite_sheet(self, vibemon: Vibemon, reference: bytes) -> bytes:
            return b"sheet"

        async def generate_battle_cry(self, vibemon: Vibemon) -> bytes:
            return b"cry"

    monkeypatch.setattr(client, "get_default_client", lambda: FakeClient())
    injected = client.get_default_client()
    assert await injected.generate_vibemon_name(vibemon.identity, [], None) == "InjectedName"
    assert await injected.generate_sprite_reference(vibemon) == b"ref"
    assert await injected.generate_sprite_sheet(vibemon, b"x") == b"sheet"
    assert await injected.generate_battle_cry(vibemon) == b"cry"
