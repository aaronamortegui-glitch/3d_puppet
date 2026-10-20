"""Measure how well the POSED PUPPET reprojects onto the result's 2D points.

    blender -b --factory-startup --python tools/measure_overlay.py -- <results_dir>

Per result prints mean pixel error for body joints and for hand joints,
plus the worst joints.  This isolates retarget error (points -> rig).
"""

import glob
import json
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import puppet_pose  # noqa: E402
from puppet_pose import pose_apply, puppet_builder  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
puppet_pose.register()


def project(cam, p, W, H):
    from bpy_extras.object_utils import world_to_camera_view
    co = world_to_camera_view(bpy.context.scene, cam, p)
    return co.x * W, (1 - co.y) * H


for path in sorted(glob.glob(os.path.join(argv[0], "*.json"))):
    with open(path, encoding="utf-8") as fh:
        r = json.load(fh)
    if not isinstance(r, dict) or "points3d" not in r:
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    arm = puppet_builder.build_puppet("P")
    cam = pose_apply.apply_result(bpy.context, arm, r)
    bpy.context.view_layer.update()
    W, H = r["image"]["width"], r["image"]["height"]
    c = r["camera"]
    target = {}
    for k, (x, y, z) in r["points3d"].items():
        target[k] = (c["fx"] * x / z + c["cx"], c["fy"] * y / z + c["cy"])
    posed = pose_apply.posed_points(arm)
    body, hand = [], []
    for k, uv in target.items():
        if k not in posed:
            continue
        pu = project(cam, posed[k], W, H)
        e = ((pu[0] - uv[0]) ** 2 + (pu[1] - uv[1]) ** 2) ** 0.5
        (hand if any(f"_{f}" in k for f in ("thumb", "index", "middle", "ring", "pinky")) else body).append((e, k))
    body.sort(reverse=True)
    hand.sort(reverse=True)
    mb = sum(e for e, _ in body) / max(len(body), 1)
    mh = sum(e for e, _ in hand) / max(len(hand), 1)
    print(f"{os.path.basename(path)[:48]:48s} body {mb:6.1f}px  hand {mh:6.1f}px  "
          f"worst {[(round(e), k) for e, k in (body + hand)[:0]] or ''}"
          f"{[(round(e), k) for e, k in sorted(body + hand, reverse=True)[:3]]}")
