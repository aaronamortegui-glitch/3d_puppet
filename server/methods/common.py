"""Helpers shared by the pose-server methods.

Every method returns the add-on's result schema (see
puppet_pose/pose_apply.py): named 3D points in OpenCV camera space
(meters) + pinhole intrinsics.
"""

import math

import numpy as np

# SMPL-X vertex ids for points that are not joints (from smplx/vertex_ids.py)
SMPLX_VERTEX_POINTS = {
    "nose": 9120, "left_ear": 6, "right_ear": 616,
    "left_toe": 5770, "left_heel": 8846, "right_toe": 8463, "right_heel": 8635,
    "left_thumb_tip": 5361, "left_index_tip": 4933, "left_middle_tip": 5058,
    "left_ring_tip": 5169, "left_pinky_tip": 5286,
    "right_thumb_tip": 8079, "right_index_tip": 7669, "right_middle_tip": 7794,
    "right_ring_tip": 7905, "right_pinky_tip": 8022,
}

SMPLX_JOINTS = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee",
    "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot",
    "neck", "left_collar", "right_collar", "head", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
    "jaw", "left_eye_smplhf", "right_eye_smplhf",
] + [f"{s}_{f}{i}" for s in ("left", "right")
     for f in ("index", "middle", "pinky", "ring", "thumb") for i in (1, 2, 3)]


def exif_focal_35mm(path):
    try:
        from PIL import Image
        v = Image.open(path).getexif().get_ifd(0x8769).get(0xA405)
        return float(v) if v else None
    except Exception:
        return None


def focal_px_from_35mm(f35, w, h):
    return f35 / math.hypot(36.0, 24.0) * math.hypot(w, h)


def load_rgb(path):
    """RGB uint8 array with EXIF orientation applied, plus the path of an
    upright copy (Blender ignores EXIF rotation)."""
    import os
    import tempfile
    from PIL import Image, ImageOps
    im = Image.open(path)
    orient = im.getexif().get(0x0112, 1) or 1
    up = ImageOps.exif_transpose(im).convert("RGB")
    used = path
    if orient != 1:
        used = os.path.join(tempfile.gettempdir(), "puppet_pose_" + os.path.splitext(
            os.path.basename(path))[0] + "_upright.png")
        up.save(used)
    return np.asarray(up), used


def project(P, f, cx, cy):
    z = np.clip(P[:, 2], 1e-3, None)
    return np.stack([f * P[:, 0] / z + cx, f * P[:, 1] / z + cy], 1)


def solve_translation(X, uv, f, cx, cy, w=None):
    rows, rhs = [], []
    w = np.ones(len(X)) if w is None else w
    for (x, y, z), (u, v), wi in zip(X, uv, w):
        du, dv = u - cx, v - cy
        rows += [wi * np.array([f, 0.0, -du]), wi * np.array([0.0, f, -dv])]
        rhs += [wi * (du * z - f * x), wi * (dv * z - f * y)]
    t, *_ = np.linalg.lstsq(np.array(rows), np.array(rhs), rcond=None)
    t[2] = max(t[2], 0.1)
    return t


def to_camera_space(P3, P2, f, cx, cy, t=None):
    """Bring model 3D points into OpenCV camera space, meters.

    Tries unit scales and the y/z flip conventions used by HMR-style
    models; keeps the variant whose projection best matches the 2D
    keypoints, re-solving the translation by least squares.
    Returns (points_cam, reprojection_error_px, description).
    """
    P3 = np.asarray(P3, dtype=np.float64)
    P2 = np.asarray(P2, dtype=np.float64)
    best = None
    for scale in (1.0, 0.001):
        for flip_name, flip in (("cv", np.diag([1, 1, 1])),
                                ("gl", np.diag([1, -1, -1]))):
            for with_t in ((True, False) if t is not None else (False,)):
                Q = (P3 * scale) @ flip.T
                if with_t:
                    Q = Q + np.asarray(t) * scale @ flip.T
                    if np.median(Q[:, 2]) <= 0:
                        continue
                    tt = np.zeros(3)
                else:
                    tt = solve_translation(Q - Q.mean(0), P2, f, cx, cy)
                    Q = Q - Q.mean(0) + tt
                err = np.median(np.linalg.norm(project(Q, f, cx, cy) - P2, axis=1))
                height = np.ptp(Q[:, 1]) if len(Q) else 0
                if not 0.2 < height < 3.0 and len(Q) > 20:
                    err += 1e6  # implausible unit scale
                if best is None or err < best[1]:
                    best = (Q, err, f"scale={scale} axes={flip_name} given_t={with_t}")
    return best


def make_result(backend, image_path, w, h, f, points, notes=None, cx=None, cy=None,
                **extra):
    res = {
        "backend": backend,
        "image": {"path": image_path, "width": int(w), "height": int(h)},
        "camera": {"fx": float(f), "fy": float(f),
                   "cx": float(w / 2 if cx is None else cx),
                   "cy": float(h / 2 if cy is None else cy)},
        "points3d": {k: [float(x) for x in v] for k, v in points.items()},
        "notes": notes or [],
    }
    res.update(extra)
    return res
