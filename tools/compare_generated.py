"""How much did an AI edit move the person?  RTMW keypoints, original vs edit.

    server\\.venv\\Scripts\\python.exe tools\\compare_generated.py <photos_dir> <generated_dir> <suffix> <out.json>

For every photo NN_name.ext in <photos_dir>, the edit <generated_dir>/NN_name<suffix>.png
is resized to the photo's size and both are run through RTMW. Reports median / max
pixel shift per body group and a similarity-aligned residual (what remains after
removing a global shift + scale, i.e. real pose change).
"""

import glob
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
from methods import common, keypoints2d  # noqa: E402

GROUPS = {
    "head": ["nose", "left_eye_smplhf", "right_eye_smplhf", "left_ear", "right_ear"],
    "shoulders": ["left_shoulder", "right_shoulder"],
    "elbows": ["left_elbow", "right_elbow"],
    "wrists": ["left_wrist", "right_wrist"],
    "fingertips": [f"{s}_{f}_tip" for s in ("left", "right")
                   for f in ("thumb", "index", "middle", "ring", "pinky")],
}


def main():
    photos, gen, suffix, out = sys.argv[1:5]
    report = {}
    for p in sorted(glob.glob(os.path.join(photos, "*"))):
        stem = os.path.splitext(os.path.basename(p))[0]
        g = os.path.join(gen, stem + suffix + ".png")
        if not os.path.exists(g):
            continue
        a, _ = common.load_rgb(p)
        b, _ = common.load_rgb(g)
        from PIL import Image
        b = np.asarray(Image.fromarray(b).resize((a.shape[1], a.shape[0]), Image.LANCZOS))
        ka, kb = keypoints2d.detect(a), keypoints2d.detect(b)
        if not ka or not kb:
            continue
        ka, kb = ka[0], kb[0]
        H, W = a.shape[:2]
        edge = 0.015 * max(W, H)
        common_names = [n for n in ka if n in kb and ka[n][2] > 0.4 and kb[n][2] > 0.4
                        and edge < ka[n][0] < W - edge and edge < ka[n][1] < H - edge]
        A = np.array([ka[n][:2] for n in common_names])
        B = np.array([kb[n][:2] for n in common_names])
        r = {}
        for grp, names in GROUPS.items():
            d = [float(np.linalg.norm(A[i] - B[i])) for i, n in enumerate(common_names) if n in names]
            if d:
                r[grp] = {"median_px": round(float(np.median(d)), 1),
                          "max_px": round(float(np.max(d)), 1), "n": len(d)}
        # similarity alignment (scale + translation) -> residual = true pose change
        ca, cb = A.mean(0), B.mean(0)
        s = np.sqrt(((A - ca) ** 2).sum() / max(((B - cb) ** 2).sum(), 1e-9))
        resid = np.linalg.norm((B - cb) * s + ca - A, axis=1)
        r["centroid_shift_px"] = [round(float(v), 1) for v in (cb - ca)]
        r["scale"] = round(float(1 / s), 3)
        r["residual_after_align_px"] = round(float(np.median(resid)), 1)
        r["image_px"] = [W, H]
        report[stem] = r
        print(stem, {k: (v["median_px"] if isinstance(v, dict) else v) for k, v in r.items()})
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
