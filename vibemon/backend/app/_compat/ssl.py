"""Route stdlib/httpx TLS verification through the operating system trust store."""


def use_system_trust_store() -> None:
    """Make the stdlib ``ssl`` module verify against the OS trust store.

    ``niquests`` (our provider HTTP layer) already verifies against the OS trust
    store via ``wassima``, so it transparently honors enterprise roots. The
    stdlib ``ssl`` stack — used by ``httpx`` and therefore ``google-genai`` —
    instead ships with ``certifi`` and ignores the OS store, so it fails behind
    a TLS-inspecting proxy whose root lives only in the OS store.

    ``truststore.inject_into_ssl`` patches ``ssl.SSLContext`` so those clients
    trust the same OS roots. This removes the need to export the OS bundle and
    set ``REQUESTS_CA_BUNDLE`` / ``SSL_CERT_FILE`` by hand on inspected networks.
    """
    import truststore

    truststore.inject_into_ssl()


use_system_trust_store()
