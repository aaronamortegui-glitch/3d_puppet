"""Synthetic validation of the ChArUco calibration (ground truth from Blender).

    1) blender -b --factory-startup --python tests/render_charuco.py -- <board.png> <render_dir>
    2) python tests/test_calibration.py <render_dir> <board.json>

A known lens distortion is applied to the renders, then:
  - intrinsics are calibrated and compared with the true focal / centre /
    distortion,
  - the plate camera pose is solved and compared with the true camera.
Exit code != 0 on failure.
"""

import glob
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
from calibration import charuco  # noqa: E402

RENDER, BOARD_JSON = sys.argv[1], sys.argv[2]
TRUE_DIST = np.array([-0.08, 0.02, 0.0, 0.0, 0.0])
truth = json.load(open(os.path.join(RENDER, "truth.json")))
spec = json.load(open(BOARD_JSON))
W, H = truth["width"], truth["height"]
K = np.array([[truth["fx"], 0, truth["cx"]], [0, truth["fy"], truth["cy"]], [0, 0, 1]])


def distort(img):
    """Synthesise what a lens with TRUE_DIST would record."""
    xs, ys = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    pts = np.stack([xs.ravel(), ys.ravel()], 1).reshape(-1, 1, 2)
    und = cv2.undistortPoints(pts, K, TRUE_DIST, P=K).reshape(H, W, 2)
    return cv2.remap(img, und[..., 0], und[..., 1], cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=(190, 190, 190))


dist_dir = os.path.join(RENDER, "distorted")
os.makedirs(dist_dir, exist_ok=True)
for p in sorted(glob.glob(os.path.join(RENDER, "*.png"))):
    cv2.imwrite(os.path.join(dist_dir, os.path.basename(p)), distort(cv2.imread(p)))

# ---- 1. intrinsics ---------------------------------------------------------
calib = sorted(glob.glob(os.path.join(dist_dir, "calib_*.png")))
prof = charuco.calibrate(calib, spec, "synthetic", "50mm", log=lambda *_: None)
ef = abs(prof["fx"] - truth["fx"]) / truth["fx"] * 100
ec = math.hypot(prof["cx"] - truth["cx"], prof["cy"] - truth["cy"])
k = prof["dist"]
print(f"views {prof['views']}  rms {prof['rms_px']}px")
print(f"focal  true {truth['fx']:.1f}px  got {prof['fx']:.1f}px  err {ef:.3f}%  "
      f"(35mm-eq {prof['focal_35mm_equiv']}mm, true {50 * 43.2666 / 36 * W / math.hypot(W, H):.2f})")
print(f"centre err {ec:.2f}px   k1 true {TRUE_DIST[0]} got {k[0]:.4f}   k2 true {TRUE_DIST[1]} got {k[1]:.4f}")

# distortion coefficients are correlated (k1/k2/k3 trade off), so compare the
# undistortion DISPLACEMENT FIELD instead: where does each pixel end up?
gx, gy = np.meshgrid(np.linspace(0, W - 1, 81), np.linspace(0, H - 1, 61))
grid = np.stack([gx.ravel(), gy.ravel()], 1).astype(np.float32).reshape(-1, 1, 2)
Kp = np.array([[prof["fx"], 0, prof["cx"]], [0, prof["fy"], prof["cy"]], [0, 0, 1]])
u_true = cv2.undistortPoints(grid, K, TRUE_DIST, P=K).reshape(-1, 2)
u_est = cv2.undistortPoints(grid, Kp, np.array(prof["dist"]), P=K).reshape(-1, 2)
field = np.linalg.norm(u_true - u_est, axis=1)
r = np.hypot((grid[:, 0, 0] - W / 2) / (W / 2), (grid[:, 0, 1] - H / 2) / (H / 2))
centre_err = float(np.percentile(field[r <= 0.8], 95))
corner_err = float(field.max())
# what matters for the 3D camera is the ray direction of each pixel
ang_c = math.degrees(centre_err / truth["fx"])
ang_max = math.degrees(corner_err / truth["fx"])
print(f"pixel-ray error (whole camera model): 95th pct central 80% {centre_err:.2f}px = {ang_c:.3f} deg, "
      f"max corners {corner_err:.2f}px = {ang_max:.3f} deg")

# residual distortion after undistortion: straightness of board rows
# (re-detect on undistorted calib images and fit a homography)
res_err = []
for p in calib[:6]:
    img = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
    u, Kn = charuco.undistort(img, prof)
    o, i = charuco.detect(cv2.cvtColor(u, cv2.COLOR_RGB2GRAY), charuco.make_board_obj(**spec))
    if o is not None and len(o) >= 8:
        Hm, _ = cv2.findHomography(o[:, :2], i, 0)
        pr = cv2.perspectiveTransform(o[:, None, :2], Hm).reshape(-1, 2)
        res_err.append(float(np.sqrt(np.mean(np.sum((pr - i) ** 2, 1)))))
print(f"undistorted planarity residual {np.mean(res_err):.3f}px (0 = perfectly straight)")

# ---- 2. plate camera pose --------------------------------------------------
img = cv2.cvtColor(cv2.imread(os.path.join(dist_dir, "plate.png")), cv2.COLOR_BGR2RGB)
und, Kn = charuco.undistort(img, prof)
bp = charuco.board_pose(und, Kn, None, spec, "floor")
assert bp is not None, "board not found in plate"
M = np.array(bp["world_from_cv"])
Mt = np.array(truth["plate_cam_matrix_world"])
true_pos = Mt[:3, 3] - np.array(truth["board_origin_world"])     # board-world coords
true_R = Mt[:3, :3] @ np.diag([1, -1, -1])                        # Blender cam -> OpenCV cam axes
ep = np.linalg.norm(M[:3, 3] - true_pos) * 1000
Rerr = M[:3, :3].T @ true_R
ea = math.degrees(math.acos(np.clip((np.trace(Rerr) - 1) / 2, -1, 1)))
dist_m = np.linalg.norm(true_pos)
print(f"plate camera  true {np.round(true_pos, 4)}  got {np.round(M[:3, 3], 4)}")
print(f"position err {ep:.1f} mm at {dist_m:.2f} m ({ep / dist_m / 10:.3f}%)  "
      f"rotation err {ea:.3f} deg  reproj {bp['reproj_px']}px  corners {bp['corners']}")

with open(os.path.join(RENDER, "profile_synthetic.json"), "w") as fh:
    json.dump(prof, fh, indent=1)
with open(os.path.join(RENDER, "plate_pose.json"), "w") as fh:
    json.dump(bp, fh, indent=1)

ok = ef < 0.5 and ec < 3 and ang_c < 0.1 and ang_max < 0.2 and np.mean(res_err) < 0.3 \
    and ep < 15 and ea < 0.5
print("RESULT:", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
