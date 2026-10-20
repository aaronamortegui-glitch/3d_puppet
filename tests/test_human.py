"""Human figure (MHR mesh + Rigify rig) build and pose-sync test.

    blender -b --factory-startup --python tests/test_human.py [-- <out_dir>]

Builds the human, poses the driver armature (arms, elbows, a fist), syncs the
Rigify FK controls and checks every DEF bone follows its driver bone.
Renders a front view when an output folder is given.
"""

import math
import os
import sys

import bpy
from mathutils import Euler, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import puppet_pose  # noqa: E402
from puppet_pose import hand_controls, human_builder  # noqa: E402

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else None
puppet_pose.register()
bpy.ops.wm.read_factory_settings(use_empty=True)
ctx = bpy.context

drv = human_builder.build_human("Human")
rig = human_builder.rig_of(drv)
print("rig bones", len(rig.data.bones), "controls",
      len([b for b in rig.pose.bones if not b.name.startswith(("DEF-", "ORG-", "MCH-"))]))

pb = drv.pose.bones
for n, e in (("left_shoulder", (0, 0.5, 0.6)), ("left_elbow", (0, -1.2, 0)),
             ("right_shoulder", (0.6, 0, -0.3)), ("right_elbow", (0, 0.4, -0.9)),
             ("left_hip", (-0.5, 0, 0)), ("left_knee", (0.9, 0, 0)), ("head", (0.2, 0, 0.3))):
    pb[n].rotation_mode = "QUATERNION"
    pb[n].rotation_quaternion = Euler(e).to_quaternion()
hand_controls.apply_preset(drv, "right", "FIST")
hand_controls.apply_preset(drv, "left", "POINT")
ctx.view_layer.update()
err = human_builder.sync_rig(drv)
print(f"max DEF position error after sync: {err * 1000:.2f} mm")

if OUT:
    os.makedirs(OUT, exist_ok=True)
    sc = ctx.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"; sh.color_type = "MATERIAL"; sh.show_cavity = True
    sc.world = bpy.data.worlds.new("W"); sc.world.color = (0.95, 0.95, 0.96)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam); sc.camera = cam
    rig.hide_set(True); rig.hide_render = True
    for nm, frm, at, lens, res in (("human_front.png", (0.9, -3.4, 1.0), (0, 0, 0.85), 50, (800, 1000)),
                                   ("human_hand.png", None, None, 70, (700, 700))):
        if frm is None:
            c = drv.matrix_world @ pb["right_wrist"].head
            frm, at = c + Vector((-0.1, -0.45, 0.1)), c
        cam.location = frm
        cam.rotation_euler = (Vector(at) - Vector(frm)).to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        sc.render.resolution_x, sc.render.resolution_y = res
        sc.render.filepath = os.path.join(OUT, nm)
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "human.blend"))

ok = err is not None and err < 0.005
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
