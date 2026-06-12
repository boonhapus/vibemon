"""Optional locked-palette quantization for snapped sprites."""

from PIL import Image

LOCKED_PALETTE = [
    "#F0E7CE",
    "#3D2B1F",
    "#C0542A",
    "#6E7540",
    "#C9A23F",
    "#7C4D8A",
    "#C4A882",
    "#3D8C8C",
    "#D4A017",
    "#6B7A2A",
    "#A0BAC8",
    "#8B3A2A",
    "#A0784A",
    "#6E8FA8",
    "#B0607A",
    "#7A8C2A",
    "#8C7A5A",
    "#524870",
    "#2A5C58",
    "#4A3428",
    "#8A8C8E",
    "#C4909A",
    "#6B9B5A",
    "#CC7A22",
    "#A03020",
    "#2A1E16",
    "#A68A4C",
    "#FFFFFF",
]


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def quantize_to_locked_palette(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    palette_image = Image.new("P", (1, 1))
    flat = [channel for hex_color in LOCKED_PALETTE for channel in _hex_to_rgb(hex_color)]
    flat += flat[:3] * (256 - len(LOCKED_PALETTE))
    palette_image.putpalette(flat)
    quantized = rgb.quantize(palette=palette_image, dither=Image.Dither.NONE).convert("RGBA")
    quantized.putalpha(image.getchannel("A"))
    return quantized
