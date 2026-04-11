from __future__ import annotations

from typing import Any

from attrs import has
from cattrs import Converter

converter = Converter()


def to_jsonable(obj: Any) -> Any:
    return converter.unstructure(obj)


def structure_generate_request(data: dict[str, Any]) -> Any:
    from app.engine.models import GenerateRequestBody

    return converter.structure(data, GenerateRequestBody)
