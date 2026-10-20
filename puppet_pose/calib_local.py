# SPDX-License-Identifier: GPL-3.0-or-later
"""Measured-camera support for the Lite backend (no server needed).

Reads a camera profile / camera pose JSON written by server/calibrate.py,
undistorts the photo with OpenCV (installed with MediaPipe) and returns
what the Lite backend needs.  See docs/CAPTURE_GUIDE.md.
"""

import json
import math
import os
import tempfile


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def undistort(image_path, profile):
    """-> (undistorted image path, 35mm-equivalent focal of the new camera)."""
    import cv2
    import numpy as np
    from . import deps
    deps.ensure_path()
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Cannot read {image_path}")
    H, W = img.shape[:2]
    sx, sy = W / profile["width"], H / profile["height"]
    if abs(sx - sy) > 0.01:
        raise RuntimeError("Photo aspect ratio differs from the camera profile (cropped photo?)")
    fx, fy = profile["fx"] * sx, profile["fy"] * sy
    K = np.array([[fx, 0, profile["cx"] * sx], [0, fy, profile["cy"] * sy], [0, 0, 1]])
    f = (fx + fy) / 2
    K_new = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    out = cv2.undistort(img, K, np.array(profile["dist"]), None, K_new)
    dst = os.path.join(tempfile.gettempdir(), "puppet_undist_" +
                       os.path.splitext(os.path.basename(image_path))[0] + ".png")
    cv2.imwrite(dst, out)
    return dst, f / math.hypot(W, H) * math.hypot(36, 24)
