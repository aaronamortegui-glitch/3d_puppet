"""Splits each before/after reference into <id>_before.png and <id>_after.png.

pair and split layouts: cut at the strongest vertical edge near the middle (the seam or the gap
between the two photos), then trim the white margins. grid_2x2: top half is the before, bottom the after.
Usage: python tools/split_hair_refs.py outputs/10_hair_refs
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image


# checked by eye: the edge search picks a hair or background edge instead of the seam
SEAM_OVERRIDE = {"r02": 0.5, "r03": 0.5, "r10": 0.5, "r27": 0.5, "r48": 0.5}


def seam(a):
    """Column of the before/after seam, searched in the middle 30% of the width."""
    g = np.abs(np.diff(a.astype(np.int16), axis=1)).sum(axis=2)  # H x (W-1)
    w = a.shape[1]
    lo, hi = int(w * 0.35), int(w * 0.65)
    # a seam is an edge on most rows, so take a low percentile instead of the mean
    score = np.percentile(g[:, lo:hi], 30, axis=0)
    # a uniform gap (white or grey band) has no edge inside but is flat: reward flat columns too
    flat = a[:, lo:hi].std(axis=0).mean(axis=1)
    gap = (flat < 6).astype(float) * score.max()
    return lo + int(np.argmax(score + gap))


def trim(im, tol=12):
    a = np.asarray(im).astype(np.int16)
    bg = a[0, 0]
    mask = (np.abs(a - bg).sum(axis=2) > tol)
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return im
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def main(base):
    base = Path(base)
    doc = json.load(open("docs/products/hair_refs.json", encoding="utf-8"))
    out = base / "split"
    out.mkdir(exist_ok=True)
    cuts = {}
    for r in doc["refs"]:
        im = Image.open(base / "refs" / f"{r['id']}.png").convert("RGB")
        w, h = im.size
        if r["layout"] == "grid_2x2":
            b, a = im.crop((0, 0, w, h // 2)), im.crop((0, h // 2, w, h))
            cuts[r["id"]] = "row %d" % (h // 2)
        else:
            x = int(SEAM_OVERRIDE[r["id"]] * w) if r["id"] in SEAM_OVERRIDE else seam(np.asarray(im))
            b, a = im.crop((0, 0, x, h)), im.crop((x + 1, 0, w, h))
            cuts[r["id"]] = x / w
        trim(b).save(out / f"{r['id']}_before.png")
        trim(a).save(out / f"{r['id']}_after.png")
    print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in cuts.items()})


if __name__ == "__main__":
    main(sys.argv[1])
