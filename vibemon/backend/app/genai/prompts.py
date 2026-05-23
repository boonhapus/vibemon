import functools as ft
import pathlib

import jinja2
import pydantic
import structlog
import yaml

_LOGGER = structlog.get_logger(__name__)
_PROMPT_DIR = pathlib.Path(__file__).parent.joinpath("prompts")


class RenderedPrompt(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    text: str
    name: str
    version: str | None
    path: str


@ft.cache
def _env_for(loader_root: pathlib.Path) -> jinja2.Environment:
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(loader_root),
        undefined=jinja2.StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(template_path: str, **variables: object) -> RenderedPrompt:
    """
    Render a prompt from the prompts directory.

    If the path is in a subdirectory, that directory becomes the Jinja
    loader root so includes resolve relative to it.
    """
    path = pathlib.Path(template_path)
    env = _env_for(_PROMPT_DIR / path.parent)

    if env.loader is None:
        raise RuntimeError("Jinja environment has no loader")

    source, _, _ = env.loader.get_source(env, path.name)

    if source.count("---\n") < 2:
        raise ValueError(f"'{template_path}' is missing frontmatter delimiters")

    _, _, rest = source.partition("---\n")
    m, _, body = rest.partition("---\n")

    metadata = yaml.safe_load(m) or {}

    _LOGGER.debug(
        "Constructing prompt",
        prompt_path=template_path,
        prompt_version=metadata.get("version"),
    )

    return RenderedPrompt(
        text=env.from_string(body.strip()).render(**variables),
        name=str(metadata.get("name") or path.stem),
        version=metadata.get("version"),
        path=template_path,
    )
