"""Registry invariants: birth set, catalog set, and defaults."""

import pytest

from app.providers import registry


def test_every_provider_name_has_one_registration() -> None:
    assert {registration.name for registration in registry.REGISTRATIONS} == set(registry.ProviderName)
    assert len(registry.REGISTRATIONS) == len(registry.ProviderName)


def test_registration_names_match_provider_class_names() -> None:
    for registration in registry.REGISTRATIONS:
        assert registration.name.value == registration.provider_type.name


def test_birth_capable_providers_appear_in_catalog() -> None:
    catalog_ids = {entry.id for entry in registry.list_catalog_entries()}
    birth_names = {r.name.value for r in registry.REGISTRATIONS if r.birth_capable}
    assert birth_names <= catalog_ids


def test_default_birth_providers_are_birth_capable() -> None:
    for name in registry.DEFAULT_BIRTH_PROVIDERS:
        assert registry.get_registration(name).birth_capable


def test_default_birth_set_matches_product_intent() -> None:
    assert registry.DEFAULT_BIRTH_PROVIDERS == (
        registry.ProviderName.CLIMATE,
        registry.ProviderName.BIOME,
        registry.ProviderName.CELESTIAL,
    )


def test_resolve_provider_names_falls_back_to_defaults() -> None:
    assert registry.resolve_provider_names(None) == registry.DEFAULT_BIRTH_PROVIDERS
    assert registry.resolve_provider_names([]) == registry.DEFAULT_BIRTH_PROVIDERS


def test_resolve_provider_names_rejects_non_birth_capable() -> None:
    with pytest.raises(ValueError, match="cannot participate in birth"):
        registry.resolve_provider_names(["video"])


def test_get_catalog_provider_unknown_name_raises_key_error() -> None:
    with pytest.raises(KeyError, match="Unknown provider"):
        registry.get_catalog_provider("polka")
