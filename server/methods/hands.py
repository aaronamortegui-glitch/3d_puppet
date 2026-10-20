"""Hand refinement.

1. Chirality: a left hand's 3D points must have the left-hand "handedness"
   (thumb on the correct side of the palm).  Single-view estimators often
   return the depth-mirrored hand (palm <-> back of the hand), which looks
   identical in 2D.  We detect it and mirror the hand in depth along the
   viewing rays (2D projection unchanged).
2. High-resolution re-detection: crop each hand around its 2D keypoints,
   upscale, run MediaPipe Hand Landmarker on the crop -> better finger 2D
   and a clean 3D hand shape that replaces the regressor's fingers.
"""

import os

import numpy as np

FINGERS = ("thumb", "index", "middle", "ring", "pinky")
HAND_NAMES = [f"{f}{i}" for f in FINGERS for i in (1, 2, 3)] + [f"{f}_tip" for f in FINGERS]
_MP_ORDER = ["wrist", "thumb1", "thumb2", "thumb3", "thumb_tip",
             "index1", "index2", "index3", "index_tip",
             "middle1", "middle2", "middle3", "middle_tip",
             "ring1", "ring2", "ring3", "ring_tip",
             "pinky1", "pinky2", "pinky3", "pinky_tip"]

from . import rest as _rest

_REST = _rest.REST                   # shared: follows rest.use(figure)


def chirality(points, side):
    need = [f"{side}_{n}" for n in ("wrist", "index1", "pinky1", "thumb2")]
    if not all(n in points for n in need):
        return 0
    w, a, b, t = (np.asarray(points[n], dtype=float) for n in need)
    return int(np.sign(np.linalg.det(np.stack([a - w, b - w, t - w]))))


# the figure's own rest pose defines the correct sign for each side
# (rest is in Blender axes; camera conversion is a proper rotation -> same sign)
def rest_sign(side):
    return chirality(_REST, side)


def mirror_hand(points, side):
    """Mirror one hand in depth about its wrist, along viewing rays."""
    out = dict(points)
    wz = float(np.asarray(points[f"{side}_wrist"])[2])
    for n in HAND_NAMES:
        k = f"{side}_{n}"
        if k in out:
            x, y, z = (float(v) for v in out[k])
            z2 = max(2 * wz - z, 0.05)
            s = z2 / z if z > 1e-6 else 1.0
            out[k] = [x * s, y * s, z2]
    return out


def fix_chirality(points, notes=None):
    for s in ("left", "right"):
        c = chirality(points, s)
        if c and c != rest_sign(s):
            points = mirror_hand(points, s)
            if notes is not None:
                notes.append(f"{s} hand was mirrored (palm/back) -> fixed")
    return points


# ---------------------------------------------------------------------------
_landmarker = None


def _get_landmarker():
    global _landmarker
    if _landmarker is None:
        from mediapipe.tasks.python import BaseOptions, vision
        from .mediapipe_method import MODELS, URLS
        import urllib.request
        p = os.path.join(MODELS, "hand_landmarker.task")
        if not os.path.exists(p):
            os.makedirs(MODELS, exist_ok=True)
            urllib.request.urlretrieve(URLS["hand_landmarker.task"], p)
        opts = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=p),
            running_mode=vision.RunningMode.IMAGE, num_hands=1,
            min_hand_detection_confidence=0.2, min_hand_presence_confidence=0.2)
        _landmarker = vision.HandLandmarker.create_from_options(opts)
    return _landmarker


def redetect(rgb, kp2d, side, size=512, pad=0.6):
    """Re-detect one hand on an upscaled crop.
    Returns (pts2d {name:(u,v,conf)}, shape3d {name: xyz relative to wrist}) or None."""
    import cv2
    import mediapipe as mp
    H, W = rgb.shape[:2]
    pts = [kp2d[f"{side}_{n}"] for n in HAND_NAMES if f"{side}_{n}" in kp2d
           and kp2d[f"{side}_{n}"][2] > 0.2]
    if f"{side}_wrist" in kp2d:
        pts.append(kp2d[f"{side}_wrist"])
    if len(pts) < 4:
        return None
    xy = np.array([[p[0], p[1]] for p in pts])
    c = xy.mean(0)
    half = max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1])) * (0.5 + pad)
    half = max(half, 0.04 * max(W, H))
    x0, y0 = int(c[0] - half), int(c[1] - half)
    x1, y1 = int(c[0] + half), int(c[1] + half)
    crop = np.zeros((y1 - y0, x1 - x0, 3), np.uint8) + 255
    sx0, sy0, sx1, sy1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
    if sx1 <= sx0 or sy1 <= sy0:
        return None
    crop[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = rgb[sy0:sy1, sx0:sx1]
    scale = size / crop.shape[0]
    crop = cv2.resize(crop, (size, size), interpolation=cv2.INTER_CUBIC)
    res = _get_landmarker().detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                            data=np.ascontiguousarray(crop)))
    if not res.hand_landmarks:
        return None
    lm, wl = res.hand_landmarks[0], res.hand_world_landmarks[0]
    conf = float(res.handedness[0][0].score) if res.handedness else 0.5
    p2 = {}
    w3 = np.array([wl[0].x, wl[0].y, wl[0].z])
    shape = {}
    for i, n in enumerate(_MP_ORDER):
        u = x0 + lm[i].x * size / scale
        v = y0 + lm[i].y * size / scale
        p2[f"{side}_{n}"] = (float(u), float(v), conf)
        shape[f"{side}_{n}"] = np.array([wl[i].x, wl[i].y, wl[i].z]) - w3
    # sanity: the crop wrist must be near the body wrist
    if f"{side}_wrist" in kp2d:
        d = np.hypot(p2[f"{side}_wrist"][0] - kp2d[f"{side}_wrist"][0],
                     p2[f"{side}_wrist"][1] - kp2d[f"{side}_wrist"][1])
        if d > 2.0 * half:
            return None
    return p2, shape


def redetect_multi(rgb, kp2d, side):
    for pad in (0.6, 0.3, 1.0, 1.5):
        r = redetect(rgb, kp2d, side, pad=pad)
        if r is not None:
            return r
    return None


def dedupe(kp2d, notes=None, proj_wrists=None):
    """Whole-body detectors sometimes put BOTH hands on the same physical hand
    (the other one being out of frame).  Keep it for the side whose body
    wrist is closest; drop the duplicate."""
    def center(s):
        xy = [kp2d[f"{s}_{n}"][:2] for n in HAND_NAMES if f"{s}_{n}" in kp2d and kp2d[f"{s}_{n}"][2] > 0.2]
        return np.mean(xy, 0) if len(xy) >= 4 else None, (np.ptp(np.array(xy), 0).max() if len(xy) >= 4 else 0)
    cl, sl = center("left")
    cr, sr = center("right")
    if cl is None or cr is None:
        return kp2d
    if np.linalg.norm(cl - cr) > 0.5 * max(sl, sr, 1.0):
        return kp2d
    def wdist(s, c):
        # prefer the 3D regressor's projected wrist (it knows which arm is up);
        # the 2D detector's body wrist is unreliable when the other arm is cropped
        if proj_wrists:
            # a wrist the 3D model does not have is an arm it did not see
            return np.linalg.norm(np.array(proj_wrists[s]) - c) if s in proj_wrists else 1e9
        w = kp2d.get(f"{s}_wrist")
        return np.linalg.norm(np.array(w[:2]) - c) if w else 1e9
    keep = "left" if wdist("left", cl) < wdist("right", cr) else "right"
    drop = "right" if keep == "left" else "left"
    out = {k: v for k, v in kp2d.items() if not (k.startswith(drop + "_") and k[len(drop) + 1:] in HAND_NAMES)}
    if notes is not None:
        notes.append(f"duplicate hand detection removed ({drop})")
    return out


def refine(points, kp2d, rgb, notes=None, cam=None):
    """Replace the hand points with the crop re-detection (3D shape attached
    at the regressor wrist) and return improved 2D keypoints for the fit."""
    points = {k: list(v) for k, v in points.items()}
    proj = None
    if cam:
        f, cx, cy = cam
        proj = {}
        for sd in ("left", "right"):
            p = points.get(f"{sd}_wrist")
            if p and p[2] > 1e-3:
                proj[sd] = (f * p[0] / p[2] + cx, f * p[1] / p[2] + cy)
    kp2d = dedupe(dict(kp2d), notes, proj)
    for s in ("left", "right"):
        if f"{s}_wrist" not in points:
            continue
        r = redetect_multi(rgb, kp2d, s)
        if r is None:
            continue
        p2, shape = r
        w = np.asarray(points[f"{s}_wrist"], dtype=float)
        # scale the MediaPipe hand (metric) to the regressor's hand size if known
        sc = 1.0
        if f"{s}_middle1" in points:
            reg = np.linalg.norm(np.asarray(points[f"{s}_middle1"]) - w)
            mp_len = np.linalg.norm(shape[f"{s}_middle1"])
            if reg > 1e-4 and mp_len > 1e-4:
                sc = reg / mp_len
        for n in HAND_NAMES:
            k = f"{s}_{n}"
            if k in shape:
                points[k] = (w + shape[k] * sc).tolist()
            if k in p2:
                kp2d[k] = p2[k]
        if notes is not None:
            notes.append(f"{s} hand re-detected on crop")
    return points, kp2d
