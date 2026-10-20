# SPDX-License-Identifier: GPL-3.0-or-later
"""OpenPose JSON <-> puppet keypoint names.

Supports BODY_25 and COCO-18 body layouts plus 21-point hands, as written
by OpenPose, ControlNet / ComfyUI OpenPose editors and similar tools.
Coordinates may be in pixels or normalised (0..1, then scaled by the
image size).
"""

import json

BODY25 = ["nose", "neck", "right_shoulder", "right_elbow", "right_wrist",
          "left_shoulder", "left_elbow", "left_wrist", "mid_hip", "right_hip",
          "right_knee", "right_ankle", "left_hip", "left_knee", "left_ankle",
          "right_eye_smplhf", "left_eye_smplhf", "right_ear", "left_ear",
          "left_toe", "left_small_toe", "left_heel", "right_toe",
          "right_small_toe", "right_heel"]
COCO18 = ["nose", "neck", "right_shoulder", "right_elbow", "right_wrist",
          "left_shoulder", "left_elbow", "left_wrist", "right_hip", "right_knee",
          "right_ankle", "left_hip", "left_knee", "left_ankle",
          "right_eye_smplhf", "left_eye_smplhf", "right_ear", "left_ear"]
HAND21 = ["wrist", "thumb1", "thumb2", "thumb3", "thumb_tip",
          "index1", "index2", "index3", "index_tip",
          "middle1", "middle2", "middle3", "middle_tip",
          "ring1", "ring2", "ring3", "ring_tip",
          "pinky1", "pinky2", "pinky3", "pinky_tip"]
# OpenPose "neck"/"mid_hip" are not puppet points; they are skipped on import
_SKIP = {"neck", "mid_hip", "left_small_toe", "right_small_toe"}


def _triplets(flat):
    return [flat[i:i + 3] for i in range(0, len(flat) - 2, 3)]


def load(path, width, height, person=0):
    """-> {name: [u, v, conf]} in pixels."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):  # some editors save a list of frames
        data = data[0]
    people = data.get("people", [])
    if not people:
        raise ValueError("No people in OpenPose JSON")
    p = people[min(person, len(people) - 1)]
    W = data.get("canvas_width", width)
    H = data.get("canvas_height", height)
    out = {}

    def put(name, x, y, c):
        if c <= 0 or name in _SKIP:
            return
        out[name] = [x, y, min(float(c), 1.0)]

    body = _triplets(p.get("pose_keypoints_2d", []))
    layout = BODY25 if len(body) >= 25 else COCO18
    for name, (x, y, c) in zip(layout, body):
        put(name, x, y, c)
    for side, key in (("left", "hand_left_keypoints_2d"), ("right", "hand_right_keypoints_2d")):
        for name, (x, y, c) in zip(HAND21, _triplets(p.get(key, []))):
            if name == "wrist":
                continue  # the body wrist is used
            put(f"{side}_{name}", x, y, c)
    # normalised coordinates?
    if out and max(max(v[0], v[1]) for v in out.values()) <= 1.5:
        for v in out.values():
            v[0] *= W
            v[1] *= H
    # rescale if the editor canvas differs from the photo
    if (W, H) != (width, height) and W and H:
        for v in out.values():
            v[0] *= width / W
            v[1] *= height / H
    return out


def save(path, kp, width, height):
    """kp: {name: [u, v(, conf)]} -> OpenPose BODY_25 + hands JSON."""
    def get(n):
        v = kp.get(n)
        return [float(v[0]), float(v[1]), float(v[2]) if len(v) > 2 else 1.0] if v else [0, 0, 0]

    body = []
    for n in BODY25:
        if n == "neck" and "left_shoulder" in kp and "right_shoulder" in kp:
            a, b = kp["left_shoulder"], kp["right_shoulder"]
            body += [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.0]
        elif n == "mid_hip" and "left_hip" in kp and "right_hip" in kp:
            a, b = kp["left_hip"], kp["right_hip"]
            body += [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 1.0]
        else:
            body += get(n)
    hands = {}
    for side in ("left", "right"):
        flat = []
        for n in HAND21:
            flat += get(f"{side}_wrist" if n == "wrist" else f"{side}_{n}")
        hands[side] = flat
    data = {"version": 1.3, "canvas_width": width, "canvas_height": height,
            "people": [{"pose_keypoints_2d": body,
                        "hand_left_keypoints_2d": hands["left"],
                        "hand_right_keypoints_2d": hands["right"]}]}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
