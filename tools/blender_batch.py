"""Build one .blend per pose result + an overlay preview (puppet over photo).

Standalone (no Claude needed):
    blender -b --factory-startup --python tools/blender_batch.py -- <results_dir> [--frame AUTO]

The figure is the one the result was fitted on ("figure" key: human or mannequin).

For every *.json in <results_dir> it creates:
    <stem>.blend          puppet posed + camera matching the photo (photo as background)
    <stem>_overlay.png    render of the puppet blended over the photo
"""

import glob
import json
import os
import sys

import bpy
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import puppet_pose  # noqa: E402
from puppet_pose import human_builder, pose_apply, puppet_builder  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not argv:
    raise SystemExit("usage: blender -b --python tools/blender_batch.py -- <results_dir>")
RESULTS = os.path.abspath(argv[0])
FRAME = argv[argv.index("--frame") + 1] if "--frame" in argv else "AUTO"
ALPHA = 0.7

puppet_pose.register()


def set_engine(scene):
    for engine in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            return
        except TypeError:
            continue


def overlay(render_png, photo_path, out_png):
    r = bpy.data.images.load(render_png)
    p = bpy.data.images.load(photo_path)
    if tuple(p.size) != tuple(r.size):
        p.scale(*r.size)
    w, h = r.size
    rp = np.array(r.pixels[:], dtype=np.float32).reshape(h, w, 4)
    pp = np.array(p.pixels[:], dtype=np.float32).reshape(h, w, 4)
    a = rp[..., 3:4] * ALPHA
    out = pp.copy()
    out[..., :3] = pp[..., :3] * (1 - a) + rp[..., :3] * a
    out[..., 3] = 1.0
    img = bpy.data.images.new("overlay", w, h, alpha=False)
    img.pixels[:] = out.ravel()
    img.filepath_raw = out_png
    img.file_format = "PNG"
    img.save()


files = sorted(glob.glob(os.path.join(RESULTS, "*.json")))
print(f"{len(files)} results in {RESULTS}")
for path in files:
    stem = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as fh:
        result = json.load(fh)
    if not isinstance(result, dict) or "points3d" not in result:
        continue  # not a pose result (e.g. lens_report.json)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    set_engine(scene)
    world = bpy.data.worlds.new("World")
    world.color = (0.8, 0.8, 0.8)
    scene.world = world
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 3.0
    sun.rotation_euler = (0.6, 0.2, 0.4)
    scene.collection.objects.link(sun)

    if result.get("figure") == "human" and human_builder.available():
        arm = human_builder.build_human("Human")
        bpy.ops.object.select_all(action="DESELECT")
    else:
        arm = puppet_builder.build_puppet("Puppet")
    cam = pose_apply.apply_result(bpy.context, arm, result, frame_mode=FRAME)
    bpy.context.view_layer.update()
    rig = human_builder.rig_of(arm)
    if rig is not None:
        human_builder.sync_rig(arm)
        rig.hide_render = True          # render the skinned body only
        arm.hide_render = True
        skin = bpy.data.materials.get("PuppetHumanSkin")
        if skin:                        # tint so the figure reads over gray renders and photos
            skin.diffuse_color = (0.2, 0.5, 1.0, 1.0)
            bsdf = skin.node_tree.nodes.get("Principled BSDF") if skin.node_tree else None
            if bsdf:
                bsdf.inputs["Base Color"].default_value = (0.2, 0.5, 1.0, 1.0)
    # light from the camera side so the puppet reads well in the overlay
    sun.rotation_euler = cam.matrix_world.to_euler()
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    tmp = os.path.join(RESULTS, f"_{stem}_render.png")
    scene.render.filepath = tmp
    bpy.ops.render.render(write_still=True)
    photo = result["image"]["path"]
    if os.path.exists(photo):
        overlay(tmp, photo, os.path.join(RESULTS, f"{stem}_overlay.png"))
    os.remove(tmp)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RESULTS, f"{stem}.blend"))
    c = cam.data
    print(f"OK {stem}: lens {c.lens:.1f}mm, camera {tuple(round(v, 2) for v in cam.location)}, "
          f"notes: {' | '.join(result.get('notes', []))}")
