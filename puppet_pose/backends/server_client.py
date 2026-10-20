# SPDX-License-Identifier: GPL-3.0-or-later
"""'Pro' backend client: talks to the local pose server (see /server).

The server runs heavy PyTorch models (body + hands + camera) in its own
Python environment on the GPU and returns the common result schema.
Only the standard library is used here.
"""

import json
import urllib.error
import urllib.request


def _url(host, port, path):
    return f"http://{host}:{port}{path}"


def health(host="127.0.0.1", port=8765, timeout=2.0):
    try:
        with urllib.request.urlopen(_url(host, port, "/health"), timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None


def refit(result, keypoints2d, host="127.0.0.1", port=8765, replace=False, timeout=300.0):
    """Re-fit a previous result with edited 2D keypoints {name: [u, v(, c)]}."""
    body = json.dumps({"result": result, "keypoints2d": keypoints2d,
                       "replace": replace}).encode("utf-8")
    req = urllib.request.Request(_url(host, port, "/refit"), data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"Pose server not reachable at {host}:{port} ({e}). "
                           "Re-fitting needs the Pro server (server/run_server.bat)")
    if "error" in res:
        raise RuntimeError(res["error"])
    return res


def run(image_path, host="127.0.0.1", port=8765, focal_35mm=0.0,
        method="auto", timeout=600.0, profile=None, camera_pose=None):
    req = {"image_path": image_path, "focal_35mm": focal_35mm, "method": method}
    if profile:
        req["profile"] = profile
    if camera_pose:
        req["camera_pose"] = camera_pose
    body = json.dumps(req).encode("utf-8")
    req = urllib.request.Request(_url(host, port, "/estimate"), data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Pose server error {e.code}: {e.read().decode('utf-8', 'ignore')[:500]}")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"Pose server not reachable at {host}:{port} ({e}). "
                           "Start it with server/run_server.bat")
    if "error" in res:
        raise RuntimeError(res["error"])
    return res
