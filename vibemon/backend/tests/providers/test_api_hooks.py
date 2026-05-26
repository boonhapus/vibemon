from app.providers.api_hooks import provider_retry_policy


def test_provider_retry_policy_retries_transient_status_codes() -> None:
    policy = provider_retry_policy()
    assert policy.total == 5
    assert policy.backoff_factor == 2
    assert 429 in policy.status_forcelist
    assert 503 in policy.status_forcelist
    assert policy.respect_retry_after_header is True
    assert policy.raise_on_status is False
