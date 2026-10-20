"""Keypoint editor end-to-end test (needs the pose server running).

    blender -b --factory-startup --python tests/test_keypoint_editor.py -- <result.json>

Applies a result, creates keypoint empties, moves the right wrist 60px,
re-fits through the server and checks the puppet followed.  Also round-
trips OpenPose JSON export/import.
"""

import json
import os
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import puppet_pose  # noqa: E402
from puppet_pose import keypoint_editor, openpose, pose_apply, puppet_builder  # noqa: E402
from puppet_pose.backends import server_client  # noqa: E402

puppet_pose.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
argv = sys.argv[sys.argv.index("--") + 1:]
with open(argv[0], encoding="utf-8") as fh:
    result = json.load(fh)

ctx = bpy.context
arm = puppet_builder.build_puppet("Puppet")
cam = pose_apply.apply_result(ctx, arm, result)
arm["puppet_last_result"] = json.dumps(result)
n = keypoint_editor.create(ctx, arm, cam, result)
print("keypoints:", n)
W, H = ctx.scene.render.resolution_x, ctx.scene.render.resolution_y


def px(p):
    co = world_to_camera_view(ctx.scene, cam, p)
    return Vector((co.x * W, (1 - co.y) * H))


side = "right" if "right_wrist" in result.get("points2d", {}) else "left"
e = bpy.data.objects["KP_%s_wrist" % side]
before = px(pose_apply.posed_points(arm)[f"{side}_wrist"])
target = Vector((e["u0"] + 60.0, e["v0"] - 40.0))
# move the empty so it projects onto `target` (same depth)
depth = -(cam.matrix_world.inverted() @ e.location).z
e.location = keypoint_editor._pixel_to_world(cam, result["camera"], target.x, target.y, depth)
edits = keypoint_editor.read(ctx, cam)
print("edits:", {k: [round(x, 1) for x in v] for k, v in edits.items()})
new = server_client.refit(result, edits)
pose_apply.apply_result(ctx, arm, new)
ctx.view_layer.update()
cam = bpy.data.objects[arm.name + "_Cam"]
after = px(pose_apply.posed_points(arm)[f"{side}_wrist"])
print(f"wrist before {tuple(round(v) for v in before)} -> after {tuple(round(v) for v in after)}"
      f" target {tuple(round(v) for v in target)}  err {(after - target).length:.1f}px")
print("fit:", new.get("fit"))

# OpenPose round trip
op = os.path.join(ROOT, "tests", "_out", "kp_openpose.json")
img = result["image"]
openpose.save(op, keypoint_editor.current(ctx, cam, result), img["width"], img["height"])
back = openpose.load(op, img["width"], img["height"])
diff = max(abs(back[k][0] - v[0]) + abs(back[k][1] - v[1])
           for k, v in keypoint_editor.current(ctx, cam, result).items() if k in back)
print("openpose round-trip points:", len(back), "max diff px:", round(diff, 3))
ok = (after - target).length < 15 and diff < 0.01
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
