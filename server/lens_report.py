"""Lens report: compare focal-length estimators on a folder of photos.

    python lens_report.py <photos_dir> [--methods mediapipe,sam3d_body]

For every photo prints the 35mm-equivalent focal given by:
  EXIF | MoGe-2 | GeoCalib | SAM 3D Body | lens search (fit) per backend
The lens search re-fits the puppet for 18..135mm and keeps the focal whose
perspective best agrees with the puppet's rigid proportions + 2D keypoints.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from methods import common, fit, focal, gravity, keypoints2d  # noqa: E402
import pose_server  # noqa: E402


def f35_of(fpx, W, H):
    return fpx / ((W * W + H * H) ** 0.5) * 43.2666


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos")
    ap.add_argument("--methods", default="mediapipe,sam3d_body")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    exts = (".jpg", ".jpeg", ".png", ".webp")
    rows = []
    for name in sorted(os.listdir(a.photos)):
        if not name.lower().endswith(exts):
            continue
        path = os.path.abspath(os.path.join(a.photos, name))
        rgb, _ = common.load_rgb(path)
        H, W = rgb.shape[:2]
        row = {"photo": name}
        ex = common.exif_focal_35mm(path)
        row["exif"] = ex
        f_moge = focal.moge_fov(rgb)
        row["moge2"] = round(f35_of(f_moge, W, H), 1) if f_moge else None
        g = gravity.estimate(path) if gravity.available() else None
        row["geocalib"] = round(f35_of(g["focal_px"], W, H), 1) if g else None
        kp = keypoints2d.detect(rgb)[0]
        for m in a.methods.split(","):
            res = pose_server.estimate(path, m, 0.0, use_gravity=False, do_fit=False)
            f0 = res["camera"]["fx"]
            if m == "sam3d_body":
                row["sam3d"] = round(f35_of(f0, W, H), 1)
            fbest, _, info, table, f35 = fit.lens_search(
                res["points3d"], kp, f0, W / 2, H / 2, W, H)
            row[f"search_{m}"] = f35
            row[f"table_{m}"] = table
        rows.append(row)
        print(json.dumps({k: v for k, v in row.items() if not k.startswith("table")}))
        for m in a.methods.split(","):
            print("   ", m, " ".join(f"{f}mm:{l:.3f}" for f, l, _ in row[f"table_{m}"]))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=1)


if __name__ == "__main__":
    main()
