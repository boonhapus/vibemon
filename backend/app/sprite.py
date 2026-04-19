from typing import ClassVar
import pathlib
import re

import attrs
import jinja2

_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(pathlib.Path(__file__).parent),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


@attrs.define
class Limb:
    count: int
    function: str
    dominant: bool = False
    joint_count: int | None = None
    tip_detail: str | None = None


@attrs.define
class Anatomy:
    head: str | None = None
    torso: str | None = None
    abdomen: str | None = None
    tail: str | None = None
    wings: str | None = None
    limbs: list[Limb] = attrs.field(factory=list)

    @property
    def named_parts(self) -> list[tuple[str, str]]:
        return [
            (part.capitalize(), getattr(self, part))
            for part in ("head", "torso", "abdomen", "tail", "wings")
            if getattr(self, part)
        ]


@attrs.define
class ColorZone:
    region: str
    description: str
    hex: str


@attrs.define
class Creature:
    name: str
    anatomy: Anatomy
    colors: list[ColorZone]
    glow_rule: str

    def render(self, template) -> str:
        """Create the 3-panel render."""
        RE_MARKDOWN_FRONTMATTER = re.compile(r"^---\n.*?\n---\n\n?", re.DOTALL)

        raw = _env.get_template(template).render(creature=self)

        return RE_MARKDOWN_FRONTMATTER.sub("", raw)


if __name__ == "__main__":
    creature = Creature(
        name="Abyssalurk",
        anatomy=Anatomy(
            head="broad oval, bioluminescent lure antenna, large amber compound eyes",
            torso="segmented ovoid, armored chitin plates with cyan trim lines",
            abdomen="tapered, 7 segments, bioluminescent vent slits",
            limbs=[
                Limb(count=2, function="raptorial claws", dominant=True),
                Limb(count=6, function="articulated walking legs", joint_count=3, tip_detail="hooked claws"),
            ],
        ),
        colors=[
            ColorZone("Exoskeleton",         "deep navy",     "#0D1B2A"),
            ColorZone("Bioluminescent trim", "electric cyan", "#00E5FF"),
            ColorZone("Underplates",         "near-black",    "#050D14"),
        ],
        glow_rule="Cyan glow only on lure tip and segment trim lines — never on limbs or face",
    )

    creature_prompt = creature.render("vibemon-sprites.mdc")

    print(creature_prompt)