"""Measures where the hair ends in each generated after and writes it next to the image.

The in-use step must end the hair exactly where the after ends it (test 17: a silk press grew longer in use).
fill_prompt.py reads the sidecar library/avatars/<avatar>/after/<rule>__<ref>.json to write that line.

Needs MediaPipe (server/.venv) and the face / selfie models in SCENE_QA_MODELS, as add_client_avatars.py:
    SCENE_QA_MODELS=<models dir> server/.venv/Scripts/python.exe tools/measure_after.py [after.png ...]
With no paths it measures every after in library/avatars/*/after/.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_client_avatars import mediapipe_tools  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sidecar(path):
    return os.path.splitext(path)[0] + ".json"


def main(paths):
    paths = paths or sorted(glob.glob(os.path.join(ROOT, "library", "avatars", "*", "after", "*.png")))
    run = mediapipe_tools()
    for p in paths:
        m = run(p)
        if not m:
            print(p, "no face or hair found")
            continue
        m["measured_by"] = "tools/measure_after.py (MediaPipe face mesh + hair mask, head heights from the top of the head)"
        json.dump(m, open(sidecar(p), "w", encoding="utf-8"), indent=1)
        print(os.path.relpath(p, ROOT), m["hair_end"], m["hair_landmark"], "cropped" if m["hair_cropped"] else "")


if __name__ == "__main__":
    main(sys.argv[1:])
