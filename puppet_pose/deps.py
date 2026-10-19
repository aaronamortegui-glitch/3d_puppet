# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional dependency management for the 'lite' backend.

MediaPipe is installed with pip into the extension's *user* directory
(not into Blender's own site-packages, which may be read-only), and that
directory is appended to sys.path.  numpy is pinned to Blender's major
version so Blender's bundled numpy keeps working.
"""

import os
import subprocess
import sys
import urllib.request

import bpy

PACKAGES = ["mediapipe"]

MODEL_URLS = {
    "pose_landmarker_heavy.task":
        "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
        "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task",
    "hand_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/latest/hand_landmarker.task",
}


def _user_dir(sub):
    try:
        return bpy.utils.extension_path_user(__package__, path=sub, create=True)
    except Exception:  # legacy add-on install (no extension repo)
        base = os.path.join(bpy.utils.user_resource("SCRIPTS"), "puppet_pose_data", sub)
        os.makedirs(base, exist_ok=True)
        return base


def site_dir():
    return _user_dir("site-packages")


def models_dir():
    return _user_dir("models")


def ensure_path():
    d = site_dir()
    if d not in sys.path:
        sys.path.append(d)  # appended: Blender's own numpy wins


def mediapipe_available():
    ensure_path()
    try:
        import mediapipe  # noqa: F401
        return True
    except Exception:
        return False


def install_packages(log=print):
    import numpy
    np_major = numpy.__version__.split(".")[0]
    cmd = [sys.executable, "-m", "ensurepip", "--upgrade"]
    subprocess.run(cmd, capture_output=True)
    cmd = [sys.executable, "-m", "pip", "install", "--no-user", "--upgrade",
           "--target", site_dir(), *PACKAGES, f"numpy=={numpy.__version__}"
           if np_major == "1" else f"numpy<{int(np_major) + 1}"]
    log("Running: " + " ".join(cmd))
    env = dict(os.environ, PYTHONNOUSERSITE="1")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    log(proc.stdout[-2000:])
    if proc.returncode != 0:
        log(proc.stderr[-4000:])
        raise RuntimeError("pip install failed (see console)")
    ensure_path()


def ensure_models(log=print):
    d = models_dir()
    paths = {}
    for name, url in MODEL_URLS.items():
        p = os.path.join(d, name)
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            log(f"Downloading {name} ...")
            urllib.request.urlretrieve(url, p)
        paths[name] = p
    return paths


def models_present():
    d = models_dir()
    return all(os.path.exists(os.path.join(d, n)) for n in MODEL_URLS)
