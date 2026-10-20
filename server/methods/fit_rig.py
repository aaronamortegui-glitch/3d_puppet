"""Fit the PUPPET RIG itself to the photo (no retarget loss).

Forward kinematics of the add-on's skeleton (same rest pose, same
hierarchy) runs in PyTorch.  We optimise one rotation per bone + the root
translation so that the puppet's joints/landmarks project onto the 2D
keypoints, while staying close to the 3D regressor (depth) and to an
analytic initial pose.  The add-on applies the resulting global bone
rotations directly, so what you see in Blender is exactly what was fitted.

Frames: everything here is in "W_c" = Blender-like camera-world axes
(camera at origin looking +Y, +Z up): W_c = (x_cv, z_cv, -y_cv).  The
rest skeleton (Blender armature axes) is used as-is in W_c.
"""

import json
import math
import os

import numpy as np

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
with open(os.path.join(_ASSETS, "puppet_rest.json"), encoding="utf-8") as _fh:
    _D = json.load(_fh)
REST = {k: np.array(v, dtype=np.float64) for k, v in _D["rest"].items()}
PARENT = _D["parent"]                # 55 joints, parent-first order
JOINTS = list(PARENT.keys())
JI = {j: i for i, j in enumerate(JOINTS)}
FINGERS = ("thumb", "index", "middle", "ring", "pinky")

# landmarks rigidly attached to a bone
ATTACH = {"head_top": "head", "chin": "jaw", "nose": "head", "left_ear": "head",
          "right_ear": "head"}
for _s in ("left", "right"):
    ATTACH.update({f"{_s}_heel": f"{_s}_ankle", f"{_s}_toe": f"{_s}_foot"})
    for _f in FINGERS:
        ATTACH[f"{_s}_{_f}_tip"] = f"{_s}_{_f}3"

CV_TO_WC = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)


def cv2wc(p):
    return CV_TO_WC @ np.asarray(p, dtype=np.float64)


# ---------------------------------------------------------------------------
# analytic initialisation (numpy port of the add-on's retarget specs)
# ---------------------------------------------------------------------------
def _frame(a, b):
    x = a / (np.linalg.norm(a) + 1e-12)
    y = b - x * (b @ x)
    n = np.linalg.norm(y)
    if n < 1e-9:
        return None
    y = y / n
    return np.stack([x, y, np.cross(x, y)], 1)


def _align(ra, rb, ta, tb):
    fr, ft = _frame(ra, rb), _frame(ta, tb)
    if fr is None or ft is None:
        return None
    return ft @ fr.T


def _swing(u, v):
    u = u / (np.linalg.norm(u) + 1e-12)
    v = v / (np.linalg.norm(v) + 1e-12)
    c = float(np.clip(u @ v, -1, 1))
    ax = np.cross(u, v)
    s = np.linalg.norm(ax)
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        ax = np.cross(u, [1, 0, 0])
        if np.linalg.norm(ax) < 1e-6:
            ax = np.cross(u, [0, 1, 0])
        ax /= np.linalg.norm(ax)
        return _rodrigues(ax * math.pi)
    return _rodrigues(ax / s * math.atan2(s, c))


def _rodrigues(w):
    th = np.linalg.norm(w)
    if th < 1e-12:
        return np.eye(3)
    k = w / th
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + math.sin(th) * K + (1 - math.cos(th)) * K @ K


def _mids(P):
    P = dict(P)
    for name, (a, b) in {"hip_mid": ("left_hip", "right_hip"),
                         "shoulder_mid": ("left_shoulder", "right_shoulder"),
                         "ear_mid": ("left_ear", "right_ear"),
                         "eye_mid": ("left_eye_smplhf", "right_eye_smplhf")}.items():
        if name not in P and a in P and b in P:
            P[name] = (P[a] + P[b]) / 2
    return P


_REST_M = _mids(REST)


def _specs():
    S = {"pelvis": ("frame", ("right_hip", "left_hip"), ("hip_mid", "shoulder_mid")),
         "spine1": ("dir", [("hip_mid", "shoulder_mid")]),
         "spine2": ("dir", [("hip_mid", "shoulder_mid")]),
         "spine3": ("frame", ("hip_mid", "shoulder_mid"), ("right_shoulder", "left_shoulder")),
         "neck": ("dir", [("neck", "head"), ("shoulder_mid", "ear_mid")]),
         "head": ("frame", ("right_eye_smplhf", "left_eye_smplhf"), ("eye_mid", "nose"))}
    for s in ("left", "right"):
        S[f"{s}_collar"] = ("dir", [(f"{s}_collar", f"{s}_shoulder"), ("shoulder_mid", f"{s}_shoulder")])
        S[f"{s}_shoulder"] = ("dir", [(f"{s}_shoulder", f"{s}_elbow")])
        S[f"{s}_elbow"] = ("frame", (f"{s}_elbow", f"{s}_wrist"), (f"{s}_pinky1", f"{s}_index1"))
        S[f"{s}_wrist"] = ("frame", (f"{s}_wrist", f"{s}_middle1"), (f"{s}_pinky1", f"{s}_index1"))
        S[f"{s}_hip"] = ("dir", [(f"{s}_hip", f"{s}_knee")])
        S[f"{s}_knee"] = ("dir", [(f"{s}_knee", f"{s}_ankle")])
        S[f"{s}_ankle"] = ("dir", [(f"{s}_heel", f"{s}_toe"), (f"{s}_ankle", f"{s}_foot")])
        for f in FINGERS:
            b1, b2, b3 = (f"{s}_{f}{i}" for i in (1, 2, 3))
            S[b1] = ("dir", [(b1, b2)])
            S[b2] = ("dir", [(b2, b3)])
            S[b3] = ("dir", [(b3, f"{s}_{f}_tip")])
    return S


SPECS = _specs()


def init_globals(T):
    """T: {name: W_c position}.  Returns {joint: 3x3 global delta}."""
    T = _mids(T)
    G = {}
    for j in JOINTS:
        p = PARENT[j]
        gp = G[p] if p else np.eye(3)
        spec = SPECS.get(j)
        g = None
        if spec and spec[0] == "frame":
            (a0, a1), (b0, b1) = spec[1], spec[2]
            if all(n in T and n in _REST_M for n in (a0, a1, b0, b1)):
                ta, tb = T[a1] - T[a0], T[b1] - T[b0]
                ra, rb = _REST_M[a1] - _REST_M[a0], _REST_M[b1] - _REST_M[b0]
                ang = math.acos(np.clip(abs(ta @ tb) / (np.linalg.norm(ta) * np.linalg.norm(tb) + 1e-12), 0, 1))
                if ang > 0.17:
                    g = _align(ra, rb, ta, tb)
            if g is None and all(n in T for n in (a0, a1)):
                g = _swing(gp @ (_REST_M[a1] - _REST_M[a0]), T[a1] - T[a0]) @ gp
        elif spec:
            for a0, a1 in spec[1]:
                if a0 in T and a1 in T and a0 in _REST_M and a1 in _REST_M:
                    g = _swing(gp @ (_REST_M[a1] - _REST_M[a0]), T[a1] - T[a0]) @ gp
                    break
        if g is None:
            if j.endswith("_shoulder"):  # unseen arm hangs relaxed
                ang = math.radians(72) * (1 if j.startswith("left") else -1)
                g = gp @ _rodrigues(np.array([0, ang, 0]))
            else:
                g = gp
        G[j] = g
    return G


# ---------------------------------------------------------------------------
# torch FK + optimisation
# ---------------------------------------------------------------------------
def _axis_angle_to_mat(w):
    import torch
    th = w.norm(dim=-1, keepdim=True).clamp(min=1e-8)
    k = w / th
    K = torch.zeros(w.shape[:-1] + (3, 3), device=w.device, dtype=w.dtype)
    K[..., 0, 1], K[..., 0, 2] = -k[..., 2], k[..., 1]
    K[..., 1, 0], K[..., 1, 2] = k[..., 2], -k[..., 0]
    K[..., 2, 0], K[..., 2, 1] = -k[..., 1], k[..., 0]
    s, c = torch.sin(th)[..., None], torch.cos(th)[..., None]
    eye = torch.eye(3, device=w.device, dtype=w.dtype).expand_as(K)
    return eye + s * K + (1 - c) * (K @ K)


def fit_rig(points_cv, kp2d, f, cx, cy, W, H, iters=500, device="cuda", log=None):
    """points_cv: regressor (or point-fitted) 3D points, OpenCV camera space.
    kp2d: {name: (u, v, conf)}.  Returns dict with G (global deltas, W_c),
    pelvis_wc, points3d (cv) of the fitted rig and stats."""
    import torch
    dev = device if torch.cuda.is_available() else "cpu"
    T = {k: cv2wc(v) for k, v in points_cv.items()}
    G0 = init_globals(T)
    # local rotations of the init
    L0 = []
    for j in JOINTS:
        p = PARENT[j]
        L0.append((G0[p].T @ G0[j]) if p else G0[j])
    L0 = torch.tensor(np.stack(L0), dtype=torch.float32, device=dev)

    names = JOINTS + [k for k in ATTACH]
    owner = [JI[n] for n in JOINTS] + [JI[ATTACH[k]] for k in ATTACH]
    rest_all = torch.tensor(np.stack([REST[n] for n in names]), dtype=torch.float32, device=dev)
    rest_j = rest_all[:len(JOINTS)]
    par = [JI[PARENT[j]] if PARENT[j] else -1 for j in JOINTS]

    def fk(w, t):
        L = _axis_angle_to_mat(w) @ L0
        Gs, Ps = [], []
        for i in range(len(JOINTS)):
            p = par[i]
            if p < 0:
                g = L[i]
                pos = t
            else:
                g = Gs[p] @ L[i]
                pos = Ps[p] + Gs[p] @ (rest_j[i] - rest_j[p])
            Gs.append(g)
            Ps.append(pos)
        Gt = torch.stack(Gs)
        Pj = torch.stack(Ps)
        own = torch.tensor(owner[len(JOINTS):], device=dev)
        Pl = Pj[own] + (Gt[own] @ (rest_all[len(JOINTS):] - rest_j[own])[..., None])[..., 0]
        return Gt, torch.cat([Pj, Pl], 0)

    # root translation init: align FK(init) with targets in 3D
    w = torch.zeros(len(JOINTS), 3, device=dev, requires_grad=True)
    with torch.no_grad():
        _, P0 = fk(w, torch.zeros(3, device=dev))
    common = [i for i, n in enumerate(names) if n in T]
    Tt = torch.tensor(np.stack([T[names[i]] for i in common]), dtype=torch.float32, device=dev)
    t0 = (Tt - P0[common]).mean(0)
    t = torch.nn.Parameter(t0.clone())
    w = torch.nn.Parameter(torch.zeros(len(JOINTS), 3, device=dev))

    # 2D observations
    edge = 0.015 * max(W, H)
    obs = [(names.index(n), kp2d[n]) for n in names if n in kp2d and kp2d[n][2] >= 0.4
           and edge <= kp2d[n][0] <= W - edge and edge <= kp2d[n][1] <= H - edge]
    oi = torch.tensor([i for i, _ in obs], device=dev, dtype=torch.long)
    ouv = torch.tensor([[k[0], k[1]] for _, k in obs], dtype=torch.float32, device=dev)
    oc = torch.tensor([k[2] for _, k in obs], dtype=torch.float32, device=dev)

    def _w(n):
        if any(f"_{fg}" in n for fg in FINGERS):
            return 0.7
        if n.endswith("_hip"):
            return 0.3
        if n.endswith("_ear"):
            return 0.5
        return 1.0
    ow = torch.tensor([_w(names[i]) for i, _ in obs], dtype=torch.float32, device=dev)
    scale_px = max(W, H) / 100.0
    # 3D prior: centred shapes, depth weighted more (2D handles x/z of W_c)
    cmask = torch.tensor(common, device=dev)
    zw = torch.tensor([1.0, 3.0, 1.0], device=dev)  # W_c y = depth
    prior_w = torch.ones(len(JOINTS), device=dev) * 0.02
    for j in ("spine1", "spine2", "spine3", "neck"):
        prior_w[JI[j]] = 0.2

    def project(P):
        x, d, z = P[:, 0], P[:, 1].clamp(min=0.05), P[:, 2]   # W_c -> cv: (x, -z, d)
        return torch.stack([f * x / d + cx, f * (-z) / d + cy], 1)

    opt = torch.optim.Adam([w, t], lr=0.02)
    for it in range(iters):
        opt.zero_grad()
        G, P = fk(w, t)
        loss = torch.zeros((), device=dev)
        if len(obs):
            r = (project(P[oi]) - ouv) / scale_px
            rho = (r ** 2).sum(1)
            l2d = (oc * ow * rho / (rho + 4.0)).sum() / len(obs) * 10  # Geman-McClure
            loss = loss + l2d
        Pc = P[cmask] - P[cmask].mean(0)
        Tc = Tt - Tt.mean(0)
        loss = loss + 2.0 * (((Pc - Tc) * zw) ** 2).sum(1).mean()
        loss = loss + (prior_w[:, None] * w ** 2).sum()
        loss.backward()
        opt.step()
        if it == int(iters * 0.6):
            for g in opt.param_groups:
                g["lr"] = 0.005
    with torch.no_grad():
        G, P = fk(w, t)
        info = {}
        if len(obs):
            e = (project(P[oi]) - ouv).norm(dim=1)
            body = torch.tensor([not any(f"_{fg}" in names[i] for fg in FINGERS) for i, _ in obs], device=dev)
            # medians: a few hallucinated out-of-frame points must not dominate
            info["rig_px_body"] = round(float(e[body].median()), 1) if body.any() else None
            info["rig_px_hands"] = round(float(e[~body].median()), 1) if (~body).any() else None
    Gn = G.cpu().numpy()
    Pn = P.cpu().numpy()
    WC_TO_CV = CV_TO_WC.T
    return {
        "G": {j: Gn[i].tolist() for i, j in enumerate(JOINTS)},
        "pelvis_wc": Pn[0].tolist(),
        "points3d": {n: (WC_TO_CV @ Pn[i]).tolist() for i, n in enumerate(names)},
        "info": info,
    }
