"""Lite backend test: render a posed puppet, run MediaPipe on the render,
apply the estimate to a fresh puppet and compare.

Run:  blender -b --factory-startup --python tests/test_lite_render.py -- <site-packages-dir>
(the optional dir is where mediapipe is installed; otherwise the add-on's
own user dir is used).
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if argv and not argv[0].startswith("--"):
    sys.path.append(argv[0])

import puppet_pose  # noqa: E402
from puppet_pose import deps, pose_apply, puppet_builder  # noqa: E402
from puppet_pose import skeleton as sk  # noqa: E402
from puppet_pose.backends import mediapipe_lite  # noqa: E402
from _common import landmark_positions, make_source  # noqa: E402

puppet_pose.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
OUT = os.path.join(ROOT, "tests", "_out")
os.makedirs(OUT, exist_ok=True)

scene = bpy.context.scene
src, truth = make_source()

# ground + light + world
bpy.ops.mesh.primitive_plane_add(size=20)
light = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
light.data.energy = 4.0
light.rotation_euler = (math.radians(40), 0, math.radians(30))
scene.collection.objects.link(light)
world = bpy.data.worlds.new("W")
world.color = (0.55, 0.6, 0.65)
scene.world = world

# camera
W, H, f = 1200, 1600, 1500.0
cam = bpy.data.objects.new("SrcCam", bpy.data.cameras.new("SrcCam"))
scene.collection.objects.link(cam)
cam.location = (1.0, -3.4, 1.4)
cam.rotation_euler = (Vector((0, 0, 0.95)) - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.sensor_fit = "AUTO"
cam.data.sensor_width = 36
cam.data.lens = f * 36 / max(W, H)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
    try:
        scene.render.engine = engine
        break
    except TypeError:
        continue
photo = os.path.join(OUT, "lite_input.png")
scene.render.filepath = photo
bpy.ops.render.render(write_still=True)
print("rendered", photo, scene.render.engine)

JSON = next((a.split("=", 1)[1] for a in argv if a.startswith("--json=")), None)
NOGRAV = "--no-gravity" in argv
if JSON:  # result produced by the pose server (e.g. NLF / SAM 3D Body)
    import json
    with open(JSON, encoding="utf-8") as fh:
        res = json.load(fh)
    if NOGRAV:
        res.pop("up_cam", None)
else:  # run MediaPipe
    models = deps.ensure_models()
    res = mediapipe_lite.run(photo, models, focal_35mm=0.0,
                             default_35mm=f / math.hypot(W, H) * math.hypot(36, 24))
print("notes:", res["notes"], "points:", len(res["points3d"]))

dst = puppet_builder.build_puppet("Lite")
dst.location.x = 2.5
FLIP = "--flip" in argv
pose_apply.apply_result(bpy.context, dst, res, frame_mode="AUTO", ground=True, flip_facing=FLIP)
bpy.context.view_layer.update()
got = landmark_positions(dst)

# compare bone directions in each puppet's own body frame (pelvis-relative)
def rel_dirs(pts, arm):
    inv = arm.pose.bones["pelvis"].matrix.to_3x3().inverted()
    out = {}
    for b in sk.SMPLX_JOINTS:
        t = sk.TAIL.get(b)
        if t and t in pts:
            out[b] = (inv @ (pts[t] - pts[b])).normalized()
    return out

a, b = rel_dirs(truth, src), rel_dirs(got, dst)
groups = {"body": [], "hands": []}
for k in a:
    err = math.degrees(a[k].angle(b[k], 0.0))
    groups["hands" if any(f"_{f}" in k for f in sk.FINGERS) else "body"].append((err, k))
for g, errs in groups.items():
    errs.sort(reverse=True)
    if errs:
        print(f"{g}: mean {sum(e for e, _ in errs)/len(errs):.1f} deg, worst {[(round(e), n) for e, n in errs[:4]]}")

lite_cam = bpy.data.objects["Lite_Cam"]
print(f"lite camera lens {lite_cam.data.lens:.1f}mm  src {cam.data.lens:.1f}mm")
# camera relative to puppet: distance + elevation angle
def cam_rel(cam_obj, arm):
    hip = arm.matrix_world @ arm.pose.bones["pelvis"].head
    v = cam_obj.matrix_world.translation - hip
    return v.length, math.degrees(math.asin(v.z / v.length))
print("src cam dist/elev: %.2f m / %.1f deg" % cam_rel(cam, src))
print("lite cam dist/elev: %.2f m / %.1f deg" % cam_rel(lite_cam, dst))

# render the reconstruction from its own camera for visual comparison
src.hide_render = True
for c in src.children:
    c.hide_render = True
scene.camera = lite_cam
lite_cam.data.show_background_images = False
scene.render.filepath = os.path.join(OUT, "lite_reconstruction.png")
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lite_test.blend"))
print("DONE")
