"""Which way the woman in a photo faces (head yaw), so the after can face another way (test 20 review: the after
kept the before's direction and looked like an edited copy).

    SCENE_QA_MODELS=<dir with face.task> server/.venv/Scripts/python.exe tools/facing.py <image> [<image> ...]

Prints one JSON line per image: yaw in degrees (+ = she faces the right of the frame) and a label
(left / frontal / right). Frame directions, as a viewer sees the photo.
"""
import json
import os
import sys

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

MODELS = os.environ.get("SCENE_QA_MODELS", "")
FRONTAL = 8  # degrees: below this the head reads as frontal

_lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(MODELS, "face.task")), num_faces=1))


def facing(path):
    im = mp.Image.create_from_file(path)
    r = _lm.detect(im)
    if not r.face_landmarks:
        return {"image": path, "yaw": None, "facing": "unknown"}
    p = r.face_landmarks[0]
    # nose tip against the two cheek contours: the nose moves toward the side the face turns to
    nose, left, right = p[1].x, p[234].x, p[454].x
    t = (nose - left) / max(right - left, 1e-6)  # 0.5 = frontal
    yaw = float(np.degrees(np.arcsin(np.clip((t - 0.5) * 2, -1, 1))))
    label = "frontal" if abs(yaw) < FRONTAL else ("right" if yaw > 0 else "left")
    return {"image": path, "yaw": round(yaw, 1), "facing": label}


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(json.dumps(facing(a)))
