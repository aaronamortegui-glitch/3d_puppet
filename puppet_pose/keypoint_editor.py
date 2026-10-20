# SPDX-License-Identifier: GPL-3.0-or-later
"""Manual 2D keypoint correction.

One empty per keypoint, placed on the photo as seen through the puppet
camera (on the viewing ray, at the puppet joint's depth).  The user drags
the empties in camera view; re-fit reads their pixel positions back and
sends them to the pose server, which re-fits the rig.  Hidden empties are
ignored (confidence 0).
"""

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

from . import pose_apply
from . import skeleton as sk

COLL = "Puppet_Keypoints"
BODY = ["nose", "left_eye_smplhf", "right_eye_smplhf", "left_ear", "right_ear",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_hip", "right_hip", "left_knee",
        "right_knee", "left_ankle", "right_ankle", "left_heel", "right_heel",
        "left_toe", "right_toe"]
HAND = [f"{f}{i}" for f in sk.FINGERS for i in (1, 2, 3)] + [f"{f}_tip" for f in sk.FINGERS]
ALL = BODY + [f"{s}_{n}" for s in sk.SIDES for n in HAND]


def _collection(context, clear=True):
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        coll = bpy.data.collections.new(COLL)
        context.scene.collection.children.link(coll)
    elif clear:
        for o in list(coll.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    return coll


def _pixel_to_world(cam, cam_info, u, v, depth):
    f, cx, cy = cam_info["fx"], cam_info["cx"], cam_info["cy"]
    local = Vector(((u - cx) / f * depth, -(v - cy) / f * depth, -depth))
    return cam.matrix_world @ local


def create(context, arm, cam, result):
    """Create/refresh the keypoint empties for `result`."""
    coll = _collection(context)
    context.view_layer.update()
    cam_info = result["camera"]
    p2 = result.get("points2d", {})
    posed = pose_apply.posed_points(arm)
    inv = cam.matrix_world.inverted()
    scene = context.scene
    W, H = scene.render.resolution_x, scene.render.resolution_y
    made = 0
    for name in ALL:
        if name not in posed:
            continue
        depth = max(-(inv @ posed[name]).z, 0.05)
        if name in p2:
            u, v = p2[name][0], p2[name][1]
            conf = p2[name][2] if len(p2[name]) > 2 else 1.0
        else:  # not detected: start at the puppet's own projection, inactive
            co = world_to_camera_view(scene, cam, posed[name])
            u, v, conf = co.x * W, (1 - co.y) * H, 0.0
        e = bpy.data.objects.new("KP_" + name, None)
        e.empty_display_type = "SPHERE"
        hand = any(f"_{f}" in name for f in sk.FINGERS)
        e.empty_display_size = depth * (0.004 if hand else 0.008)
        e.location = _pixel_to_world(cam, cam_info, u, v, depth)
        e.show_in_front = True
        e["kp_name"] = name
        e["u0"], e["v0"], e["conf"] = float(u), float(v), float(conf)
        coll.objects.link(e)
        made += 1
    return made


def read(context, cam):
    """-> {name: [u, v, conf]} for moved / hidden empties only."""
    coll = bpy.data.collections.get(COLL)
    if coll is None:
        return {}
    context.view_layer.update()  # fresh matrix_world for moved/new empties
    scene = context.scene
    W, H = scene.render.resolution_x, scene.render.resolution_y
    out = {}
    for e in coll.objects:
        name = e.get("kp_name")
        if not name:
            continue
        if e.hide_get() or e.hide_viewport:
            out[name] = [e["u0"], e["v0"], 0.0]     # user disabled this point
            continue
        co = world_to_camera_view(scene, cam, e.matrix_world.translation)
        u, v = co.x * W, (1 - co.y) * H
        if abs(u - e["u0"]) + abs(v - e["v0"]) > 1.5:
            out[name] = [u, v, 1.0]                   # user moved it
    return out


def current(context, cam, result):
    """All keypoints (edited where moved) as {name: [u, v, conf]}."""
    kp = {k: list(v) + ([1.0] if len(v) == 2 else []) for k, v in result.get("points2d", {}).items()}
    kp.update(read(context, cam))
    return {k: v for k, v in kp.items() if v[2] > 0}
