# SPDX-License-Identifier: GPL-3.0-or-later
"""'Lite' backend: MediaPipe Pose + Hand landmarkers (Apache-2.0).

Runs inside Blender's Python (CPU, ~1 s per photo).  Produces metric
3D points for 33 body + 2x21 hand landmarks, then solves the camera
translation with a perspective least-squares fit so the puppet can be
placed in front of a camera that reproduces the photo framing.

No bpy imports here: the module can also run in a plain Python process.
"""

import math
import os
import tempfile

import numpy as np

BODY = {
    0: "nose", 7: "left_ear", 8: "right_ear",
    11: "left_shoulder", 12: "right_shoulder", 13: "left_elbow",
    14: "right_elbow", 15: "left_wrist", 16: "right_wrist",
    23: "left_hip", 24: "right_hip", 25: "left_knee", 26: "right_knee",
    27: "left_ankle", 28: "right_ankle", 29: "left_heel", 30: "right_heel",
    31: "left_toe", 32: "right_toe",
}
HAND = {
    1: "thumb1", 2: "thumb2", 3: "thumb3", 4: "thumb_tip",
    5: "index1", 6: "index2", 7: "index3", 8: "index_tip",
    9: "middle1", 10: "middle2", 11: "middle3", 12: "middle_tip",
    13: "ring1", 14: "ring2", 15: "ring3", 16: "ring_tip",
    17: "pinky1", 18: "pinky2", 19: "pinky3", 20: "pinky_tip",
}


def load_image(path):
    """Load with EXIF orientation applied.  Returns (rgb array, path used,
    35mm-equivalent focal or None)."""
    from PIL import Image, ImageOps

    im = Image.open(path)
    f35 = None
    try:
        exif = im.getexif()
        sub = exif.get_ifd(0x8769)
        v = sub.get(0xA405)  # FocalLengthIn35mmFilm
        if v:
            f35 = float(v)
    except Exception:
        pass
    orientation = im.getexif().get(0x0112, 1) or 1
    fixed = ImageOps.exif_transpose(im)
    used = path
    if orientation != 1:  # Blender ignores EXIF rotation: save an upright copy
        out = os.path.join(tempfile.gettempdir(), "puppet_pose_" +
                           os.path.splitext(os.path.basename(path))[0] + "_upright.png")
        fixed.convert("RGB").save(out)
        used = out
    return np.asarray(fixed.convert("RGB")), used, f35


def solve_translation(X, uv, f, cx, cy, w=None):
    """Least squares t with project(X + t) ~= uv (OpenCV axes)."""
    rows, rhs = [], []
    w = np.ones(len(X)) if w is None else np.asarray(w)
    for (x, y, z), (u, v), wi in zip(X, uv, w):
        du, dv = u - cx, v - cy
        rows += [wi * np.array([f, 0.0, -du]), wi * np.array([0.0, f, -dv])]
        rhs += [wi * (du * z - f * x), wi * (dv * z - f * y)]
    t, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    t[2] = max(t[2], 0.1)
    return t


def run(image_path, models, focal_35mm=0.0, default_35mm=35.0,
        min_visibility=0.5):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision

    rgb, used_path, exif_f35 = load_image(image_path)
    H, W = rgb.shape[:2]
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
    notes = []

    pose_opts = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=models["pose_landmarker_heavy.task"]),
        running_mode=vision.RunningMode.IMAGE, num_poses=1,
        min_pose_detection_confidence=0.3)
    with vision.PoseLandmarker.create_from_options(pose_opts) as lm:
        pres = lm.detect(mp_img)
    if not pres.pose_world_landmarks:
        raise RuntimeError("No person detected in the photo")
    wl, il = pres.pose_world_landmarks[0], pres.pose_landmarks[0]

    hand_opts = vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=models["hand_landmarker.task"]),
        running_mode=vision.RunningMode.IMAGE, num_hands=2,
        min_hand_detection_confidence=0.3, min_hand_presence_confidence=0.3)
    with vision.HandLandmarker.create_from_options(hand_opts) as hl:
        hres = hl.detect(mp_img)

    # ---- camera intrinsics -------------------------------------------------
    f35 = focal_35mm or exif_f35 or default_35mm
    notes.append(f"focal 35mm-eq: {f35:.1f} ({'user' if focal_35mm else 'EXIF' if exif_f35 else 'default'})")
    f = f35 / math.hypot(36.0, 24.0) * math.hypot(W, H)
    cx, cy = W * 0.5, H * 0.5

    # ---- body points (hip-centred metric, OpenCV axes) ---------------------
    local, pix, vis = {}, {}, {}
    for i, name in BODY.items():
        p, q = wl[i], il[i]
        v = getattr(q, "visibility", 1.0) or 0.0
        vis[name] = v
        local[name] = np.array([p.x, p.y, p.z])
        pix[name] = (q.x * W, q.y * H)

    # ---- hands: assign by proximity to pose wrists ------------------------
    hands_found = []
    for k, hw in enumerate(hres.hand_world_landmarks or []):
        h2d = hres.hand_landmarks[k]
        wrist_px = np.array([h2d[0].x * W, h2d[0].y * H])
        d = {s: np.linalg.norm(wrist_px - np.array(pix[f"{s}_wrist"])) for s in ("left", "right")}
        side = min(d, key=d.get)
        if side in hands_found:
            side = "left" if side == "right" else "right"
        hands_found.append(side)
        hw_np = np.array([[p.x, p.y, p.z] for p in hw])
        offset = local[f"{side}_wrist"] - hw_np[0]
        for i, n in HAND.items():
            local[f"{side}_{n}"] = hw_np[i] + offset
    notes.append("hands: " + (", ".join(hands_found) or "none"))

    # ---- translation --------------------------------------------------------
    keys = [n for n in BODY.values() if vis[n] >= min_visibility]
    if len(keys) < 4:
        keys = list(BODY.values())
    t = solve_translation([local[n] for n in keys], [pix[n] for n in keys], f, cx, cy,
                          [vis[n] for n in keys])

    # drop low-visibility limb points so the rig keeps a neutral pose there
    points = {}
    for n, p in local.items():
        if n in vis and vis[n] < min_visibility and n not in (
                "left_hip", "right_hip", "left_shoulder", "right_shoulder"):
            continue
        points[n] = (p + t).tolist()

    return {
        "backend": "mediapipe_lite",
        "image": {"path": used_path, "width": W, "height": H},
        "camera": {"fx": f, "fy": f, "cx": cx, "cy": cy},
        "points3d": points,
        "points2d": {n: list(pix[n]) for n in pix},
        "notes": notes,
    }
