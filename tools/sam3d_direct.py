"""SAM 3D Body straight on the photo: the person's 3D mesh, no rig, no fitting.

    server\\.venv\\Scripts\\python.exe tools\\sam3d_direct.py <out_dir> <image> [<image> ...]

SAM 3D Body regresses Meta's MHR body (shape + pose + camera) for every person,
so the photo gives a full 3D mesh already aligned to the image. For each image:
  <stem>_mesh.obj        the 3D mesh in camera space (metres, OpenCV axes)
  <stem>_overlay.png     shaded mesh blended over the photo
  <stem>_mask.png        person silhouette from the mesh (3D-based segmentation)
  <stem>_depth.png       mesh depth, near = bright (16-bit)
  <stem>_sheet.png       photo | overlay | mask | depth
"""

import os
import sys

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
from methods import common, sam3d_method  # noqa: E402
from methods.detect import person_boxes  # noqa: E402

FACES = np.load(os.path.join(ROOT, "puppet_pose", "assets", "human.npz"))["faces"]


def _camera_points(o, key):
    """Points in OpenCV camera space, checked against the 2D keypoints."""
    f = float(np.asarray(o["focal_length"]).reshape(-1)[0])
    t = np.asarray(o["pred_cam_t"], dtype=np.float64).reshape(3)
    k3 = np.asarray(o["pred_keypoints_3d"], dtype=np.float64).reshape(-1, 3)
    k2 = np.asarray(o["pred_keypoints_2d"], dtype=np.float64).reshape(-1, 2)
    best = None
    for flip in (np.array([1, 1, 1]), np.array([1, -1, -1])):
        P = k3 * flip + t
        uv = P[:, :2] / P[:, 2:3] * f
        off = np.median(k2 - uv, 0)                       # principal point
        err = np.median(np.linalg.norm(uv + off - k2, axis=1))
        if best is None or err < best[0]:
            best = (err, flip, off)
    _, flip, off = best
    V = np.asarray(o[key], dtype=np.float64).reshape(-1, 3) * flip + t
    return V, f, off, best[0]


def render(V, f, c, H, W):
    """Painter's-algorithm raster of the mesh: shaded image, mask, depth."""
    uv = V[:, :2] / V[:, 2:3] * f + c
    tri = FACES
    z = V[tri, 2].mean(1)
    n = np.cross(V[tri[:, 1]] - V[tri[:, 0]], V[tri[:, 2]] - V[tri[:, 0]])
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    shade = np.clip(np.abs(n[:, 2]) * 0.8 + 0.2, 0, 1)
    img = np.zeros((H, W, 3), np.float32)
    mask = np.zeros((H, W), np.uint8)
    depth = np.zeros((H, W), np.float32)
    for i in np.argsort(-z):                               # far to near
        pts = np.round(uv[tri[i]]).astype(np.int32)
        col = (0.25 * shade[i], 0.55 * shade[i], 1.0 * shade[i])
        cv2.fillConvexPoly(img, pts, col)
        cv2.fillConvexPoly(mask, pts, 255)
        cv2.fillConvexPoly(depth, pts, float(z[i]))
    return img, mask, depth


def main():
    out, paths = sys.argv[1], sys.argv[2:]
    os.makedirs(out, exist_ok=True)
    est = sam3d_method._load()
    for p in paths:
        stem = os.path.splitext(os.path.basename(p))[0]
        rgb, _ = common.load_rgb(p)
        H, W = rgb.shape[:2]
        outs = est.process_one_image(rgb, bboxes=person_boxes(rgb))
        if not outs:
            print("no person:", p)
            continue
        o = max(outs, key=lambda d: float(d["bbox"][3] - d["bbox"][1]))
        V, f, c, err = _camera_points(o, "pred_vertices")
        img, mask, depth = render(V, f, c, H, W)
        a = (mask[..., None] > 0) * 0.65
        over = (rgb / 255.0) * (1 - a) + img * a
        cv2.imwrite(os.path.join(out, f"{stem}_overlay.png"), (over[..., ::-1] * 255).astype(np.uint8))
        cv2.imwrite(os.path.join(out, f"{stem}_mask.png"), mask)
        m = mask > 0
        dn = np.zeros_like(depth)
        if m.any():
            lo, hi = depth[m].min(), depth[m].max()
            dn[m] = 1 - (depth[m] - lo) / max(hi - lo, 1e-6) * 0.85
        cv2.imwrite(os.path.join(out, f"{stem}_depth.png"), (dn * 65535).astype(np.uint16))
        with open(os.path.join(out, f"{stem}_mesh.obj"), "w") as fh:
            fh.writelines(f"v {x:.5f} {y:.5f} {z:.5f}\n" for x, y, z in V)
            fh.writelines(f"f {a + 1} {b + 1} {d + 1}\n" for a, b, d in FACES)
        tiles = [rgb[..., ::-1], (over[..., ::-1] * 255).astype(np.uint8),
                 cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR),
                 cv2.applyColorMap((dn * 255).astype(np.uint8), cv2.COLORMAP_TURBO) * m[..., None]]
        h = 600
        tiles = [cv2.resize(t, (int(t.shape[1] * h / t.shape[0]), h)) for t in tiles]
        cv2.imwrite(os.path.join(out, f"{stem}_sheet.png"), np.hstack(tiles))
        print(f"{stem}: {len(V)} verts, keypoint reprojection {err:.1f}px, "
              f"mask {m.mean():.0%} of image, depth {depth[m].min():.2f}-{depth[m].max():.2f} m")


if __name__ == "__main__":
    main()
