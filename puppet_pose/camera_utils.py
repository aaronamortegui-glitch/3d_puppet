# SPDX-License-Identifier: GPL-3.0-or-later
"""Camera helpers: OpenCV <-> Blender conventions and camera creation.

Conventions
-----------
OpenCV camera:  x right, y down, z forward (into the scene).
"Camera world" (W_c, used internally): the camera sits at the origin
looking along +Y with +Z up, i.e. a Blender-friendly frame:
    W_c = (x_cv, z_cv, -y_cv)
Blender camera object: looks along its local -Z with local +Y up, so a
camera looking along +Y has rotation Euler((90 deg, 0, 0)).
"""

import math
import os

import bpy
from mathutils import Matrix, Vector

CV_TO_WC = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
CAM_IN_WC = Matrix.Rotation(math.radians(90.0), 3, "X")  # Blender cam -> W_c


def cv_to_wc(p):
    return CV_TO_WC @ Vector(p)


def focal_px_from_35mm(f35, width, height):
    """35mm-equivalent focal (diagonal-based) to focal length in pixels."""
    diag_px = math.hypot(width, height)
    return f35 / math.hypot(36.0, 24.0) * diag_px


def focal_px_from_fov(fov_deg, size_px):
    return 0.5 * size_px / math.tan(math.radians(fov_deg) * 0.5)


def solve_translation(points_local, pixels, f, cx, cy, weights=None):
    """Least-squares translation t so that project(X + t) ~= pixels.

    points_local: list of (x, y, z) in OpenCV camera axes (any origin).
    pixels: list of (u, v).  Linear in t:
        f*(X+tx) - (u-cx)*(Z+tz) = 0
        f*(Y+ty) - (v-cy)*(Z+tz) = 0
    Solved with 3x3 normal equations (no numpy required).
    """
    A = [[0.0] * 3 for _ in range(3)]
    b = [0.0] * 3
    for i, ((X, Y, Z), (u, v)) in enumerate(zip(points_local, pixels)):
        w = 1.0 if weights is None else weights[i]
        du, dv = u - cx, v - cy
        rows = (((f, 0.0, -du), du * Z - f * X), ((0.0, f, -dv), dv * Z - f * Y))
        for a, rhs in rows:
            for r in range(3):
                b[r] += w * a[r] * rhs
                for c in range(3):
                    A[r][c] += w * a[r] * a[c]
    t = Matrix(A).inverted_safe() @ Vector(b)
    if t.z < 0.1:  # person must be in front of the camera
        t.z = max(t.z, 0.1)
    return t


def ensure_camera(name="PuppetCam"):
    cam = bpy.data.objects.get(name)
    if cam is None or cam.type != "CAMERA":
        data = bpy.data.cameras.new(name)
        cam = bpy.data.objects.new(name, data)
        bpy.context.scene.collection.objects.link(cam)
    return cam


def setup_camera(cam, matrix_world, f_px, width, height, cx=None, cy=None,
                 image_path=None, sensor_width=36.0, set_active=True,
                 bg_alpha=0.6):
    scene = bpy.context.scene
    data = cam.data
    data.type = "PERSP"
    data.sensor_fit = "AUTO"            # sensor spans the larger image side
    data.sensor_width = sensor_width
    longest = max(width, height)
    data.lens = f_px * sensor_width / longest
    if cx is not None and cy is not None:
        data.shift_x = (width * 0.5 - cx) / longest
        data.shift_y = (cy - height * 0.5) / longest
    else:
        data.shift_x = data.shift_y = 0.0
    data.clip_start = 0.01
    data.clip_end = 500.0
    cam.matrix_world = matrix_world

    scene.render.resolution_x = int(width)
    scene.render.resolution_y = int(height)
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.0
    if set_active:
        scene.camera = cam

    if image_path and os.path.exists(image_path):
        img = bpy.data.images.load(image_path, check_existing=True)
        data.show_background_images = True
        bg = data.background_images[0] if len(data.background_images) else \
            data.background_images.new()
        bg.image = img
        bg.alpha = bg_alpha
        bg.display_depth = "BACK"
        bg.frame_method = "FIT"
    return cam


def camera_world_matrix(rot_wc_to_world, cam_location):
    """Blender camera matrix for a camera that sits at W_c origin."""
    rot = rot_wc_to_world @ CAM_IN_WC
    m = rot.to_4x4()
    m.translation = cam_location
    return m
