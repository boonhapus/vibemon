"""httpx runtime fixes for Python 3.14+ annotation introspection."""


def ensure_annotations() -> None:
    """Make httpx.Client annotations introspectable on Python 3.14+.

    httpx 0.28.x references ``ssl.SSLContext`` in PEP 649 annotations but only
    imports ``ssl`` under ``TYPE_CHECKING``, so ``inspect.signature`` fails.
    google-genai triggers that path when building its HTTP client.
    """
    import httpx._client as httpx_client

    if "ssl" in httpx_client.__dict__:
        return

    import ssl

    httpx_client.ssl = ssl
