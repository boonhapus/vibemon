from PIL import Image
import numpy as np
import rembg


def split_creature(image_path: str) -> dict[str, Image.Image]:
    """Split creature image into 3 panels at black dividers.

    Args:
        image_path: Path to source image.

    Returns:
        Dict with keys 'left', 'center', 'right' containing processed images.
    """
    img = Image.open(image_path).convert('RGBA')
    arr = np.array(img)

    col_means = arr[:, :, :3].mean(axis=0).max(axis=1)
    dark_cols = np.where(col_means < 20)[0]

    divider1_end = dark_cols[dark_cols < 600][-1]
    divider2_start = dark_cols[dark_cols > 600][0]

    panels = [
        (0, dark_cols[0]),
        (divider1_end + 1, divider2_start - 1),
        (dark_cols[-1] + 1, img.width),
    ]
    names = ['left', 'center', 'right']

    result = {}
    for name, (x1, x2) in zip(names, panels):
        panel = img.crop((x1, 0, x2, img.height))
        panel_no_bg = rembg.remove(panel)
        result[name] = panel_no_bg

        out_path = image_path.replace('.png', f'_{name}.png')
        panel_no_bg.save(out_path)
        print(f'Saved {out_path} — size: {panel_no_bg.size}')

    return result


if __name__ == '__main__':
    split_creature('app/Gemini_Generated_Image_88fiby88fiby88fi.png')