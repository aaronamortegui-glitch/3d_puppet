"""Camera gravity (roll/pitch) + focal with GeoCalib (ECCV 2024).

Code Apache-2.0, weights CC-BY-4.0.  https://github.com/cvg/GeoCalib
Returns the world *up* direction expressed in OpenCV camera axes.
"""

import numpy as np

_model = None


def available():
    try:
        import geocalib  # noqa: F401
        return True
    except Exception:
        return False


def estimate(image_path, focal_px=None):
    """-> dict(up_cam=[x,y,z], focal_px=float, roll_deg, pitch_deg) or None."""
    global _model
    try:
        import torch
        from geocalib import GeoCalib
    except Exception:
        return None
    if _model is None:
        _model = GeoCalib().to("cuda").eval()
    img = _model.load_image(image_path).to("cuda")
    kwargs = {}
    if focal_px:
        kwargs["priors"] = {"focal": torch.tensor(float(focal_px), device="cuda")}
    with torch.no_grad():
        try:
            res = _model.calibrate(img, **kwargs)
        except TypeError:
            res = _model.calibrate(img)
    g = res["gravity"]
    vec = g.vec3d.reshape(-1, 3)[0].cpu().numpy().astype(float)
    up = -vec / (np.linalg.norm(vec) + 1e-9)
    if up[1] > 0:  # in OpenCV axes "up" must point to -y for a sane photo
        up = -up
    rp = g.rp.reshape(-1, 2)[0].cpu().numpy()
    f = float(res["camera"].f.reshape(-1)[0].cpu())
    return {"up_cam": up.tolist(), "focal_px": f,
            "roll_deg": float(np.degrees(rp[0])), "pitch_deg": float(np.degrees(rp[1]))}
