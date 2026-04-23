import pathlib

import yaml


def load_prompt(name: str, **variables: str) -> str:
    """Load a prompt from the prompts directory."""
    prompt_fp = pathlib.Path(__file__).parent.joinpath(f"prompts/{name}.mdc")
    prompt_md = prompt_fp.read_text(encoding="utf-8")

    if prompt_md.count("---\n") < 2:
        raise ValueError(f"'{name}.mdc' is missing frontmatter delimiters")

    _, _, rest = prompt_md.partition("---\n")
    m, _, body = rest.partition("---\n")

    meta = yaml.safe_load(m)

    if missing := set(meta.get("variables", [])) - variables.keys():
        raise ValueError(f"'{name}' missing variables: {missing}")

    return body.strip().format(**variables)
