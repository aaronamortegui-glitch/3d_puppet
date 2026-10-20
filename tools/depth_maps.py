"""Depth maps with MoGe-2 for a set of images (photos or AI renders).

    server\\.venv\\Scripts\\python.exe tools\\depth_maps.py <out_dir> <image> [<image> ...]

For each image writes, next to <out_dir>/<stem>:
  <stem>_depth16.png   16-bit grayscale, NEAR = BRIGHT (ControlNet / depth-to-image
                       convention), normalised to the valid-depth range of that image;
                       invalid pixels (sky / background MoGe masks out) are 0
  <stem>_depth.png     colorized preview (turbo) of the same map
  <stem>_depth.npz     raw metric depth (metres), validity mask and focal in pixels
"""

import os
import sys

import numpy as np
from PIL import Image

_model = None


def load_model():
    global _model
    if _model is None:
        import torch  # noqa: F401
        from moge.model.v2 import MoGeModel
        _model = MoGeModel.from_pretrained("Ruicheng/moge-2-vitl-normal").cuda().eval()
    return _model


def infer(rgb):
    import torch
    t = torch.tensor(rgb / 255.0, dtype=torch.float32, device="cuda").permute(2, 0, 1)
    with torch.no_grad():
        out = load_model().infer(t)
    depth = out["depth"].cpu().numpy()
    mask = out["mask"].cpu().numpy().astype(bool) if "mask" in out else np.isfinite(depth)
    mask &= np.isfinite(depth)
    focal = float(out["intrinsics"].cpu().numpy()[0, 0] * rgb.shape[1])
    return depth, mask, focal


def normalise(depth, mask):
    """Inverse-depth (disparity) scaled to 0..1 inside the mask, near = 1."""
    disp = np.zeros_like(depth, dtype=np.float64)
    disp[mask] = 1.0 / np.maximum(depth[mask], 1e-6)
    lo, hi = np.percentile(disp[mask], [1, 99]) if mask.any() else (0.0, 1.0)
    n = np.clip((disp - lo) / max(hi - lo, 1e-9), 0, 1)
    n[~mask] = 0
    return n


def colorize(n, mask):
    import cv2
    c = cv2.applyColorMap((n * 255).astype(np.uint8), cv2.COLORMAP_TURBO)[..., ::-1].copy()
    c[~mask] = 0
    return c


def main():
    out_dir, paths = sys.argv[1], sys.argv[2:]
    os.makedirs(out_dir, exist_ok=True)
    for p in paths:
        stem = os.path.splitext(os.path.basename(p))[0]
        rgb = np.asarray(Image.open(p).convert("RGB"))
        depth, mask, focal = infer(rgb)
        n = normalise(depth, mask)
        Image.fromarray((n * 65535).astype(np.uint16)).save(
            os.path.join(out_dir, stem + "_depth16.png"))
        Image.fromarray(colorize(n, mask)).save(os.path.join(out_dir, stem + "_depth.png"))
        np.savez_compressed(os.path.join(out_dir, stem + "_depth.npz"),
                            depth=depth.astype(np.float32), mask=mask, focal_px=focal)
        d = depth[mask]
        print(f"{stem}: {rgb.shape[1]}x{rgb.shape[0]} focal {focal:.0f}px "
              f"depth {d.min():.2f}-{np.median(d):.2f}-{d.max():.2f} m, valid {mask.mean():.0%}")


if __name__ == "__main__":
    main()
