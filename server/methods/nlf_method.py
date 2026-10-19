"""NLF - Neural Localizer Fields (Sarandi & Pons-Moll, NeurIPS 2024).

Code MIT, weights non-commercial research only.  Single TorchScript
file, returns SMPL-X joints + vertices with a full perspective camera.
https://github.com/isarandi/nlf
"""

import os
import urllib.request

import numpy as np

from . import common

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(ROOT, "models", "nlf", "nlf_l_multi.torchscript")
MODEL_URL = "https://bit.ly/nlf_l_pt"

_model = None


def available():
    try:
        import torch  # noqa: F401
        return torch.cuda.is_available()
    except Exception:
        return False


def _load():
    global _model
    if _model is None:
        import torch
        import torchvision  # noqa: F401  registers torchvision::nms for TorchScript
        if not os.path.exists(MODEL_PATH):
            os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        _model = torch.jit.load(MODEL_PATH).cuda().eval()
    return _model


def run(image_path, focal_px=None, focal_note="", **_):
    import torch
    rgb, used = common.load_rgb(image_path)
    h, w = rgb.shape[:2]
    f = focal_px or common.focal_px_from_35mm(35.0, w, h)
    model = _load()
    img = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).cuda()
    K = torch.tensor([[[f, 0, w / 2], [0, f, h / 2], [0, 0, 1]]],
                     dtype=torch.float32, device="cuda")
    with torch.inference_mode():
        pred = None
        for thr in (0.3, 0.1):  # retry with a looser detector (mannequins, crops)
            pred = model.detect_smpl_batched(
                img, intrinsic_matrix=K, model_name="smplx", detector_threshold=thr,
                suppress_implausible_poses=False, num_aug=2)
            if len(pred["joints3d"][0]):
                break
        if not len(pred["joints3d"][0]):
            # fallback: our own person boxes (or the whole image), NLF xywh+conf
            from .detect import person_boxes
            b = person_boxes(rgb, thr=0.3)
            xywh = np.concatenate([b[:, :2], b[:, 2:4] - b[:, :2], np.ones((len(b), 1))], 1)
            boxes = [torch.tensor(xywh, dtype=torch.float32, device="cuda")]
            pred = model.estimate_smpl_batched(img, boxes, intrinsic_matrix=K,
                                               model_name="smplx", num_aug=2)
    if not len(pred["joints3d"][0]):
        raise RuntimeError("No person detected")
    # largest person (by 2D extent)
    j2 = pred["joints2d"][0].cpu().numpy()
    idx = int(np.argmax([np.ptp(p[:, 1]) for p in j2]))
    J3 = pred["joints3d"][0][idx].cpu().numpy()
    V3 = pred["vertices3d"][0][idx].cpu().numpy()
    J2 = j2[idx]
    n = min(len(J3), len(common.SMPLX_JOINTS))
    names = common.SMPLX_JOINTS[:n]
    vnames = list(common.SMPLX_VERTEX_POINTS)
    vids = [common.SMPLX_VERTEX_POINTS[k] for k in vnames]
    P3 = np.concatenate([J3[:n], V3[vids]], 0)
    # 2D for the vertex points: project with the same camera after unit fix
    Qcam, err, how = common.to_camera_space(J3[:n], J2[:n], f, w / 2, h / 2,
                                            t=np.zeros(3))
    scale = 0.001 if "scale=0.001" in how else 1.0
    P = P3 * scale
    if "axes=gl" in how:
        P = P * np.array([1, -1, -1])
    if "given_t=False" in how:
        P = P - P[:n].mean(0) + Qcam.mean(0)
    pts = dict(zip(names + vnames, P))
    notes = [f"NLF SMPL-X, reproj {err:.1f}px ({how})"]
    if focal_note:
        notes.append("focal source: " + focal_note)
    extra = {}
    try:  # SMPL-X axis-angle, joint order = SMPLX_JOINTS (55 x 3)
        pose = pred["pose"][0][idx].cpu().numpy().reshape(-1, 3)
        if len(pose) >= 55:
            extra["rotations"] = {n: pose[i].tolist() for i, n in enumerate(common.SMPLX_JOINTS)}
    except Exception:
        pass
    return common.make_result("server/nlf", used, w, h, f, pts, notes, **extra)
