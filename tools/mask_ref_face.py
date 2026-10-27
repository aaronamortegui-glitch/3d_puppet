"""Keep only the hair of a real hair reference (test 20), so a model can only take the hair from it.

Nano Banana 2.1 copied the reference woman's face and clothes into an in-use shot (A03 with r54). The
reference stays the original photo: only its hair pixels (MediaPipe hair mask, slightly grown) are kept, on a
flat neutral grey, cropped to the hair. Writes <name>_hair.png; also <name>_noface.png (face covered).

    SCENE_QA_MODELS=<models> server/.venv/Scripts/python.exe tools/mask_ref_face.py <after.png> [...]
Writes <name>_noface.png next to each file.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_client_avatars import mediapipe_tools  # noqa: E402

from PIL import ImageFilter

run = mediapipe_tools(raw=True)
for p in sys.argv[1:]:
    im = Image.open(p).convert("RGB")
    hair, face = run(im)
    if hair is not None and hair.sum() > 500:
        m = Image.fromarray((hair * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(3))
        bg = Image.new("RGB", im.size, (150, 150, 150))
        cut = Image.composite(im, bg, m)
        box = m.point(lambda v: 255 if v > 20 else 0).getbbox()
        if box:
            pad = int(0.04 * max(im.size))
            box = (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, im.width), min(box[3] + pad, im.height))
            cut.crop(box).save(os.path.splitext(p)[0] + "_hair.png")
    if face is None:
        print(p, "no face found: kept as is")
        continue
    cx, cy = face[:, 0].mean(), face[:, 1].mean()
    rx = (face[:, 0].max() - face[:, 0].min()) / 2 * 1.15
    ry = (face[:, 1].max() - face[:, 1].min()) / 2 * 1.15
    d = ImageDraw.Draw(im)
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(128, 128, 128))
    out = os.path.splitext(p)[0] + "_noface.png"
    im.save(out)
    print(out)
