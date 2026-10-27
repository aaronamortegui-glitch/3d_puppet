"""Fix only the product of an image: crop around it, edit the crop, stitch it back (test 20).

Adapted from EL_Inpainting_system (vendor/comfyui-inpaint-cropstitch-nb2 SmartMaskCrop / SmartMaskStitch,
engine/blend.py): the edit sees a crop, never the whole picture, and only the product area is pasted back,
so the face, the hair and the background keep their original pixels.

    python tools/inpaint_product.py crop   <image> <x0> <y0> <x1> <y1> <out_dir>
    python tools/inpaint_product.py stitch <out_dir> <edited_crop.png> <final.png>

<x0 y0 x1 y1> is the product box as fractions of the image (the tool, the hand that holds it and the hair it
touches). crop writes <out_dir>/crop_model.png (the model input, long side 2048) and crop.json.
stitch resizes the edit back, colour-matches it to the original crop (LAB mean/std on the ring outside the
product box) and pastes the product box grown by 6% with a feathered edge.
"""
import json
import os
import sys

import cv2
import numpy as np

GROW = 1.35       # context around the product box
MIN_SIDE = 768    # px of the source image
MODEL_SIDE = 2048 # long side sent to the model
PASTE_GROW = 0.06 # product box grown by this fraction of the crop for the paste
FEATHER = 0.05    # feather of the paste mask, fraction of the crop's long side
# The exact shapes Sunburst returns at 2K (w / h). The crop must have one of them, or the edit is stretched on the way
# back and the product lands off its place (test 20 bug: near-square crops came back 3:4 / 4:3, up to 35% stretched).
ASPECTS = {"3:4": 1760 / 2368, "1:1": 1.0, "4:3": 2368 / 1760}
# Wide banners (test 22): the product spans most of a 16:9 frame, so the crop can be 16:9 (Sunburst 4K: 3840 x 2160).
ASPECTS["16:9"] = 3840 / 2160


def load(p):
    im = cv2.imread(p, cv2.IMREAD_COLOR)
    if im is None:
        raise SystemExit(f"cannot read {p}")
    return im


def crop(image, box, out_dir):
    im = load(image)
    h, w = im.shape[:2]
    x0, y0, x1, y1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    bw, bh = max((x1 - x0) * GROW, MIN_SIDE), max((y1 - y0) * GROW, MIN_SIDE)
    name = min(ASPECTS, key=lambda k: abs(np.log(ASPECTS[k] * bh / bw)))  # nearest model shape
    aspect = ASPECTS[name]
    if bw / bh < aspect:  # grow only
        bw = bh * aspect
    else:
        bh = bw / aspect
    k = min(1.0, w / bw, h / bh)  # too big for the image: shrink both sides, never just one (keeps the aspect)
    bw, bh = bw * k, bh * k
    cx0 = int(round(min(max(cx - bw / 2, 0), w - bw)))
    cy0 = int(round(min(max(cy - bh / 2, 0), h - bh)))
    cw, ch = int(round(bw)), int(round(bh))
    c = im[cy0:cy0 + ch, cx0:cx0 + cw]
    s = MODEL_SIDE / max(cw, ch)
    model = cv2.resize(c, (int(round(cw * s)), int(round(ch * s))), interpolation=cv2.INTER_LANCZOS4)
    os.makedirs(out_dir, exist_ok=True)
    cv2.imwrite(os.path.join(out_dir, "crop_model.png"), model)
    meta = {"image": image, "box": box, "crop": [cx0, cy0, cw, ch], "aspect": name,
            "product_in_crop": [(x0 - cx0) / cw, (y0 - cy0) / ch, (x1 - cx0) / cw, (y1 - cy0) / ch]}
    json.dump(meta, open(os.path.join(out_dir, "crop.json"), "w"), indent=1)
    print(json.dumps(meta))


def lab_match(src, ref, ring):
    """Reinhard transfer: src's LAB mean/std on the ring set to ref's."""
    a = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float32)
    b = cv2.cvtColor(ref, cv2.COLOR_BGR2LAB).astype(np.float32)
    for k in range(3):
        ma, sa = a[..., k][ring].mean(), a[..., k][ring].std() + 1e-6
        mb, sb = b[..., k][ring].mean(), b[..., k][ring].std() + 1e-6
        a[..., k] = (a[..., k] - ma) * (sb / sa) + mb
    return cv2.cvtColor(np.clip(a, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def register(ed, orig, ring):
    """Warp the edit onto the original crop: the model may shift, scale or re-frame the scene slightly.
    Similarity transform (shift, scale, small rotation) from ORB matches outside the product, RANSAC."""
    orb = cv2.ORB_create(6000)
    g1, g2 = cv2.cvtColor(ed, cv2.COLOR_BGR2GRAY), cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY)
    m = ring.astype(np.uint8) * 255
    k1, d1 = orb.detectAndCompute(g1, m)
    k2, d2 = orb.detectAndCompute(g2, m)
    if d1 is None or d2 is None or len(k1) < 30 or len(k2) < 30:
        return ed, "no registration (too few features)"
    matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2)
    if len(matches) < 20:
        return ed, "no registration (too few matches)"
    a = np.float32([k1[x.queryIdx].pt for x in matches])
    b = np.float32([k2[x.trainIdx].pt for x in matches])
    M, inl = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=3)
    if M is None or inl.sum() < 15:
        return ed, "no registration (RANSAC failed)"
    h, w = orig.shape[:2]
    out = cv2.warpAffine(ed, M, (w, h), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    s = float(np.hypot(M[0, 0], M[1, 0]))
    return out, f"registered: scale {s:.3f}, shift {M[0, 2]:.1f},{M[1, 2]:.1f} px, {int(inl.sum())} inliers"


def stitch(out_dir, edited, final):
    meta = json.load(open(os.path.join(out_dir, "crop.json")))
    im = load(meta["image"])
    cx0, cy0, cw, ch = meta["crop"]
    orig = im[cy0:cy0 + ch, cx0:cx0 + cw]
    raw = load(edited)
    # resize by width only (no stretch) onto the crop, then register; aspect mismatch is reported
    s = cw / raw.shape[1]
    ed = cv2.resize(raw, (cw, max(1, int(round(raw.shape[0] * s)))), interpolation=cv2.INTER_LANCZOS4)
    ed = cv2.copyMakeBorder(ed, 0, max(0, ch - ed.shape[0]), 0, 0, cv2.BORDER_REPLICATE)[:ch]
    off = abs(np.log((raw.shape[1] / raw.shape[0]) / (cw / ch)))
    px0, py0, px1, py1 = meta["product_in_crop"]
    g = PASTE_GROW
    bx0, by0 = int(max(px0 - g, 0) * cw), int(max(py0 - g, 0) * ch)
    bx1, by1 = int(min(px1 + g, 1) * cw), int(min(py1 + g, 1) * ch)
    mask = np.zeros((ch, cw), np.float32)
    mask[by0:by1, bx0:bx1] = 1
    ring = mask < 0.5
    if ring.sum() < 1000:  # product fills the crop: register on everything
        ring = np.ones_like(ring)
    ed, how = register(ed, orig, ring)
    diff = float(np.abs(cv2.cvtColor(ed, cv2.COLOR_BGR2GRAY).astype(float)
                        - cv2.cvtColor(orig, cv2.COLOR_BGR2GRAY).astype(float))[mask < 0.5].mean()) if (mask < 0.5).sum() else -1
    print(f"aspect off {off * 100:.1f}% · {how} · mean diff outside the product {diff:.1f}")
    ring = mask < 0.5
    if ring.sum() > 1000:
        ed = lab_match(ed, orig, ring)
    k = int(FEATHER * max(cw, ch)) | 1
    mask = cv2.GaussianBlur(mask, (k, k), k / 3)
    edge = np.ones_like(mask)  # never touch the crop border (7% ramp, as SmartMaskStitch)
    r = max(int(0.07 * min(cw, ch)), 1)
    ramp = np.clip(np.arange(r) / r, 0, 1)
    edge[:r, :] *= ramp[:, None]; edge[-r:, :] *= ramp[::-1][:, None]
    edge[:, :r] *= ramp[None, :]; edge[:, -r:] *= ramp[::-1][None, :]
    m = (mask * edge)[..., None]
    out = im.copy()
    out[cy0:cy0 + ch, cx0:cx0 + cw] = (ed * m + orig * (1 - m)).astype(np.uint8)
    cv2.imwrite(final, out)
    print(final)


if __name__ == "__main__":
    if sys.argv[1] == "crop":
        crop(sys.argv[2], [float(v) for v in sys.argv[3:7]], sys.argv[7])
    else:
        stitch(sys.argv[2], sys.argv[3], sys.argv[4])
