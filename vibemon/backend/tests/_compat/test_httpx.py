import inspect

import httpx

from app._compat import httpx as httpx_compat


def test_ensure_annotations_allows_client_signature_introspection() -> None:
    httpx_compat.ensure_annotations()
    assert "verify" in inspect.signature(httpx.Client.__init__).parameters
