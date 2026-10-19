"""MediaPipe on the server (same code as the add-on's lite backend)."""

import importlib.util
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODELS = os.path.join(ROOT, "server", "models", "mediapipe")
URLS = {
    "pose_landmarker_heavy.task":
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
    "hand_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task",
}


def _lite_module():
    path = os.path.join(ROOT, "puppet_pose", "backends", "mediapipe_lite.py")
    spec = importlib.util.spec_from_file_location("mediapipe_lite", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def available():
    try:
        import mediapipe  # noqa: F401
        return True
    except Exception:
        return False


def run(image_path, focal_px=None, focal_note="", **_):
    os.makedirs(MODELS, exist_ok=True)
    models = {}
    for name, url in URLS.items():
        p = os.path.join(MODELS, name)
        if not os.path.exists(p):
            urllib.request.urlretrieve(url, p)
        models[name] = p
    lite = _lite_module()
    rgb, _, _ = lite.load_image(image_path)
    h, w = rgb.shape[:2]
    f35 = 0.0
    if focal_px:
        f35 = focal_px / ((w * w + h * h) ** 0.5) * 43.2666
    res = lite.run(image_path, models, focal_35mm=f35)
    res["backend"] = "server/mediapipe"
    if focal_note:
        res["notes"].append("focal source: " + focal_note)
    return res
