# SPDX-License-Identifier: GPL-3.0-or-later
"""Simple hand controls: open/close (curl), spread and presets.

Finger bones are built with local Z pointing to the palm, so a positive
rotation around local X curls the finger and local Z spreads it.
"""

import math

from mathutils import Euler

from . import skeleton as sk

# per-joint max curl (radians) for joints 1,2,3
_CURL_MAX = (math.radians(85), math.radians(100), math.radians(70))
_THUMB_CURL_MAX = (math.radians(35), math.radians(50), math.radians(70))
_SPREAD = {"index": -1.0, "middle": 0.0, "ring": 1.0, "pinky": 2.0, "thumb": -1.5}

PRESETS = {
    # name: (curl, spread, thumb_curl, per-finger override curl)
    "OPEN": (0.0, 0.3, 0.0, {}),
    "RELAXED": (0.25, 0.1, 0.2, {}),
    "FIST": (1.0, 0.0, 1.0, {}),
    "POINT": (1.0, 0.0, 0.9, {"index": 0.0}),
    "PEACE": (1.0, 0.4, 1.0, {"index": 0.0, "middle": 0.0}),
    "THUMBS_UP": (1.0, 0.0, 0.0, {}),
    "GRIP": (0.55, 0.0, 0.45, {}),
    "PINCH": (0.15, 0.0, 0.55, {"index": 0.55}),
}


def set_hand(arm, side, curl=0.0, spread=0.0, thumb_curl=None, overrides=None):
    overrides = overrides or {}
    thumb_curl = curl if thumb_curl is None else thumb_curl
    sign = 1.0 if side == "left" else -1.0
    for f in sk.FINGERS:
        c = overrides.get(f, thumb_curl if f == "thumb" else curl)
        maxes = _THUMB_CURL_MAX if f == "thumb" else _CURL_MAX
        for i, b in enumerate(sk.finger_bones(side, f)):
            pb = arm.pose.bones.get(b)
            if pb is None:
                continue
            spread_ang = math.radians(8.0) * spread * _SPREAD[f] * sign if i == 0 else 0.0
            e = Euler((c * maxes[i], 0.0, spread_ang), "XYZ")
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = e.to_quaternion()


def apply_preset(arm, side, preset):
    curl, spread, thumb, over = PRESETS[preset]
    sides = sk.SIDES if side == "BOTH" else (side.lower(),)
    for s in sides:
        set_hand(arm, s, curl, spread, thumb, over)


# -- property update callbacks ------------------------------------------------
def update_from_props(self, context):
    arm = context.object
    if arm is None or arm.type != "ARMATURE":
        return
    p = arm.puppet_hands
    set_hand(arm, "left", p.left_curl, p.left_spread, p.left_thumb)
    set_hand(arm, "right", p.right_curl, p.right_spread, p.right_thumb)
