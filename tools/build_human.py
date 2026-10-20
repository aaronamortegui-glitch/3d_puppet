"""Build the realistic human figure from Meta's MHR body model (Apache-2.0).

    server\\.venv\\Scripts\\python.exe tools\\build_human.py [--photos <img> ...] [--name human]

MHR is the body model of SAM 3D Body: a scan-based human mesh (18 439 vertices),
a 127-joint skeleton with twist and finger joints and linear-blend skin weights.
With --photos, SAM 3D Body is run on each photo and the body shape / proportions
of the people found are averaged, so the figure looks like the people we pose.

Writes
  puppet_pose/assets/<name>.npz      mesh, UVs, skin weights, MHR joints and the
                                      55 SMPL-X joint / landmark positions (Blender
                                      axes: metres, Z up, facing -Y, feet on Z=0)
  server/assets/<name>_rest.json      the same skeleton in the format the fit uses
"""

import argparse
import glob
import json
import os
import sys

import numpy as np
import torch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))

HF = os.path.expanduser("~/.cache/huggingface/hub/models--facebook--sam-3d-body-dinov3/snapshots")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def _snapshot():
    snaps = sorted(glob.glob(os.path.join(HF, "*")))
    if not snaps:
        raise SystemExit("SAM 3D Body weights not found - run the server installer first")
    return snaps[-1]


def load_head_buffers(snap):
    sd = torch.load(os.path.join(snap, "model.ckpt"), map_location="cpu", weights_only=False)
    sd = sd.get("state_dict", sd)
    keys = ("keypoint_mapping", "scale_mean", "scale_comps")
    return {k: sd[f"head_pose.{k}"].float() for k in keys}


def shape_from_photos(paths):
    """Average SAM 3D Body identity (45) and scale (28) coefficients over photos."""
    from methods import common, sam3d_method
    from methods.detect import person_boxes
    est = sam3d_method._load()
    shapes, scales = [], []
    for p in paths:
        rgb, _ = common.load_rgb(p)
        outs = est.process_one_image(rgb, bboxes=person_boxes(rgb))
        if not outs:
            print("no person:", p)
            continue
        o = max(outs, key=lambda d: float(d["bbox"][3] - d["bbox"][1]))
        shapes.append(np.asarray(o["shape_params"], dtype=np.float32).reshape(-1))
        scales.append(np.asarray(o["scale_params"], dtype=np.float32).reshape(-1))
        print(f"{os.path.basename(p)}: shape |{np.linalg.norm(shapes[-1]):.2f}|")
    return np.mean(shapes, 0), np.mean(scales, 0)


def to_blender(p_cm):
    """MHR (cm, Y up, facing +Z) -> Blender (m, Z up, facing -Y)."""
    p = np.asarray(p_cm, dtype=np.float64) * 0.01
    return np.stack([p[..., 0], -p[..., 2], p[..., 1]], -1)


# SMPL-X joint -> MHR joint (rotation centres)
JOINT_MAP = {
    "pelvis": "root", "spine1": "c_spine1", "spine2": "c_spine2", "spine3": "c_spine3",
    "neck": "c_neck", "head": "c_head", "jaw": "c_jaw",
}
for _s, _m in (("left", "l"), ("right", "r")):
    JOINT_MAP.update({
        f"{_s}_hip": f"{_m}_upleg", f"{_s}_knee": f"{_m}_lowleg", f"{_s}_ankle": f"{_m}_foot",
        f"{_s}_foot": f"{_m}_ball", f"{_s}_collar": f"{_m}_clavicle",
        f"{_s}_shoulder": f"{_m}_uparm", f"{_s}_elbow": f"{_m}_lowarm",
        f"{_s}_wrist": f"{_m}_wrist", f"{_s}_eye_smplhf": f"{_m}_eye",
    })
    for _f in ("index", "middle", "ring", "pinky"):
        for _i in (1, 2, 3):
            JOINT_MAP[f"{_s}_{_f}{_i}"] = f"{_m}_{_f}{_i}"
    # MHR thumb0 is a carpal joint next to the wrist; thumb1..3 = CMC, MCP, IP
    for _i in (1, 2, 3):
        JOINT_MAP[f"{_s}_thumb{_i}"] = f"{_m}_thumb{_i}"

# landmarks taken from MHR's 70 surface keypoints (same ones SAM 3D Body outputs)
LANDMARKS = ["nose", "left_ear", "right_ear", "left_heel", "right_heel", "left_toe", "right_toe"]
LANDMARKS += [f"{s}_{f}_tip" for s in ("left", "right") for f in FINGERS]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photos", nargs="*", default=[])
    ap.add_argument("--name", default="human")
    ap.add_argument("--shape-from", help="reuse shape/scale from an existing <name>_rest.json")
    a = ap.parse_args()

    snap = _snapshot()
    mhr = torch.jit.load(os.path.join(snap, "assets", "mhr_model.pt"), map_location="cpu").eval()
    ct = mhr.character_torch
    head = load_head_buffers(snap)
    n_id = ct.blend_shape.shape_vectors.shape[0]
    n_face = mhr.face_expressions_model.shape_vectors.shape[0]
    n_par = ct.parameter_transform.parameter_transform.shape[1] - n_id
    n_scale = head["scale_mean"].shape[0]

    shape = np.zeros(n_id, np.float32)
    scale = np.zeros(head["scale_comps"].shape[0], np.float32)
    if a.shape_from:
        with open(a.shape_from, encoding="utf-8") as fh:
            prev = json.load(fh)
        shape, scale = np.array(prev["shape"], np.float32), np.array(prev["scale"], np.float32)
    elif a.photos:
        shape, scale = shape_from_photos(a.photos)
        cache = os.path.join(ROOT, "server", "assets", f"{a.name}_rest.json")
        with open(cache, "w", encoding="utf-8") as fh:  # keep the shape even if a later step fails
            json.dump({"shape": shape.tolist(), "scale": scale.tolist()}, fh)
    scales = head["scale_mean"] + torch.from_numpy(scale)[None] @ head["scale_comps"]
    params = torch.cat([torch.zeros(1, n_par - n_scale), scales], 1)
    with torch.no_grad():
        verts, skel = mhr(torch.from_numpy(shape)[None], params, torch.zeros(1, n_face), False)
    verts, skel = verts[0], skel[0]
    kp = (head["keypoint_mapping"] @ torch.cat([verts, skel[:, :3]], 0))[:70].numpy()

    from methods.sam3d_method import MHR70
    names = list(ct.skeleton.joint_names)
    V = to_blender(verts.numpy())
    J = to_blender(skel[:, :3].numpy())
    K = {n: to_blender(kp[i]) for i, n in enumerate(MHR70)}
    ground = V[:, 2].min()
    V[:, 2] -= ground
    J[:, 2] -= ground
    for n in K:
        K[n][2] -= ground

    rest = {s: J[names.index(m)] for s, m in JOINT_MAP.items()}
    rest.update({n: K[n] for n in LANDMARKS})
    rest["head_top"] = V[np.argmax(V[:, 2])]
    # chin: lowest point of the face on the mid-line, in front of the neck
    face = (np.abs(V[:, 0]) < 0.01) & (V[:, 1] < rest["neck"][1] - 0.06) & (V[:, 2] > rest["neck"][2])
    rest["chin"] = V[face][np.argmin(V[face][:, 2])]
    for mid, (l, r) in {"hip_mid": ("left_hip", "right_hip"), "ear_mid": ("left_ear", "right_ear"),
                        "shoulder_mid": ("left_shoulder", "right_shoulder")}.items():
        rest[mid] = (rest[l] + rest[r]) / 2

    with open(os.path.join(ROOT, "server", "assets", "puppet_rest.json"), encoding="utf-8") as fh:
        base = json.load(fh)
    missing = set(base["rest"]) - set(rest)
    if missing:
        raise SystemExit(f"missing points: {sorted(missing)}")
    out_json = {"figure": a.name, "rest": {k: [round(float(x), 5) for x in rest[k]] for k in base["rest"]},
                "parent": base["parent"], "tail": base["tail"],
                "shape": shape.tolist(), "scale": scale.tolist()}
    with open(os.path.join(ROOT, "server", "assets", f"{a.name}_rest.json"), "w", encoding="utf-8") as fh:
        json.dump(out_json, fh, indent=1)

    lbs = ct.linear_blend_skinning
    np.savez_compressed(
        os.path.join(ROOT, "puppet_pose", "assets", f"{a.name}.npz"),
        verts=V.astype(np.float32), faces=ct.mesh.faces.numpy().astype(np.int32),
        uv=ct.mesh.texcoords.numpy().astype(np.float32),
        uv_faces=ct.mesh.texcoord_faces.numpy().astype(np.int32),
        joints=J.astype(np.float32), joint_names=np.array(names),
        parents=ct.skeleton.joint_parents.numpy().astype(np.int32),
        w_vert=lbs.vert_indices_flattened.numpy().astype(np.int32),
        w_joint=lbs.skin_indices_flattened.numpy().astype(np.int16),
        w=lbs.skin_weights_flattened.numpy().astype(np.float32),
        rest_json=json.dumps(out_json["rest"]))
    h = V[:, 2].max()
    print(f"{a.name}: height {h:.3f} m, {len(V)} verts, {len(names)} joints")


if __name__ == "__main__":
    main()
