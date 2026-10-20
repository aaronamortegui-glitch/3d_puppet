# SPDX-License-Identifier: GPL-3.0-or-later
"""Apply a backend result (named 3D points + camera) to puppet and camera.

Result schema (produced by every backend, JSON-serialisable)::

    {
      "image": {"path": str, "width": int, "height": int},
      "camera": {"fx": float, "fy": float, "cx": float, "cy": float},
      "points3d": {name: [x, y, z]},  # OpenCV camera space, meters
      "rotations": {joint: [rx, ry, rz]},  # optional SMPL-X axis-angle
      "global_orient_cam": [rx, ry, rz],  # optional, pelvis in camera
      "up_cam": [x, y, z],  # optional world-up in camera axes (GeoCalib)
      "backend": str, "notes": [str]
    }
"""

import math

from mathutils import Matrix, Vector

from . import camera_utils as cu
from . import retarget as rt
from . import skeleton as sk


def _body_frame_rotation(pts, mode, up_override=None):
    """Rotation Q (W_c -> world) that normalises the subject.

    mode 'UPRIGHT': subject's torso becomes vertical and faces -Y; any
    lean/tilt is moved into the camera (camera gets pitch/roll).
    mode 'LEVEL': camera keeps zero roll/pitch (W_c up = world up); only
    the yaw is normalised, the lean stays in the puppet.
    mode 'NONE': camera at origin of the world looking along +Y.
    """
    if mode == "NONE":
        return Matrix.Identity(3)
    side = up = None
    if "left_hip" in pts and "right_hip" in pts:
        side = pts["left_hip"] - pts["right_hip"]
    if "left_shoulder" in pts and "right_shoulder" in pts:
        s2 = pts["left_shoulder"] - pts["right_shoulder"]
        side = s2 if side is None else (side + s2)
    if "hip_mid" in pts and "shoulder_mid" in pts:
        up = pts["shoulder_mid"] - pts["hip_mid"]
    if side is None:
        return Matrix.Identity(3)
    if mode == "AUTO" and up_override is not None and up_override.length > 1e-6:
        # true gravity from the image (GeoCalib): exact pitch AND roll
        q1 = up_override.normalized().rotation_difference(Vector((0, 0, 1))).to_matrix()
        s2 = q1 @ side
        yaw = Vector((s2.x, s2.y, 0.0)).rotation_difference(Vector((1, 0, 0))).to_matrix()
        return yaw @ q1
    if mode == "AUTO" and up is not None:
        # Photos almost never have camera roll: keep the camera X axis
        # horizontal; take pitch from the body's up vector (torso + legs).
        legs = [pts[f"{s}_hip"] - pts[f"{s}_ankle"] for s in ("left", "right")
                if f"{s}_ankle" in pts and f"{s}_hip" in pts]
        u = up.normalized()
        for leg in legs:
            if leg.length > 1e-6 and leg.normalized().dot(u) > 0.8:  # straight-ish leg
                u = u + leg.normalized() * 0.5
        pitch = math.atan2(u.y, u.z)                  # tilt toward/away from camera
        rx = Matrix.Rotation(pitch, 3, "X")
        s2 = rx @ side
        yaw = Vector((s2.x, s2.y, 0.0)).rotation_difference(Vector((1, 0, 0))).to_matrix()
        return yaw @ rx
    if mode == "UPRIGHT" and up is not None:
        rest_up, rest_side = Vector((0, 0, 1)), Vector((1, 0, 0))
        q = rt.align(rest_up, rest_side, up, side)  # rest -> target
        if q is not None:
            return q.transposed()                   # target -> rest
    # LEVEL (or fallback): yaw only around W_c +Z
    flat = Vector((side.x, side.y, 0.0))
    if flat.length < 1e-6:
        return Matrix.Identity(3)
    return flat.rotation_difference(Vector((1, 0, 0))).to_matrix()


def _chain_length(p, names):
    total = 0.0
    for a, b in zip(names, names[1:]):
        if a not in p or b not in p:
            return None
        total += (p[b] - p[a]).length
    return total


def _scale_ratio(rest, tgt):
    """Puppet size / subject size, from torso + legs (or arms)."""
    chains = [
        ["hip_mid", "shoulder_mid"],
        ["left_hip", "left_knee", "left_ankle"],
        ["right_hip", "right_knee", "right_ankle"],
        ["left_shoulder", "left_elbow", "left_wrist"],
        ["right_shoulder", "right_elbow", "right_wrist"],
    ]
    rs = ts = 0.0
    for c in chains:
        r, t = _chain_length(rest, c), _chain_length(tgt, c)
        if r and t:
            rs += r
            ts += t
    return rs / ts if ts > 1e-6 else 1.0


def _posed_point(arm, name):
    """Armature-space position of a joint head after posing."""
    return arm.pose.bones[name].head.copy()


def _lowest_z(arm):
    mw = arm.matrix_world
    zs = []
    for pb in arm.pose.bones:
        zs.append((mw @ pb.head).z)
        zs.append((mw @ pb.tail).z)
    return min(zs) if zs else 0.0


def apply_result(context, arm, result, *, frame_mode="AUTO",
                 make_camera=True, ground=True, use_rotations=False,
                 apply_body=True, apply_hands=True, bg_image=True,
                 keyframe=False, flip_facing=False, refine=True, use_rig=True):
    """Pose `arm` from `result` and create/update the matching camera."""
    pts_cv = result.get("points3d", {})
    if not pts_cv:
        raise ValueError("Backend returned no 3D points")

    if flip_facing:
        pts_cv = flip_front_back(pts_cv)
    pts_wc = {k: cu.cv_to_wc(v) for k, v in pts_cv.items()}
    pts_wc = rt.derive_points(pts_wc)
    up_cam = result.get("up_cam")
    up_wc = cu.cv_to_wc(up_cam) if up_cam else None
    Q = _body_frame_rotation(pts_wc, frame_mode, up_wc)
    pts = {k: Q @ v for k, v in pts_wc.items()}

    # --- pose -------------------------------------------------------------
    rig = result.get("rig") if use_rig else None
    if rig:
        # exact path: global bone rotations fitted on THIS skeleton (server
        # fit_rig.py) in camera-world axes; only the frame Q is applied.
        Gq = {b: Q @ Matrix(m) for b, m in rig["G"].items()}
        bones = set()
        if apply_body:
            bones |= {b for b in sk.SMPLX_JOINTS if not _is_hand_bone(b)}
        if apply_hands:
            bones |= {b for b in sk.SMPLX_JOINTS if _is_hand_bone(b)}
        rt.apply_globals(arm, Gq, bones=bones)
    elif use_rotations and result.get("rotations"):
        rt.apply_smplx_rotations(arm, result["rotations"])
        # global orientation still comes from points (camera-consistent)
        G = rt.solve(pts)
        rt.apply_globals(arm, {"pelvis": G["pelvis"]}, bones={"pelvis"})
    else:
        G = rt.solve(pts)
        bones = set()
        if apply_body:
            bones |= {b for b in sk.SMPLX_JOINTS if not _is_hand_bone(b)}
        if apply_hands:
            bones |= {b for b in sk.SMPLX_JOINTS if _is_hand_bone(b)}
        rt.apply_globals(arm, G, bones=bones)

    for pb in arm.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
    context.view_layer.update()

    # --- ground the puppet --------------------------------------------------
    offset = Vector((0, 0, 0))
    if ground:
        offset.z = -_lowest_z(arm)
        arm.location = arm.location + offset
        context.view_layer.update()

    # --- camera -------------------------------------------------------------
    cam = None
    cam_info = result.get("camera")
    if make_camera and cam_info and rig:
        # pelvis joint position is known exactly in camera-world space
        arm_rot = arm.matrix_world.to_3x3().normalized()
        pelvis_world = arm.matrix_world @ arm.pose.bones["pelvis"].head
        cam_loc = pelvis_world - arm_rot @ (Q @ Vector(rig["pelvis_wc"]))
        mw = cu.camera_world_matrix(arm_rot @ Q, cam_loc)
        img = result.get("image", {})
        cam = cu.ensure_camera(arm.name + "_Cam")
        cu.setup_camera(cam, mw, cam_info["fx"], img.get("width", 1920),
                        img.get("height", 1080), cam_info.get("cx"),
                        cam_info.get("cy"),
                        image_path=img.get("path") if bg_image else None)
    elif make_camera and cam_info and "hip_mid" in pts:
        scale = _scale_ratio(rt.REST_POINTS, pts)
        hip_posed = (_posed_point(arm, "left_hip") + _posed_point(arm, "right_hip")) * 0.5
        hip_world = arm.matrix_world @ hip_posed
        arm_rot = arm.matrix_world.to_3x3().normalized()
        # camera sits at the W_c origin; subject hip_mid is at pts["hip_mid"]
        cam_loc = hip_world - arm_rot @ (pts["hip_mid"] * scale)
        mw = cu.camera_world_matrix(arm_rot @ Q, cam_loc)
        if refine:
            mw = refine_camera(arm, mw, result, flip_facing)
        img = result.get("image", {})
        cam = cu.ensure_camera(arm.name + "_Cam")
        cu.setup_camera(cam, mw, cam_info["fx"], img.get("width", 1920),
                        img.get("height", 1080), cam_info.get("cx"),
                        cam_info.get("cy"),
                        image_path=img.get("path") if bg_image else None)

    if keyframe:
        frame = context.scene.frame_current
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=frame)
        arm.keyframe_insert("location", frame=frame)
        if cam:
            cam.keyframe_insert("location", frame=frame)
            cam.keyframe_insert("rotation_euler", frame=frame)
            cam.data.keyframe_insert("lens", frame=frame)
    return cam


def flip_front_back(pts_cv):
    """Resolve the classic front/back ambiguity: same 2D projection, but the
    subject faces the other way.  Swap left/right labels and mirror depth
    around the hip centre along the viewing ray of each point."""
    def swap(name):
        if name.startswith("left_"):
            return "right_" + name[5:]
        if name.startswith("right_"):
            return "left_" + name[6:]
        return name
    hips = [pts_cv[k] for k in ("left_hip", "right_hip") if k in pts_cv]
    if not hips:
        return pts_cv
    zc = sum(h[2] for h in hips) / len(hips)
    out = {}
    for k, (x, y, z) in pts_cv.items():
        z2 = max(2.0 * zc - z, 0.05)
        s = z2 / z if z > 1e-6 else 1.0  # keep the 2D projection unchanged
        out[swap(k)] = [x * s, y * s, z2]
    return out


def posed_points(arm):
    """World positions of every named joint/landmark of the posed puppet."""
    mw = arm.matrix_world
    pts = {pb.name: mw @ pb.head for pb in arm.pose.bones}
    attach = {"head_top": "head", "chin": "jaw", "nose": "head",
              "left_ear": "head", "right_ear": "head"}
    for s_ in sk.SIDES:
        attach.update({f"{s_}_heel": f"{s_}_ankle", f"{s_}_toe": f"{s_}_foot"})
        for f in sk.FINGERS:
            attach[f"{s_}_{f}_tip"] = f"{s_}_{f}3"
    for lm, bone in attach.items():
        pb = arm.pose.bones.get(bone)
        if pb is None:
            continue
        rest = arm.data.bones[bone].matrix_local
        pts[lm] = mw @ (pb.matrix @ rest.inverted() @ sk.REST[lm])
    return pts


def refine_camera(arm, cam_matrix, result, flip_facing=False):
    """Re-solve the camera position so the posed puppet's visible joints land
    on the photo's 2D keypoints (keeps rotation + focal).  Fixes framing when
    the puppet's proportions differ from the subject or the photo is cropped."""
    cam = result["camera"]
    img = result.get("image", {})
    W, H = img.get("width", 0), img.get("height", 0)
    f, cx, cy = cam["fx"], cam.get("cx", W / 2), cam.get("cy", H / 2)
    p3 = result.get("points3d", {})
    if flip_facing:
        p3 = flip_front_back(p3)
    uv = {}
    for k, (x, y, z) in p3.items():
        if z > 1e-3:
            uv[k] = (f * x / z + cx, f * y / z + cy)
    if not flip_facing:
        for k, v in result.get("points2d", {}).items():
            if k in uv:
                uv[k] = (v[0], v[1])
    posed = posed_points(arm)
    R_cv = cam_matrix.to_3x3().normalized() @ Matrix.Diagonal((1, -1, -1))
    names, A, P, w = [], [], [], []
    margin = 0.02 * max(W, H)
    for k, (u, v) in uv.items():
        if k not in posed or not (-margin <= u <= W + margin and -margin <= v <= H + margin):
            continue
        names.append(k)
        A.append(tuple(R_cv.transposed() @ posed[k]))
        P.append((u, v))
        w.append(0.3 if _is_hand_bone(k) or "_tip" in k else 1.0)
    if len(names) < 4:
        return cam_matrix
    t = cu.solve_translation(A, P, f, cx, cy, w)
    m = cam_matrix.copy()
    m.translation = -(R_cv @ t)
    return m


def _is_hand_bone(name):
    return any(f"_{f}" in name for f in sk.FINGERS)
