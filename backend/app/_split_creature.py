from PIL import Image
import numpy as np
import rembg

img = Image.open('app/Gemini_Generated_Image_88fiby88fiby88fi.png').convert('RGBA')
arr = np.array(img)

# Find black vertical dividers by checking columns for near-black pixels
col_means = arr[:, :, :3].mean(axis=0).max(axis=1)
dark_cols = np.where(col_means < 20)[0]
divider1_end = dark_cols[dark_cols < 600][-1]
divider2_start = dark_cols[dark_cols > 600][0]

panels = [(0, dark_cols[0]), (divider1_end + 1, divider2_start - 1), (dark_cols[-1] + 1, img.width)]
names = ['creature_left', 'creature_center', 'creature_right']

for name, (x1, x2) in zip(names, panels):
    panel = img.crop((x1, 0, x2, img.height))
    panel_no_bg = rembg.remove(panel)
    panel_no_bg.save(f'{name}.png')
    print(f'Saved {name}.png — size: {panel_no_bg.size}')
