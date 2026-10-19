"""Shared helpers for the Blender test scripts."""
import math

import bpy
from mathutils import Euler, Matrix, Vector

from puppet_pose import hand_controls, puppet_builder
from puppet_pose import skeleton as sk


def landmark_positions(arm):
    """World positions of every named point (joints + landmarks) of a posed rig."""
    mw = arm.matrix_world
    pts = {}
    for pb in arm.pose.bones:
        pts[pb.name] = mw @ pb.head
    # landmarks attached rigidly to their bone: use bone matrices
    attach = {"head_top": "head", "chin": "jaw", "nose": "head",
              "left_ear": "head", "right_ear": "head"}
    for s in sk.SIDES:
        attach.update({f"{s}_heel": f"{s}_ankle", f"{s}_toe": f"{s}_foot"})
        for f in sk.FINGERS:
            attach[f"{s}_{f}_tip"] = f"{s}_{f}3"
    for lm, bone in attach.items():
        pb = arm.pose.bones[bone]
        rest = arm.data.bones[bone].matrix_local
        pts[lm] = mw @ (pb.matrix @ rest.inverted() @ sk.REST[lm])
    return pts


def make_source(name="Source"):
    src = puppet_builder.build_puppet(name)
    rots = {
        "pelvis": Euler((0.0, 0.0, math.radians(25))),
        "spine2": Euler((math.radians(10), 0.0, math.radians(8))),
        "neck": Euler((math.radians(-10), 0.0, math.radians(15))),
        "left_shoulder": Euler((math.radians(20), math.radians(10), math.radians(-50))),
        "left_elbow": Euler((0.0, math.radians(-30), math.radians(-70))),
        "right_shoulder": Euler((math.radians(-30), 0.0, math.radians(40))),
        "right_elbow": Euler((0.0, 0.0, math.radians(60))),
        "left_hip": Euler((math.radians(-40), 0.0, math.radians(5))),
        "left_knee": Euler((math.radians(60), 0.0, 0.0)),
        "right_hip": Euler((math.radians(15), 0.0, math.radians(-8))),
        "left_wrist": Euler((math.radians(20), math.radians(15), 0.0)),
    }
    for name, e in rots.items():
        src.pose.bones[name].rotation_quaternion = e.to_quaternion()
    hand_controls.set_hand(src, "left", curl=0.8, spread=0.2, thumb_curl=0.3,
                           overrides={"index": 0.0})
    hand_controls.set_hand(src, "right", curl=0.4)
    bpy.context.view_layer.update()
    truth = landmark_positions(src)
    return src, truth
