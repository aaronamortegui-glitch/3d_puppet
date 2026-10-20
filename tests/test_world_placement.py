"""Measured-camera (world_from_cv) placement test.

    blender -b --factory-startup --python tests/test_world_placement.py

A puppet is posed and placed somewhere on the floor, a camera looks at it.
We build the result a calibrated shoot would produce (rig rotations in
camera axes + the measured camera pose) and check that Blender puts the
camera and every joint back where they were - for the Pro (rig) path and
the Lite (points) path.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
import puppet_pose  # noqa: E402
from puppet_pose import camera_utils as cu  # noqa: E402
from puppet_pose import pose_apply, puppet_builder  # noqa: E402
from puppet_pose import skeleton as sk  # noqa: E402
from _common import landmark_positions, make_source  # noqa: E402

puppet_pose.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
ctx = bpy.context

# ---- ground truth ---------------------------------------------------------
src, _ = make_source()
src.location = (0.6, 0.9, 0.0)                    # stands away from the origin
src.rotation_euler = (0, 0, math.radians(30))     # and turned
ctx.view_layer.update()
truth = landmark_positions(src)
W, H, f = 1600, 1200, 2000.0
cam_loc = Vector((1.8, -2.4, 1.5))
R_bl = (Vector((0.6, 0.9, 1.0)) - cam_loc).to_track_quat("-Z", "Y").to_matrix()
R_bl = R_bl @ Matrix.Rotation(math.radians(4), 3, "Z")      # a little roll
R_cv = R_bl @ Matrix.Diagonal((1, -1, -1))                  # OpenCV cam axes in world
world_from_cv = R_cv.to_4x4()
world_from_cv.translation = cam_loc
wc_from_world = cu.CV_TO_WC @ R_cv.transposed()             # world dir -> W_c dir

points3d = {k: list(R_cv.transposed() @ (p - cam_loc)) for k, p in truth.items()}
# rig: global deltas of the source puppet (armature space -> world -> W_c)
arm_rot = src.matrix_world.to_3x3().normalized()
G = {}
for pb in src.pose.bones:
    g_arm = pb.matrix.to_3x3() @ src.data.bones[pb.name].matrix_local.to_3x3().inverted()
    # rest pose numbers are the same in every frame, so a global delta maps
    # rest -> posed and changes frame by LEFT multiplication only
    G[pb.name] = [list(r) for r in (wc_from_world @ arm_rot @ g_arm)]
pelvis_world = src.matrix_world @ src.pose.bones["pelvis"].head
rig = {"G": G, "pelvis_wc": list(wc_from_world @ (pelvis_world - cam_loc))}

base = {"backend": "synthetic", "image": {"path": "", "width": W, "height": H},
        "camera": {"fx": f, "fy": f, "cx": W / 2, "cy": H / 2},
        "points3d": points3d, "world_from_cv": [list(r) for r in world_from_cv]}

ok = True
for label, result in (("rig (Pro)", dict(base, rig=rig)), ("points (Lite)", dict(base))):
    dst = puppet_builder.build_puppet("P_" + label.split()[0])
    cam = pose_apply.apply_result(ctx, dst, result, hide_unseen=False)
    ctx.view_layer.update()
    got = landmark_positions(dst)
    errs = sorted(((got[k] - truth[k]).length * 1000, k) for k in truth if k in got)
    mean = sum(e for e, _ in errs) / len(errs)
    cam_pos_err = (cam.matrix_world.translation - cam_loc).length * 1000
    Rerr = cam.matrix_world.to_3x3().transposed() @ R_bl
    cam_ang = math.degrees(math.acos(max(-1, min(1, (Rerr[0][0] + Rerr[1][1] + Rerr[2][2] - 1) / 2))))
    print(f"{label:14s} joints: mean {mean:.1f} mm, worst {errs[-1][0]:.1f} mm ({errs[-1][1]})  "
          f"camera: {cam_pos_err:.2f} mm, {cam_ang:.4f} deg, lens {cam.data.lens:.2f}mm")
    limit = 1.0 if label.startswith("rig") else 60.0   # points path retargets (approximate)
    ok = ok and mean < limit and cam_pos_err < 0.5 and cam_ang < 0.01
    dst.hide_set(True)

print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
