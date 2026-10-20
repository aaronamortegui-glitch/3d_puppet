"""Camera calibration CLI (ChArUco).  See docs/CAPTURE_GUIDE.md.

    python calibrate.py board      --out calibration/boards [--squares 7x5 --square-mm 40 --marker-mm 30]
    python calibrate.py intrinsics <photos_dir> --out profiles/my_camera_50mm.json [--camera "Sony A7IV" --lens "50mm"]
    python calibrate.py pose       <photo> --profile profiles/my_camera_50mm.json [--mount floor|wall] [--out pose.json]
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from calibration import charuco  # noqa: E402

EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp")


def _spec(a):
    sx, sy = (int(v) for v in a.squares.lower().split("x"))
    return dict(squares_x=sx, squares_y=sy, square_m=a.square_mm / 1000.0,
                marker_m=a.marker_mm / 1000.0, dictionary=a.dictionary)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("board", "intrinsics", "pose"):
        p = sub.add_parser(name)
        p.add_argument("--squares", default="7x5")
        p.add_argument("--square-mm", type=float, default=40.0)
        p.add_argument("--marker-mm", type=float, default=30.0)
        p.add_argument("--dictionary", default="DICT_5X5_250")
        p.add_argument("--out", default=None)
        if name == "board":
            p.add_argument("--dpi", type=int, default=300)
        if name == "intrinsics":
            p.add_argument("photos")
            p.add_argument("--camera", default="")
            p.add_argument("--lens", default="")
        if name == "pose":
            p.add_argument("photo")
            p.add_argument("--profile", required=True)
            p.add_argument("--mount", choices=["floor", "wall"], default="floor")
    a = ap.parse_args()
    spec = _spec(a)

    if a.cmd == "board":
        r = charuco.make_board(a.out or "calibration_boards", dpi=a.dpi, **spec)
        print(json.dumps(r, indent=1))
        print("Print at 100% scale (no 'fit to page') and MEASURE one square: "
              "it must be exactly", a.square_mm, "mm. Glue it flat on rigid board.")
        return

    if a.cmd == "intrinsics":
        paths = [os.path.join(a.photos, n) for n in sorted(os.listdir(a.photos))
                 if n.lower().endswith(EXTS)]
        prof = charuco.calibrate(paths, spec, a.camera, a.lens)
        out = a.out or os.path.join(a.photos, "camera_profile.json")
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(prof, fh, indent=1)
        print(f"views {prof['views']}  rms {prof['rms_px']}px  fx {prof['fx']:.1f}px  "
              f"35mm-eq {prof['focal_35mm_equiv']}mm  hfov {prof['hfov_deg']}deg")
        print("saved", out)
        if prof["rms_px"] > 1.0:
            print("WARNING: rms > 1px - check focus/motion blur, flatness of the board and "
                  "that zoom/focus did not change between photos")
        return

    if a.cmd == "pose":
        with open(a.profile, encoding="utf-8") as fh:
            prof = json.load(fh)
        from PIL import Image, ImageOps
        import numpy as np
        rgb = np.asarray(ImageOps.exif_transpose(Image.open(a.photo)).convert("RGB"))
        und, K = charuco.undistort(rgb, prof)
        r = charuco.board_pose(und, K, None, prof.get("board", spec), a.mount)
        if r is None:
            raise SystemExit("Board not found in the photo")
        out = a.out or os.path.splitext(a.photo)[0] + "_camera_pose.json"
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=1)
        print(f"camera at {r['camera_position_m']} m  reproj {r['reproj_px']}px  "
              f"corners {r['corners']}  -> {out}")


if __name__ == "__main__":
    main()
