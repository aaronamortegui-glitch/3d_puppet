"""ChArUco camera calibration for our own photo shoots.

Three steps (see docs/CAPTURE_GUIDE.md):

1. make_board()        -> printable board (PNG + PDF) with exact sizes
2. calibrate()         -> camera profile JSON (focal, principal point,
                          distortion) from 10-30 photos of the board,
                          once per camera + lens + zoom setting
3. board_pose()        -> exact camera position/rotation for a shot in
                          which the board is visible (board = world origin)

Conventions
-----------
Board frame (OpenCV): origin at the board's top-left inner corner, x to the
right along the board, y down along the board, z into the board.
We expose a Blender-style *world* frame (Z up, meters):
  - board on the FLOOR (default): world X = board x, world Y = -board y,
    world Z = -board z (board normal pointing up, out of the print).
  - board on a WALL / stand (vertical): world X = board x, world Z = -board y
    (board "up" is world up), world Y = board z (into the wall).
"""

import json
import math
import os

import cv2
import numpy as np

DEFAULT = dict(squares_x=7, squares_y=5, square_m=0.04, marker_m=0.03,
               dictionary="DICT_5X5_250")


def _dict(name):
    return cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, name))


def make_board_obj(squares_x=7, squares_y=5, square_m=0.04, marker_m=0.03,
                   dictionary="DICT_5X5_250"):
    return cv2.aruco.CharucoBoard((squares_x, squares_y), square_m, marker_m, _dict(dictionary))


def board_spec(spec=None):
    s = dict(DEFAULT)
    s.update(spec or {})
    return s


# ---------------------------------------------------------------------------
# 1. printable board
# ---------------------------------------------------------------------------
def make_board(out_dir, dpi=300, **spec):
    """Write board PNG + PDF (exact physical size at `dpi`) + spec JSON."""
    s = board_spec(spec)
    board = make_board_obj(**s)
    px_per_m = dpi / 0.0254
    w_px = int(round(s["squares_x"] * s["square_m"] * px_per_m))
    h_px = int(round(s["squares_y"] * s["square_m"] * px_per_m))
    margin = int(round(0.01 * px_per_m))  # 1 cm white margin
    img = board.generateImage((w_px + 2 * margin, h_px + 2 * margin), marginSize=margin, borderBits=1)
    os.makedirs(out_dir, exist_ok=True)
    name = f"charuco_{s['squares_x']}x{s['squares_y']}_{int(s['square_m'] * 1000)}mm"
    png = os.path.join(out_dir, name + ".png")
    cv2.imwrite(png, img)
    pdf = os.path.join(out_dir, name + ".pdf")
    try:
        from PIL import Image
        Image.fromarray(img).convert("L").save(pdf, resolution=dpi)
    except Exception:  # noqa: BLE001
        pdf = None
    with open(os.path.join(out_dir, name + ".json"), "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=1)
    return {"png": png, "pdf": pdf, "spec": s,
            "print_size_mm": [round((w_px + 2 * margin) / px_per_m * 1000, 1),
                              round((h_px + 2 * margin) / px_per_m * 1000, 1)]}


# ---------------------------------------------------------------------------
# detection helpers
# ---------------------------------------------------------------------------
def detect(gray, board):
    det = cv2.aruco.CharucoDetector(board)
    corners, ids, _, _ = det.detectBoard(gray)
    if ids is None or len(ids) < 6:
        return None, None
    obj, img = board.matchImagePoints(corners, ids)
    return obj.reshape(-1, 3).astype(np.float32), img.reshape(-1, 2).astype(np.float32)


def _gray(path):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(path)).convert("L")
    return np.asarray(im)


# ---------------------------------------------------------------------------
# 2. intrinsics
# ---------------------------------------------------------------------------
def calibrate(image_paths, spec=None, camera_name="", lens_name="", log=print):
    """Calibrate intrinsics from photos of the board (same camera/lens/zoom).
    Returns the camera profile dict."""
    s = board_spec(spec)
    board = make_board_obj(**s)
    objs, imgs, used, size = [], [], [], None
    for p in image_paths:
        g = _gray(p)
        if size is None:
            size = (g.shape[1], g.shape[0])
        elif (g.shape[1], g.shape[0]) != size:
            log(f"skip {os.path.basename(p)}: different resolution")
            continue
        o, i = detect(g, board)
        if o is None:
            log(f"skip {os.path.basename(p)}: board not found")
            continue
        objs.append(o)
        imgs.append(i)
        used.append(os.path.basename(p))
    if len(objs) < 4:
        raise RuntimeError(f"Need >= 4 usable board photos, got {len(objs)}")
    W, H = size
    f0 = max(W, H)
    K0 = np.array([[f0, 0, W / 2], [0, f0, H / 2], [0, 0, 1]], dtype=np.float64)
    # k3 is fixed: for normal (non-fisheye) lenses it only overfits and makes the
    # corners unstable; tangential distortion is negligible on modern lenses
    flags = (cv2.CALIB_USE_INTRINSIC_GUESS | cv2.CALIB_FIX_ASPECT_RATIO |
             cv2.CALIB_ZERO_TANGENT_DIST | cv2.CALIB_FIX_K3)
    rms, K, dist, rvecs, tvecs = cv2.calibrateCamera(objs, imgs, size, K0, None, flags=flags)
    # per-view error
    errs = []
    for o, i, r, t in zip(objs, imgs, rvecs, tvecs):
        pr, _ = cv2.projectPoints(o, r, t, K, dist)
        errs.append(float(np.sqrt(np.mean(np.sum((pr.reshape(-1, 2) - i) ** 2, 1)))))
    fx = float(K[0, 0])
    f35 = fx / math.hypot(W, H) * math.hypot(36, 24)
    prof = {
        "type": "puppet_pose_camera_profile", "version": 1,
        "camera": camera_name, "lens": lens_name,
        "width": W, "height": H,
        "fx": fx, "fy": float(K[1, 1]), "cx": float(K[0, 2]), "cy": float(K[1, 2]),
        "dist": [float(v) for v in dist.ravel()],
        "focal_35mm_equiv": round(f35, 2),
        "hfov_deg": round(math.degrees(2 * math.atan(W / (2 * fx))), 2),
        "rms_px": round(float(rms), 3),
        "views": len(objs), "view_errors_px": [round(e, 3) for e in errs],
        "images": used, "board": s,
    }
    return prof


def scale_profile(prof, width, height):
    """Adapt a profile to a resized image of the same aspect ratio."""
    sx, sy = width / prof["width"], height / prof["height"]
    if abs(sx - sy) > 0.01:
        raise ValueError("Image aspect ratio differs from the calibration (cropped photo?)")
    p = dict(prof)
    p.update(width=width, height=height, fx=prof["fx"] * sx, fy=prof["fy"] * sy,
             cx=prof["cx"] * sx, cy=prof["cy"] * sy)
    return p


def undistort(rgb, prof):
    """Undistort and re-centre the principal point.  Returns (rgb, K_new)."""
    H, W = rgb.shape[:2]
    p = scale_profile(prof, W, H) if (W, H) != (prof["width"], prof["height"]) else prof
    K = np.array([[p["fx"], 0, p["cx"]], [0, p["fy"], p["cy"]], [0, 0, 1]])
    dist = np.array(p["dist"])
    f = (p["fx"] + p["fy"]) / 2
    K_new = np.array([[f, 0, W / 2], [0, f, H / 2], [0, 0, 1]])
    out = cv2.undistort(rgb, K, dist, None, K_new)
    return out, K_new


# ---------------------------------------------------------------------------
# 3. extrinsics from a board in the shot
# ---------------------------------------------------------------------------
def _world_from_board(mount):
    if mount == "wall":
        # board x -> X, board y (down) -> -Z, board z (into wall) -> +Y
        return np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=np.float64)
    # floor: board x -> X, board y -> -Y, board z (into print = down) -> -Z
    return np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=np.float64)


def board_pose(rgb_or_path, K, dist=None, spec=None, mount="floor"):
    """Camera pose from a board visible in the image.

    K: 3x3 intrinsics of the (undistorted) image; dist: distortion (None if
    the image is already undistorted).  Returns dict with
    world_from_cv (4x4, OpenCV camera -> Blender-style world, meters),
    reprojection error and camera position."""
    s = board_spec(spec)
    board = make_board_obj(**s)
    if isinstance(rgb_or_path, str):
        g = _gray(rgb_or_path)
    else:
        g = cv2.cvtColor(rgb_or_path, cv2.COLOR_RGB2GRAY) if rgb_or_path.ndim == 3 else rgb_or_path
    o, i = detect(g, board)
    if o is None:
        return None
    K = np.asarray(K, dtype=np.float64)
    d = np.zeros(5) if dist is None else np.asarray(dist, dtype=np.float64)
    ok, rvec, tvec = cv2.solvePnP(o, i, K, d, flags=cv2.SOLVEPNP_IPPE)
    if not ok:
        return None
    rvec, tvec = cv2.solvePnPRefineLM(o, i, K, d, rvec, tvec)
    R_cb, _ = cv2.Rodrigues(rvec)                 # board -> camera
    pr, _ = cv2.projectPoints(o, rvec, tvec, K, d)
    err = float(np.sqrt(np.mean(np.sum((pr.reshape(-1, 2) - i) ** 2, 1))))
    # camera -> board, then board -> world
    R_bc = R_cb.T
    t_bc = -R_bc @ tvec.reshape(3)
    Wb = _world_from_board(mount)
    M = np.eye(4)
    M[:3, :3] = Wb @ R_bc
    M[:3, 3] = Wb @ t_bc
    return {"world_from_cv": M.tolist(), "reproj_px": round(err, 3),
            "camera_position_m": [round(float(v), 4) for v in M[:3, 3]],
            "corners": int(len(o)), "mount": mount}
