from typing import Any
import pathlib

import jinja2
import structlog
import yaml

_LOGGER = structlog.get_logger(__name__)

_PROMPT_DIR = pathlib.Path(__file__).parent.joinpath("prompts")
_PROMPT_ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_PROMPT_DIR),
    undefined=jinja2.StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)


def load_prompt(name: str, **variables: Any) -> str:
    """Load a prompt from the prompts directory."""
    assert isinstance(_PROMPT_ENV.loader, jinja2.FileSystemLoader), "PromptLoader must be jinja2.FileSystemLoader"

    template_name = f"{name}.mdc"

    prompt_md, _, _ = _PROMPT_ENV.loader.get_source(_PROMPT_ENV, template_name)

    if prompt_md.count("---\n") < 2:
        raise ValueError(f"'{name}.mdc' is missing frontmatter delimiters")

    _, _, rest = prompt_md.partition("---\n")
    m, _, body = rest.partition("---\n")

    meta = yaml.safe_load(m) or {}

    _LOGGER.debug("Constructing prompt", prompt_name=name, prompt_version=meta.get("version"))

    return _PROMPT_ENV.from_string(body.strip()).render(**variables)
