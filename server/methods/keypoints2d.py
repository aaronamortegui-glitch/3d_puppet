"""High-precision 2D whole-body keypoints: RTMW (COCO-WholeBody, 133 points)
through rtmlib (Apache-2.0, ONNX Runtime, no mmcv).
https://github.com/Tau-J/rtmlib
"""

import numpy as np

_model = None

BODY = {0: "nose", 1: "left_eye_smplhf", 2: "right_eye_smplhf", 3: "left_ear", 4: "right_ear", 5: "left_shoulder",
        6: "right_shoulder", 7: "left_elbow", 8: "right_elbow", 9: "left_wrist",
        10: "right_wrist", 11: "left_hip", 12: "right_hip", 13: "left_knee",
        14: "right_knee", 15: "left_ankle", 16: "right_ankle", 17: "left_toe",
        19: "left_heel", 20: "right_toe", 22: "right_heel"}
_HAND = ["wrist", "thumb1", "thumb2", "thumb3", "thumb_tip",
         "index1", "index2", "index3", "index_tip",
         "middle1", "middle2", "middle3", "middle_tip",
         "ring1", "ring2", "ring3", "ring_tip",
         "pinky1", "pinky2", "pinky3", "pinky_tip"]
NAMES = dict(BODY)
for _i, _n in enumerate(_HAND):
    if _n != "wrist":  # body wrist is more reliable than the hand-model wrist
        NAMES[91 + _i] = "left_" + _n
        NAMES[112 + _i] = "right_" + _n


def available():
    try:
        import rtmlib  # noqa: F401
        return True
    except Exception:
        return False


def detect(rgb, mode="performance"):
    """-> list of people, each {name: (u, v, conf)}, largest person first."""
    global _model
    import cv2
    from rtmlib import Wholebody
    if _model is None:
        try:
            _model = Wholebody(to_openpose=False, mode=mode, backend="onnxruntime",
                               device="cuda")
        except Exception:
            _model = Wholebody(to_openpose=False, mode=mode, backend="onnxruntime",
                               device="cpu")
    kps, scores = _model(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    people = []
    for k, s in zip(np.asarray(kps), np.asarray(scores)):
        # RTMW SimCC scores are not 0..1 (typically 0..~8); map to 0..1
        people.append({n: (float(k[i, 0]), float(k[i, 1]), float(min(max(s[i] / 5.0, 0.0), 1.0)))
                       for i, n in NAMES.items()})

    def size(p):
        pts = np.array([[u, v] for u, v, c in p.values() if c > 0.3])
        return np.ptp(pts[:, 1]) * np.ptp(pts[:, 0]) if len(pts) > 2 else 0
    return sorted(people, key=size, reverse=True)
