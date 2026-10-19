# SPDX-License-Identifier: GPL-3.0-or-later
"""Puppet skeleton definition.

Joint names and hierarchy follow SMPL-X (55 joints) so results from
SMPL-X based estimators map 1:1.  Rest pose is a T-pose in Blender
armature space: +X = subject's left, -Y = front, +Z = up, meters,
feet on the ground.

Besides joints we define extra *landmarks* (nose, ears, heels, finger
tips...).  They are not bones, but they exist both in the rest pose and
in every pose-estimator result, which lets the retargeter compare rest
and target vectors with the same names.
"""

from mathutils import Vector

SIDES = ("left", "right")
FINGERS = ("thumb", "index", "middle", "ring", "pinky")

# SMPL-X joint order (first 55 joints) -> parent index.
SMPLX_JOINTS = [
    "pelvis", "left_hip", "right_hip", "spine1", "left_knee", "right_knee",
    "spine2", "left_ankle", "right_ankle", "spine3", "left_foot", "right_foot",
    "neck", "left_collar", "right_collar", "head", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist",
    "jaw", "left_eye_smplhf", "right_eye_smplhf",
]
for _side in SIDES:
    for _f in ("index", "middle", "pinky", "ring", "thumb"):
        for _i in (1, 2, 3):
            SMPLX_JOINTS.append(f"{_side}_{_f}{_i}")

SMPLX_PARENTS = [
    -1, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 9, 9, 12, 13, 14, 16, 17, 18, 19,
    15, 15, 15,
    20, 25, 26, 20, 28, 29, 20, 31, 32, 20, 34, 35, 20, 37, 38,
    21, 40, 41, 21, 43, 44, 21, 46, 47, 21, 49, 50, 21, 52, 53,
]

PARENT = {
    name: (SMPLX_JOINTS[p] if p >= 0 else None)
    for name, p in zip(SMPLX_JOINTS, SMPLX_PARENTS)
}

# ---------------------------------------------------------------------------
# Rest positions (left side; right side is mirrored on X)
# ---------------------------------------------------------------------------
_CENTER = {
    "pelvis": (0.0, 0.0, 0.93),
    "spine1": (0.0, 0.005, 1.03),
    "spine2": (0.0, 0.0, 1.15),
    "spine3": (0.0, -0.005, 1.27),
    "neck": (0.0, 0.01, 1.45),
    "head": (0.0, -0.005, 1.53),
    "jaw": (0.0, -0.03, 1.555),
    # landmarks
    "head_top": (0.0, 0.0, 1.73),
    "chin": (0.0, -0.085, 1.50),
    "nose": (0.0, -0.108, 1.59),
}

_LEFT = {
    "left_hip": (0.085, 0.0, 0.86),
    "left_knee": (0.095, -0.005, 0.48),
    "left_ankle": (0.095, 0.025, 0.08),
    "left_foot": (0.10, -0.09, 0.02),
    "left_collar": (0.04, 0.0, 1.40),
    "left_shoulder": (0.18, 0.01, 1.41),
    "left_elbow": (0.44, 0.02, 1.41),
    "left_wrist": (0.69, 0.0, 1.41),
    "left_eye_smplhf": (0.032, -0.085, 1.62),
    # landmarks
    "left_heel": (0.095, 0.05, 0.02),
    "left_toe": (0.105, -0.155, 0.02),
    "left_ear": (0.075, 0.0, 1.60),
    # thumb (palm faces down, thumb points to the front)
    "left_thumb1": (0.715, -0.03, 1.395),
    "left_thumb2": (0.745, -0.06, 1.39),
    "left_thumb3": (0.772, -0.078, 1.39),
    "left_thumb_tip": (0.795, -0.092, 1.39),
}

# finger base (MCP) and phalanx lengths
_FINGER_BASE = {
    "index": ((0.785, -0.030, 1.405), (0.040, 0.025, 0.022)),
    "middle": ((0.790, -0.008, 1.405), (0.045, 0.028, 0.024)),
    "ring": ((0.783, 0.013, 1.405), (0.042, 0.027, 0.022)),
    "pinky": ((0.772, 0.032, 1.405), (0.032, 0.021, 0.019)),
}
for _f, (_base, _lens) in _FINGER_BASE.items():
    _x, _y, _z = _base
    _LEFT[f"left_{_f}1"] = (_x, _y, _z)
    for _i, _name in enumerate((f"left_{_f}2", f"left_{_f}3", f"left_{_f}_tip")):
        _x += _lens[_i]
        _LEFT[_name] = (_x, _y, _z)


def _build_rest():
    rest = {k: Vector(v) for k, v in _CENTER.items()}
    for k, v in _LEFT.items():
        rest[k] = Vector(v)
        rest["right" + k[4:]] = Vector((-v[0], v[1], v[2]))
    return rest


REST = _build_rest()

# Bone tail = position of this landmark/joint.
TAIL = {
    "pelvis": "spine1", "spine1": "spine2", "spine2": "spine3",
    "spine3": "neck", "neck": "head", "head": "head_top", "jaw": "chin",
}
for _s in SIDES:
    TAIL.update({
        f"{_s}_hip": f"{_s}_knee", f"{_s}_knee": f"{_s}_ankle",
        f"{_s}_ankle": f"{_s}_foot", f"{_s}_foot": f"{_s}_toe",
        f"{_s}_collar": f"{_s}_shoulder", f"{_s}_shoulder": f"{_s}_elbow",
        f"{_s}_elbow": f"{_s}_wrist", f"{_s}_wrist": f"{_s}_middle1",
    })
    for _f in FINGERS:
        TAIL[f"{_s}_{_f}1"] = f"{_s}_{_f}2"
        TAIL[f"{_s}_{_f}2"] = f"{_s}_{_f}3"
        TAIL[f"{_s}_{_f}3"] = f"{_s}_{_f}_tip"


def bone_tail(name):
    """Rest tail position for a bone."""
    if name in TAIL:
        return REST[TAIL[name]]
    if name.endswith("_eye_smplhf"):
        return REST[name] + Vector((0.0, -0.02, 0.0))
    raise KeyError(name)


def finger_bones(side, finger):
    return [f"{side}_{finger}{i}" for i in (1, 2, 3)]


def all_finger_bones(side):
    return [b for f in FINGERS for b in finger_bones(side, f)]
