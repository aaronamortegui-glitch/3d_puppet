"""Round-trip test: known pose + known camera -> synthetic result -> apply.

Run:  blender -b --factory-startup --python tests/test_roundtrip.py
Exit code != 0 on failure.
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
from puppet_pose import pose_apply, puppet_builder  # noqa: E402
from puppet_pose import skeleton as sk  # noqa: E402
from _common import landmark_positions, make_source  # noqa: E402

puppet_pose.register()
bpy.ops.wm.read_factory_settings(use_empty=True)

src, truth = make_source()

# ------------------------------------------------------------- known camera
W, H, f = 1600, 1200, 1500.0
cam_loc = Vector((1.2, -3.2, 1.6))
target = Vector((0.0, 0.0, 1.0))
cam_rot = (target - cam_loc).to_track_quat("-Z", "Y").to_matrix()
# world -> OpenCV camera
R_bl = cam_rot  # blender camera axes in world
R_cv = R_bl @ Matrix.Diagonal((1, -1, -1))  # opencv camera axes in world
points3d = {}
for name, p in truth.items():
    pc = R_cv.transposed() @ (p - cam_loc)
    points3d[name] = list(pc)

result = {
    "backend": "synthetic",
    "image": {"path": "", "width": W, "height": H},
    "camera": {"fx": f, "fy": f, "cx": W / 2, "cy": H / 2},
    "points3d": points3d,
}

# --------------------------------------------------------------- apply (RAW)
dst = puppet_builder.build_puppet("Target")
pose_apply.apply_result(bpy.context, dst, result, frame_mode="NONE",
                        ground=False, make_camera=True)
bpy.context.view_layer.update()
got = landmark_positions(dst)
cam = bpy.data.objects["Target_Cam"]

# Compare directions in camera space (pose shape independent of placement)
def to_cam(points, cam_obj):
    inv = cam_obj.matrix_world.inverted()
    return {k: inv @ v for k, v in points.items()}

tc = {k: R_bl.transposed() @ (v - cam_loc) for k, v in truth.items()}
gc = to_cam(got, cam)

errors = []
for bone in sk.SMPLX_JOINTS:
    tail = sk.TAIL.get(bone)
    if not tail or tail not in tc:
        continue
    d1 = (tc[tail] - tc[bone]).normalized()
    d2 = (gc[tail] - gc[bone]).normalized()
    errors.append((math.degrees(d1.angle(d2, 0.0)), bone))
errors.sort(reverse=True)
mean_err = sum(e for e, _ in errors) / len(errors)
print(f"bone direction error: mean {mean_err:.2f} deg, worst {errors[:5]}")

# projected 2D error of all points
def project(pc):
    return (f * pc.x / -pc.z + W / 2, -f * pc.y / -pc.z + H / 2)

px_err = [((Vector(project(tc[k])) - Vector(project(gc[k]))).length) for k in tc]
print(f"reprojection error: mean {sum(px_err)/len(px_err):.1f}px max {max(px_err):.1f}px")
print(f"camera lens {cam.data.lens:.2f}mm (expected {f*36/max(W,H):.2f})")

# UPRIGHT mode must keep camera framing identical
dst2 = puppet_builder.build_puppet("Target2")
pose_apply.apply_result(bpy.context, dst2, result, frame_mode="UPRIGHT",
                        ground=True, make_camera=True)
bpy.context.view_layer.update()
gc2 = to_cam(landmark_positions(dst2), bpy.data.objects["Target2_Cam"])
px_err2 = [((Vector(project(tc[k])) - Vector(project(gc2[k]))).length) for k in tc]
print(f"UPRIGHT reprojection error: mean {sum(px_err2)/len(px_err2):.1f}px")

# AUTO mode: camera must stay roll-free and keep framing
dst3 = puppet_builder.build_puppet("Target3")
pose_apply.apply_result(bpy.context, dst3, result, frame_mode="AUTO",
                        ground=True, make_camera=True)
bpy.context.view_layer.update()
cam3 = bpy.data.objects["Target3_Cam"]
gc3 = to_cam(landmark_positions(dst3), cam3)
px_err3 = [((Vector(project(tc[k])) - Vector(project(gc3[k]))).length) for k in tc]
cam_x = cam3.matrix_world.to_3x3().col[0]
print(f"AUTO reprojection error: mean {sum(px_err3)/len(px_err3):.1f}px, camera roll {math.degrees(math.asin(cam_x.z)):.2f} deg")

out = os.path.join(ROOT, "tests", "_out")
os.makedirs(out, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, "roundtrip.blend"))

ok = mean_err < 3.0 and sum(px_err) / len(px_err) < 15 and \
    sum(px_err2) / len(px_err2) < 15 and \
    sum(px_err3) / len(px_err3) < 15 and abs(cam_x.z) < 1e-3
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
