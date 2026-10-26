"""Crops a hair lock (texture only: curl pattern, shine) from each grade A after in docs/products/hair_refs.json.

The lock is a 3:4 window, 30% of the hair width, placed where the MediaPipe hair mask is solid, away from the
face and in the lower part of the hair (mid-lengths to ends, where the pattern shows). LOCK_OVERRIDE holds
boxes set by eye where the search picks a bad spot.
Usage: SCENE_QA_MODELS=<dir> server/.venv/Scripts/python.exe tools/crop_hair_locks.py outputs/10_hair_refs
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from add_client_avatars import mediapipe_tools  # noqa: E402

# id -> (left, top, right, bottom) as fractions of the after image, checked by eye
LOCK_OVERRIDE = {
    "r03": (0.30, 0.45, 0.70, 0.717),  # the search took the ends and the shirt
    "r38": (0.68, 0.50, 0.92, 0.663),  # background in the window
    "r40": (0.66, 0.50, 0.86, 0.62),   # background in the window
    "r41": (0.60, 0.47, 0.78, 0.59),   # no solid window found
    "r45": (0.17, 0.42, 0.32, 0.71),   # back view of the after
    "r57": (0.20, 0.35, 0.34, 0.49),   # no solid window found; hair beside the cheek
}


def best_window(hair, face_box, ww, wh):
    """Window with the most hair, in the lower 60% of the hair, not on the face."""
    H, W = hair.shape
    ys = np.nonzero(hair.any(axis=1))[0]
    top, bot = ys.min(), ys.max()
    integ = np.pad(hair.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    best, box = -1, None
    step = max(4, ww // 8)
    for y in range(int(top + 0.35 * (bot - top)), max(int(top + 0.35 * (bot - top)) + 1, bot - wh + 1), step):
        for x in range(0, W - ww + 1, step):
            s = integ[y + wh, x + ww] - integ[y, x + ww] - integ[y + wh, x] + integ[y, x]
            frac = s / (ww * wh)
            if face_box is not None:
                fx0, fy0, fx1, fy1 = face_box
                if x < fx1 and x + ww > fx0 and y < fy1 and y + wh > fy0:
                    continue
            score = frac + 0.15 * (y - top) / max(1, bot - top)  # prefer mid-lengths/ends
            if frac > 0.9 and score > best:
                best, box = score, (x, y, x + ww, y + wh)
    return box


def main(base):
    base = Path(base)
    doc = json.load(open("docs/products/hair_refs.json", encoding="utf-8"))
    out = base / "locks"
    out.mkdir(exist_ok=True)
    seg = mediapipe_tools(raw=True)
    res = {}
    for r in doc["refs"]:
        if r["grade"] != "A":
            continue
        src = base / "split" / f"{r['id']}_after.png"
        im = Image.open(src).convert("RGB")
        if r["id"] in LOCK_OVERRIDE:
            l, t, rr, b = LOCK_OVERRIDE[r["id"]]
            box = (int(l * im.width), int(t * im.height), int(rr * im.width), int(b * im.height))
        else:
            hair, face = seg(im)
            fb = None
            if face is not None:
                fb = (face[:, 0].min(), face[:, 1].min(), face[:, 0].max(), face[:, 1].max())
            xs = np.nonzero(hair.any(axis=0))[0]
            ww = max(48, int(0.3 * (xs.max() - xs.min())))
            box = best_window(hair, fb, ww, int(ww * 4 / 3))
            if box is None:
                print(r["id"], "no solid hair window")
                continue
        lock = im.crop(box)
        lock = lock.resize((384, 512), Image.LANCZOS)
        lock.save(out / f"{r['id']}_lock.png")
        res[r["id"]] = [round(v, 3) for v in (box[0] / im.width, box[1] / im.height, box[2] / im.width, box[3] / im.height)]
    print(json.dumps(res))


if __name__ == "__main__":
    main(sys.argv[1])
