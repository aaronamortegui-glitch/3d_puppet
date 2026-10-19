"""SAM 3D Body (Meta, 2025) - body + hands + feet on the MHR rig.

Weights: SAM License (gated on Hugging Face, request access first).
Outputs 70 keypoints (MHR70) with 21 per hand, plus focal length and
camera translation.  Expects the repo cloned into server/vendor/sam-3d-body
(see server/install_sam3d.bat).
https://github.com/facebookresearch/sam-3d-body
"""

import os
import sys

import numpy as np

from . import common

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.join(ROOT, "vendor", "sam-3d-body")
HF_REPO = os.environ.get("SAM3D_HF_REPO", "facebook/sam-3d-body-dinov3")

MHR70 = [
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_hip", "right_hip", "left_knee", "right_knee", "left_ankle",
    "right_ankle", "left_toe", "left_small_toe", "left_heel",
    "right_toe", "right_small_toe", "right_heel",
]
for _side in ("right", "left"):
    for _f in ("thumb", "index", "middle", "ring", "pinky"):
        # MHR order per finger: tip, first (DIP), second (PIP), third (MCP)
        MHR70 += [f"{_side}_{_f}_tip", f"{_side}_{_f}3", f"{_side}_{_f}2", f"{_side}_{_f}1"]
    MHR70.append(f"{_side}_wrist")
MHR70 += ["left_olecranon", "right_olecranon", "left_cubital_fossa",
          "right_cubital_fossa", "left_acromion", "right_acromion", "mhr_neck"]
assert len(MHR70) == 70

_estimator = None


def available():
    return os.path.isdir(REPO)


def _load():
    global _estimator
    if _estimator is None:
        if REPO not in sys.path:
            sys.path.insert(0, REPO)
        from notebook.utils import setup_sam_3d_body  # type: ignore
        # no detectron2 detector: we pass boxes from torchvision (detect.py)
        _estimator = setup_sam_3d_body(hf_repo_id=HF_REPO, detector_name=None,
                                       fov_name="moge2")
    return _estimator


def run(image_path, focal_px=None, focal_note="", **_):
    import torch
    rgb, used = common.load_rgb(image_path)
    h, w = rgb.shape[:2]
    est = _load()
    cam_int = None
    if focal_px:
        cam_int = torch.tensor([[[focal_px, 0, w / 2], [0, focal_px, h / 2], [0, 0, 1]]],
                               dtype=torch.float32)
    from .detect import person_boxes
    outs = est.process_one_image(rgb, bboxes=person_boxes(rgb), cam_int=cam_int)
    if not outs:
        raise RuntimeError("No person detected")
    # largest person by bbox height
    o = max(outs, key=lambda d: float(d["bbox"][3] - d["bbox"][1]))
    f = float(np.asarray(o["focal_length"]).reshape(-1)[0])
    K3 = np.asarray(o["pred_keypoints_3d"], dtype=np.float64).reshape(-1, 3)
    K2 = np.asarray(o["pred_keypoints_2d"], dtype=np.float64).reshape(-1, 2)
    t = np.asarray(o["pred_cam_t"], dtype=np.float64).reshape(3)
    body = [i for i, n in enumerate(MHR70) if "_" in n and i < 21]
    Q, err, how = common.to_camera_space(K3[body], K2[body], f, w / 2, h / 2, t=t)
    # apply the same convention to every keypoint
    scale = 0.001 if "scale=0.001" in how else 1.0
    flip = np.array([1, -1, -1]) if "axes=gl" in how else np.ones(3)
    P = K3 * scale * flip
    if "given_t=True" in how:
        P = P + t * scale * flip
    else:
        P = P - P[body].mean(0) + Q.mean(0)
    pts = {n: P[i] for i, n in enumerate(MHR70) if not n.startswith(("mhr_", "left_eye", "right_eye"))}
    notes = [f"SAM 3D Body, focal {f:.0f}px, reproj {err:.1f}px ({how})"]
    if focal_note:
        notes.append("focal source: " + focal_note)
    return common.make_result("server/sam3d_body", used, w, h, f, pts, notes)
