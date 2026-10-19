"""Focal length estimation: user value > EXIF > MoGe-2 > default."""

from . import common

_moge = None


def moge_available():
    try:
        import moge  # noqa: F401
        return True
    except Exception:
        return False


def moge_fov(rgb):
    """Return focal in pixels from MoGe-2 (Microsoft, MIT), or None."""
    global _moge
    try:
        import torch
        from moge.model.v2 import MoGeModel
    except Exception:
        return None
    if _moge is None:
        _moge = MoGeModel.from_pretrained("Ruicheng/moge-2-vitl-normal").cuda().eval()
    h, w = rgb.shape[:2]
    t = torch.tensor(rgb / 255.0, dtype=torch.float32, device="cuda").permute(2, 0, 1)
    with torch.no_grad():
        out = _moge.infer(t)
    K = out["intrinsics"].cpu().numpy()  # normalised (fx / width)
    return float(K[0, 0] * w)


def resolve(image_path, rgb, focal_35mm=0.0, default_35mm=35.0, allow_moge=True):
    """Returns (focal_px, source)."""
    h, w = rgb.shape[:2]
    if focal_35mm:
        return common.focal_px_from_35mm(focal_35mm, w, h), f"user {focal_35mm:.0f}mm"
    exif = common.exif_focal_35mm(image_path)
    if exif:
        return common.focal_px_from_35mm(exif, w, h), f"EXIF {exif:.0f}mm"
    if allow_moge:
        f = moge_fov(rgb)
        if f:
            f35 = f / ((w * w + h * h) ** 0.5) * 43.2666
            return f, f"MoGe-2 ~{f35:.0f}mm"
    return common.focal_px_from_35mm(default_35mm, w, h), f"default {default_35mm:.0f}mm"
