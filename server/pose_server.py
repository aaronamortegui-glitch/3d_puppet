"""Local pose server for the Puppet Pose add-on ('Pro' backend).

    python pose_server.py [--port 8765] [--host 127.0.0.1]
    python pose_server.py --once photo.jpg --method nlf --out result.json

Endpoints
    GET  /health    -> {"ok": true, "methods": [...], "gpu": "..."}
    POST /estimate  {"image_path", "method", "focal_35mm"} -> result schema

Models are loaded lazily on first use and kept in memory.
"""

import argparse
import json
import os
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from methods import focal, gravity, mediapipe_method, nlf_method, sam3d_method  # noqa: E402
from methods import common, fit, fit_rig, hands, keypoints2d  # noqa: E402

METHODS = {
    "sam3d_body": sam3d_method,
    "nlf": nlf_method,
    "mediapipe": mediapipe_method,
}
AUTO_ORDER = ["sam3d_body", "nlf", "mediapipe"]
_lock = threading.Lock()  # one GPU job at a time


def available_methods():
    return [k for k, m in METHODS.items() if m.available()]


def estimate(image_path, method="auto", focal_35mm=0.0, use_gravity=True, do_fit=True):
    if not os.path.isfile(image_path):
        raise FileNotFoundError(image_path)
    avail = available_methods()
    if method in ("auto", "", None) and do_fit and keypoints2d.available():
        # try every installed model, keep the one whose fitted rig best
        # matches the photo (median px error of body + hands)
        best, table = None, []
        for m in [m for m in AUTO_ORDER if m in avail]:
            try:
                r = estimate(image_path, m, focal_35mm, use_gravity, do_fit)
            except Exception as e:  # noqa: BLE001
                table.append(f"{m}: failed ({e})")
                continue
            fi = r.get("fit", {})
            score = (fi.get("rig_px_body") or 1e6) + 0.5 * (fi.get("rig_px_hands") or 0)
            table.append(f"{m}: {score:.1f}px")
            if best is None or score < best[0]:
                best = (score, r)
        if best is None:
            raise RuntimeError("no method succeeded: " + "; ".join(table))
        best[1].setdefault("notes", []).insert(0, "auto pick -> " + best[1]["backend"]
                                                + " (" + ", ".join(table) + ")")
        return best[1]
    if method in ("auto", "", None):
        method = next((m for m in AUTO_ORDER if m in avail), None)
    if method not in avail:
        raise RuntimeError(f"Method '{method}' not available. Installed: {avail}")
    rgb, _ = common.load_rgb(image_path)
    # SAM 3D Body estimates its own FOV (MoGe-2) unless we know the focal
    fpx, fsrc = None, ""
    exif = common.exif_focal_35mm(image_path)
    if focal_35mm or exif or method != "sam3d_body":
        fpx, fsrc = focal.resolve(image_path, rgb, focal_35mm,
                                  allow_moge=focal.moge_available())
    with _lock:
        res = METHODS[method].run(image_path, focal_px=fpx, focal_note=fsrc)
        if do_fit and keypoints2d.available():
            _refine_with_2d(res, rgb)
        if use_gravity and gravity.available():
            try:
                g = gravity.estimate(image_path, res["camera"]["fx"])
                if g:
                    res["up_cam"] = g["up_cam"]
                    res.setdefault("notes", []).append(
                        f"GeoCalib roll {g['roll_deg']:.1f} pitch {g['pitch_deg']:.1f}")
            except Exception as e:  # noqa: BLE001
                res.setdefault("notes", []).append(f"GeoCalib failed: {e}")
        return res


def _refine_with_2d(res, rgb):
    """Snap the 3D points onto RTMW whole-body 2D keypoints (see methods/fit.py)."""
    try:
        people = keypoints2d.detect(rgb)
        if not people:
            return
        cam = res["camera"]
        f, cx, cy = cam["fx"], cam["cx"], cam["cy"]
        H, W = rgb.shape[:2]
        pts = res["points3d"]
        # pick the detected person that best matches the regressor's person
        kp = min(people, key=lambda p: min(
            fit.label_error(pts, p, f, cx, cy, fit.LR_CHECK),
            fit.label_error(fit.flip_front_back(
                {k: __import__("numpy").asarray(v) for k, v in pts.items()}),
                p, f, cx, cy, fit.LR_CHECK)))
        notes = res.setdefault("notes", [])
        try:  # hands: high-res crop re-detection + palm/back (chirality) fix
            pts, kp = hands.refine(pts, kp, rgb, notes, cam=(f, cx, cy))
        except Exception as e:  # noqa: BLE001
            notes.append(f"hand re-detection failed: {e}")
        pts = hands.fix_chirality(pts, notes)
        new_pts, info = fit.fit(pts, kp, f, cx, cy, W, H)
        new_pts = hands.fix_chirality(new_pts, notes)
        try:  # fit the puppet rig itself (exact in Blender, no retarget loss)
            rig = fit_rig.fit_rig(new_pts, kp, f, cx, cy, W, H)
            res["rig"] = {"G": rig["G"], "pelvis_wc": rig["pelvis_wc"]}
            info.update(rig["info"])
            new_pts = rig["points3d"]
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            notes.append(f"rig fit failed: {e}")
        res["points3d_raw"] = pts
        res["points3d"] = new_pts
        res["points2d"] = {k: [v[0], v[1]] for k, v in kp.items() if v[2] >= 0.4}
        res["fit"] = info
        res.setdefault("notes", []).append("2D fit (RTMW): " + ", ".join(
            f"{k}={v}" for k, v in info.items()))
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        res.setdefault("notes", []).append(f"2D fit failed: {e}")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/health"):
            gpu = ""
            try:
                import torch
                gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
            except Exception:
                gpu = "no torch"
            self._send(200, {"ok": True, "methods": available_methods(), "gpu": gpu,
                             "gravity": gravity.available(), "moge": focal.moge_available(),
                             "fit2d": keypoints2d.available()})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if not self.path.startswith("/estimate"):
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n).decode("utf-8"))
            res = estimate(req["image_path"], req.get("method", "auto"),
                           float(req.get("focal_35mm") or 0.0),
                           bool(req.get("gravity", True)), bool(req.get("fit", True)))
            self._send(200, res)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self._send(200, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):
        sys.stderr.write("[pose-server] " + fmt % args + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--once", help="run a single image and exit")
    ap.add_argument("--batch", help="run every image in this folder; JSONs go to --out")
    ap.add_argument("--method", default="auto")
    ap.add_argument("--focal", type=float, default=0.0, help="35mm-equivalent focal")
    ap.add_argument("--out", help="write result JSON here (with --once)")
    ap.add_argument("--no-gravity", action="store_true", help="skip GeoCalib")
    ap.add_argument("--no-fit", action="store_true", help="skip the RTMW 2D fitting stage")
    a = ap.parse_args()
    if a.batch:
        exts = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff")
        out_dir = a.out or os.path.join(a.batch, "results")
        os.makedirs(out_dir, exist_ok=True)
        for name in sorted(os.listdir(a.batch)):
            if not name.lower().endswith(exts):
                continue
            stem = os.path.splitext(name)[0]
            try:
                res = estimate(os.path.abspath(os.path.join(a.batch, name)), a.method,
                               a.focal, not a.no_gravity, not a.no_fit)
                with open(os.path.join(out_dir, f"{stem}_{a.method}.json"), "w",
                          encoding="utf-8") as fh:
                    json.dump(res, fh, indent=1)
                print(f"OK   {name}: " + " | ".join(res.get("notes", [])))
            except Exception as e:  # noqa: BLE001
                print(f"FAIL {name}: {e}")
        return
    if a.once:
        res = estimate(os.path.abspath(a.once), a.method, a.focal, not a.no_gravity, not a.no_fit)
        txt = json.dumps(res, indent=1)
        if a.out:
            with open(a.out, "w", encoding="utf-8") as fh:
                fh.write(txt)
        print("\n".join(res.get("notes", [])), f"\n{len(res['points3d'])} points")
        return
    print(f"Pose server on http://{a.host}:{a.port}  methods: {available_methods()}")
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
