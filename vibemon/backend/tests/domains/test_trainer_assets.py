import io

from PIL import Image

from app.domains.sprite import orient as sprite_orient
from app.domains.sprite import types as sprite_types
from app.domains.trainer import assets as trainer_assets


def _likeness_bytes(*, fill: tuple[int, int, int]) -> bytes:
    payload = io.BytesIO()
    Image.new("RGB", (64, 96), fill).save(payload, format="JPEG")
    return payload.getvalue()


def test_orient_reference_left_preserves_left_facing_likeness() -> None:
    image = Image.new("RGBA", (32, 32), (200, 80, 40, 255))
    image.putpixel((28, 16), (255, 255, 255, 255))

    oriented = Image.open(
        io.BytesIO(
            sprite_orient.orient_reference_left(
                image,
                facing=sprite_types.SpriteFacing.LEFT,
            )
        )
    )

    assert oriented.getpixel((28, 16)) == (255, 255, 255, 255)


def test_orient_reference_left_mirrors_right_facing_likeness() -> None:
    image = Image.new("RGBA", (32, 32), (200, 80, 40, 255))
    image.putpixel((28, 16), (255, 255, 255, 255))

    oriented = Image.open(
        io.BytesIO(
            sprite_orient.orient_reference_left(
                image,
                facing=sprite_types.SpriteFacing.RIGHT,
            )
        )
    )

    assert oriented.getpixel((3, 16)) == (255, 255, 255, 255)


def test_orient_reference_left_mirrors_center_facing_likeness() -> None:
    image = Image.new("RGBA", (32, 32), (200, 80, 40, 255))
    image.putpixel((28, 16), (255, 255, 255, 255))

    oriented = Image.open(
        io.BytesIO(
            sprite_orient.orient_reference_left(
                image,
                facing=sprite_types.SpriteFacing.CENTER,
            )
        )
    )

    assert oriented.getpixel((3, 16)) == (255, 255, 255, 255)
    matte = trainer_assets.solve_trainer_reference_background(_likeness_bytes(fill=(180, 40, 40)))

    assert matte.hex.upper() not in {"#FFFFFF", "#F0F0F5", "#F5F5DC"}


def test_solve_trainer_reference_background_uses_likeness_samples() -> None:
    samples = trainer_assets._sample_likeness_foreground_colors(_likeness_bytes(fill=(180, 40, 40)))

    assert samples
    assert all(sample.hex.upper() not in {"#FFFFFF", "#F0F0F5"} for sample in samples)


def test_sample_likeness_skin_colors_reads_face_region() -> None:
    payload = io.BytesIO()
    image = Image.new("RGB", (64, 96))
    for y in range(96):
        for x in range(64):
            image.putpixel((x, y), (210, 150, 110) if y < 40 else (20, 80, 20))
    image.save(payload, format="JPEG")

    skin = trainer_assets._sample_likeness_skin_colors(payload.getvalue())

    assert skin
    assert all(sample.hex.upper() != "#145014" for sample in skin)
