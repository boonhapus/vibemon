"""Cached niquests session that includes `params=` in the cache key."""

from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from niquests_cache import AsyncCachedSession
import niquests


def _params_to_pairs(params: Any) -> list[tuple[str, str]]:
    """Normalize niquests-style params to (key, value) string pairs.

    Handles dicts and iterables of pairs; flattens list/tuple values
    (e.g. `{"id": [1, 2]}` → `[("id", "1"), ("id", "2")]`); drops `None`
    values to match niquests' "None means omit" semantics.
    """
    items = params.items() if isinstance(params, Mapping) else params
    pairs: list[tuple[str, str]] = []
    for k, v in items:
        if v is None:
            continue
        if isinstance(v, (list, tuple)):
            pairs.extend((str(k), str(x)) for x in v if x is not None)
        else:
            pairs.append((str(k), str(v)))
    return pairs


def _merge_params_into_url(url: str, params: Any) -> str:
    """Fold `params` into the URL's query string in canonical (sorted) order.

    niquests-cache derives the cache key from the URL string before niquests
    has a chance to merge `params=` into the prepared request. Folding them
    in up front means the key reflects them. Sorting ensures two callers
    passing equivalent dicts in different insertion orders share a cache
    entry.
    """
    parts = urlsplit(url)
    pairs = list(parse_qsl(parts.query, keep_blank_values=True))
    pairs.extend(_params_to_pairs(params))
    pairs.sort()
    return urlunsplit(parts._replace(query=urlencode(pairs)))


class CachedAPIClient(AsyncCachedSession):
    """AsyncCachedSession with `params=`-aware cache keys."""

    async def request(  # type: ignore[override]
        self,
        method: str,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> niquests.Response:
        if params := kwargs.pop("params", None):
            url = _merge_params_into_url(url, params)

        return await super().request(method, url, *args, **kwargs)
