"""Pixel-accurate fitting of 3D points to 2D keypoints.

Takes the 3D points of any regressor (SAM 3D Body, NLF, MediaPipe) and
moves them so that:
  * their projection matches high-precision 2D keypoints (RTMW),
  * bone lengths equal the PUPPET's bone lengths (so after retargeting the
    puppet lands exactly on the photo),
  * bone directions / relative depth stay close to the regressor where
    the 2D evidence is weak (occluded / out of frame).
It also fixes the front/back (left/right) ambiguity by comparing labels
with the 2D detector.
"""

import json
import os

import numpy as np

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
with open(os.path.join(ASSETS, "puppet_rest.json"), encoding="utf-8") as _fh:
    _REST_RAW = json.load(_fh)
# rest is in Blender axes (x left, -y front, z up); lengths are all we need
REST = {k: np.array(v) for k, v in _REST_RAW["rest"].items()}

FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def _edges():
    e = []
    for s in ("left", "right"):
        e += [(f"{s}_shoulder", f"{s}_elbow", 1.0), (f"{s}_elbow", f"{s}_wrist", 1.0),
              (f"{s}_hip", f"{s}_knee", 1.0), (f"{s}_knee", f"{s}_ankle", 1.0),
              (f"{s}_ankle", f"{s}_heel", 0.5), (f"{s}_heel", f"{s}_toe", 0.5),
              (f"{s}_shoulder", f"{s}_hip", 0.3), ("pelvis", f"{s}_hip", 0.5),
              (f"{s}_collar", f"{s}_shoulder", 0.3)]
        for f in FINGERS:
            e += [(f"{s}_wrist", f"{s}_{f}1", 1.0), (f"{s}_{f}1", f"{s}_{f}2", 1.0),
                  (f"{s}_{f}2", f"{s}_{f}3", 1.0), (f"{s}_{f}3", f"{s}_{f}_tip", 1.0)]
        e += [(f"{s}_index1", f"{s}_middle1", 1.0), (f"{s}_middle1", f"{s}_ring1", 1.0),
              (f"{s}_ring1", f"{s}_pinky1", 1.0), (f"{s}_index1", f"{s}_pinky1", 1.0)]
    e += [("left_shoulder", "right_shoulder", 1.0), ("left_hip", "right_hip", 1.0),
          ("left_ear", "right_ear", 0.5), ("nose", "left_ear", 0.5), ("nose", "right_ear", 0.5),
          ("pelvis", "spine1", 0.3), ("spine3", "neck", 0.3), ("neck", "head", 0.3)]
    return e


EDGES = _edges()


def _swap(name):
    if name.startswith("left_"):
        return "right_" + name[5:]
    if name.startswith("right_"):
        return "left_" + name[6:]
    return name


def flip_front_back(points):
    hips = [points[k] for k in ("left_hip", "right_hip") if k in points]
    zc = float(np.mean([h[2] for h in hips])) if hips else float(
        np.mean([p[2] for p in points.values()]))
    out = {}
    for k, p in points.items():
        x, y, z = p
        z2 = max(2 * zc - z, 0.05)
        s = z2 / z if z > 1e-6 else 1.0
        out[_swap(k)] = np.array([x * s, y * s, z2])
    return out


def _proj(P, f, cx, cy):
    return np.stack([f * P[:, 0] / P[:, 2] + cx, f * P[:, 1] / P[:, 2] + cy], 1)


def label_error(points, kp2d, f, cx, cy, names):
    """Mean 2D distance between projected 3D points and detections (torso/limbs)."""
    d = []
    for n in names:
        if n in points and n in kp2d and kp2d[n][2] > 0.4:
            p = np.asarray(points[n])
            if p[2] > 1e-3:
                uv = np.array([f * p[0] / p[2] + cx, f * p[1] / p[2] + cy])
                d.append(np.linalg.norm(uv - np.array(kp2d[n][:2])))
    return float(np.mean(d)) if d else 1e9


LR_CHECK = ["left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
            "left_wrist", "right_wrist", "left_hip", "right_hip", "left_ear", "right_ear",
            "left_knee", "right_knee"]


def refocus(points, f0, f1):
    """Re-express camera-space points estimated with focal f0 as if the lens
    were f1, keeping every 2D projection and the body's depth extent: the
    whole body moves back/forward (dolly) by Z_root*(f1/f0 - 1)."""
    P = {k: np.asarray(v, dtype=np.float64) for k, v in points.items()}
    zr = float(np.median([p[2] for p in P.values()]))
    shift = zr * (f1 / f0 - 1.0)
    out = {}
    for k, (x, y, z) in P.items():
        z1 = z + shift
        s = z1 / z * f0 / f1
        out[k] = np.array([x * s, y * s, z1])
    return out


def lens_search(points, kp2d, f0, cx, cy, W, H, candidates_35=None, **kw):
    """Fit the puppet for several focal lengths and keep the one whose
    perspective is most consistent with rigid puppet proportions + 2D.
    Returns (best_f, best_points, best_info, table)."""
    diag = (W * W + H * H) ** 0.5
    to_px = lambda f35: f35 / 43.2666 * diag  # noqa: E731
    cands = candidates_35 or [18, 24, 28, 35, 42, 50, 60, 70, 85, 105, 135]
    table, best = [], None
    for f35 in cands:
        f1 = to_px(f35)
        p1 = refocus(points, f0, f1)
        pts, info = fit(p1, kp2d, f1, cx, cy, W, H, iters=kw.get("iters", 400))
        table.append((f35, round(info.get("loss", 1e9), 4), info.get("fit_px_body")))
        if best is None or info.get("loss", 1e9) < best[3].get("loss", 1e9):
            best = (f1, pts, f35, info)
    return best[0], best[1], best[3], table, best[2]


def fit(points, kp2d, f, cx, cy, W, H, iters=600, w2d=1.0, wbone=200.0,
        wdir=0.5, wdepth=30.0, min_conf=0.4, device="cuda", log=None):
    """points: {name: [x,y,z]} OpenCV camera space (m). kp2d: {name: (u,v,conf)}.
    Returns (new_points, info)."""
    import torch

    pts = {k: np.asarray(v, dtype=np.float64) for k, v in points.items()}
    info = {}
    # 1) front/back ambiguity: compare label consistency with the 2D detector
    e0 = label_error(pts, kp2d, f, cx, cy, LR_CHECK)
    flipped = flip_front_back(pts)
    e1 = label_error(flipped, kp2d, f, cx, cy, LR_CHECK)
    if e1 < 0.7 * e0:
        pts = flipped
        info["auto_flip"] = True
    info["label_err_px"] = round(min(e0, e1), 1)

    names = sorted(pts)
    idx = {n: i for i, n in enumerate(names)}
    M = np.stack([pts[n] for n in names])

    # 2) rescale the regressor skeleton to puppet proportions (about its centroid)
    edges = [(a, b, w) for a, b, w in EDGES if a in idx and b in idx and a in REST and b in REST]
    if not edges:
        return points, {"error": "no edges"}
    ratio = np.median([np.linalg.norm(REST[a] - REST[b]) /
                       max(np.linalg.norm(M[idx[a]] - M[idx[b]]), 1e-6) for a, b, _ in edges])
    # scaling about the camera centre keeps every projection identical:
    # the skeleton just moves nearer/farther to have the puppet's size
    M0 = M * ratio
    info["scale_to_puppet"] = round(float(ratio), 3)

    dev = device if torch.cuda.is_available() else "cpu"
    T = lambda a: torch.tensor(np.asarray(a), dtype=torch.float32, device=dev)  # noqa: E731
    P = torch.nn.Parameter(T(M0))
    init = T(M0)
    ea = torch.tensor([idx[a] for a, b, w in edges], device=dev)
    eb = torch.tensor([idx[b] for a, b, w in edges], device=dev)
    ew = T([w for a, b, w in edges])
    L = T([np.linalg.norm(REST[a] - REST[b]) for a, b, w in edges])
    init_dir = torch.nn.functional.normalize(init[eb] - init[ea], dim=1)

    # keypoints glued to the image border are usually guesses for cropped limbs
    edge = 0.015 * max(W, H)
    obs = [(idx[n], kp2d[n]) for n in names if n in kp2d and kp2d[n][2] >= min_conf
           and edge <= kp2d[n][0] <= W - edge and edge <= kp2d[n][1] <= H - edge]
    if len(obs) < 4:
        info["fit"] = "skipped (few 2D points)"
        return {n: M0[i].tolist() for i, n in enumerate(names)}, info
    oi = torch.tensor([i for i, _ in obs], device=dev)
    ouv = T([[k[0], k[1]] for _, k in obs])
    oc = T([k[2] for _, k in obs])
    # finger points get a bit less weight than body (detections are noisier)
    def _w(n):
        if any(f"_{fg}" in n for fg in FINGERS):
            return 0.5   # fingers: noisier detections
        if n.endswith("_hip"):
            return 0.3   # COCO hips are not skeleton hip joints (and often cropped)
        return 1.0
    hw = T([_w(names[i]) for i, _ in obs])
    scale_px = max(W, H) / 100.0  # 1 unit = 1% of image size

    # an edge is "seen" if both ends are observed with good confidence
    seen = set(i for i, _ in obs)
    edge_seen = T([1.0 if (idx[a] in seen and idx[b] in seen) else 0.0 for a, b, w in edges])

    dz = torch.nn.Parameter(torch.zeros(1, device=dev))  # free global depth shift
    opt = torch.optim.Adam([P, dz], lr=0.01)
    for it in range(iters):
        opt.zero_grad()
        z = P[:, 2].clamp(min=0.05)
        uv = torch.stack([f * P[:, 0] / z + cx, f * P[:, 1] / z + cy], 1)
        r = (uv[oi] - ouv) / scale_px
        l2d = (oc * hw * torch.nn.functional.huber_loss(r, torch.zeros_like(r), reduction="none",
                                                         delta=1.0).sum(1)).sum() / len(obs)
        d = P[eb] - P[ea]
        ln = d.norm(dim=1)
        lbone = (ew * (ln - L) ** 2).sum() / len(edges)
        cosv = (torch.nn.functional.normalize(d, dim=1) * init_dir).sum(1)
        ldir = ((1 - edge_seen * 0.8) * (1 - cosv)).sum() / len(edges)
        # every point keeps the regressor's depth (up to one global shift):
        # without this, points slide along their viewing rays (2D unchanged)
        ldepth = ((P[:, 2] - init[:, 2] - dz) ** 2).mean()
        loss = w2d * l2d + wbone * lbone + wdir * ldir + wdepth * ldepth
        loss.backward()
        opt.step()
        if it == iters // 2:
            for g in opt.param_groups:
                g["lr"] = 0.003
    with torch.no_grad():
        z = P[:, 2].clamp(min=0.05)
        uv = torch.stack([f * P[:, 0] / z + cx, f * P[:, 1] / z + cy], 1)
        err = (uv[oi] - ouv).norm(dim=1)
        info["fit_px_mean"] = round(float(err.mean()), 1)
        info["fit_px_body"] = round(float(err[hw > 0.9].mean()), 1) if (hw > 0.9).any() else None
        info["bone_err_mm"] = round(float(((P[eb] - P[ea]).norm(dim=1) - L).abs().mean() * 1000), 1)
        info["loss"] = float(loss.detach())
    Pn = P.detach().cpu().numpy()
    return {n: Pn[i].tolist() for i, n in enumerate(names)}, info
