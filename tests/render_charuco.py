"""Render a ChArUco board with a KNOWN camera (synthetic calibration ground truth).

    blender -b --factory-startup --python tests/render_charuco.py -- <board.png> <out_dir> [views]

The board lies on the floor (z = 0) with the image top towards +Y.
Writes calib_XX.png (random views), plate.png (one fixed camera) and
truth.json (intrinsics in pixels, plate camera pose, board origin).
"""

import json
import math
import os
import random
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
BOARD_PNG, OUT = os.path.abspath(argv[0]), os.path.abspath(argv[1])
N = int(argv[2]) if len(argv) > 2 else 24
os.makedirs(OUT, exist_ok=True)
spec = json.load(open(os.path.splitext(BOARD_PNG)[0] + ".json"))

W, H, LENS, SENSOR = 1600, 1200, 50.0, 36.0
MARGIN = 0.01
bw = spec["squares_x"] * spec["square_m"] + 2 * MARGIN
bh = spec["squares_y"] * spec["square_m"] + 2 * MARGIN

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = 100
sc.world = bpy.data.worlds.new("W")
sc.world.color = (0.75, 0.75, 0.75)

# board plane with emissive texture (no lighting dependence)
bpy.ops.mesh.primitive_plane_add(size=1)
plane = bpy.context.object
plane.scale = (bw, bh, 1)
mat = bpy.data.materials.new("Board")
mat.use_nodes = True
nt = mat.node_tree
for n in list(nt.nodes):
    nt.nodes.remove(n)
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = bpy.data.images.load(BOARD_PNG)
tex.interpolation = "Cubic"
em = nt.nodes.new("ShaderNodeEmission")
out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tex.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
plane.data.materials.append(mat)

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam)
cam.data.lens, cam.data.sensor_width, cam.data.sensor_fit = LENS, SENSOR, "HORIZONTAL"
sc.camera = cam


def look(loc, target, roll_deg=0.0):
    cam.location = loc
    q = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y")
    cam.rotation_euler = (q.to_matrix() @ Matrix.Rotation(math.radians(roll_deg), 3, "Z")).to_euler()


def render(path):
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


random.seed(7)
for i in range(N):
    az = random.uniform(0, 360)
    el = random.uniform(40, 85)
    d = random.uniform(0.45, 0.8)
    loc = (d * math.cos(math.radians(el)) * math.cos(math.radians(az)),
           d * math.cos(math.radians(el)) * math.sin(math.radians(az)),
           d * math.sin(math.radians(el)))
    # aim off-centre (same optics, no lens shift) so the board also lands
    # near the image edges and corners, where distortion is measurable
    off = 0.06 if i < N // 3 else 0.22
    tgt = (random.uniform(-off, off), random.uniform(-off * 0.8, off * 0.8), 0)
    look(loc, tgt, random.uniform(-25, 25))
    render(os.path.join(OUT, f"calib_{i:02d}.png"))

# plate: a typical shooting position (camera 1.4 m away, 1 m high)
look((0.35, -1.3, 1.0), (0.0, 0.0, 0.0), 0.0)
bpy.context.view_layer.update()
render(os.path.join(OUT, "plate.png"))

fx = LENS / SENSOR * W
truth = {
    "fx": fx, "fy": fx, "cx": W / 2, "cy": H / 2, "width": W, "height": H,
    "plate_cam_matrix_world": [list(r) for r in cam.matrix_world],
    # OpenCV board origin (top-left outer chessboard corner) in Blender world
    "board_origin_world": [-bw / 2 + MARGIN, bh / 2 - MARGIN, 0.0],
}
json.dump(truth, open(os.path.join(OUT, "truth.json"), "w"), indent=1)
print("RENDERED", N, "views +plate ->", OUT)
