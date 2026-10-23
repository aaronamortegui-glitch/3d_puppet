"""Scene QA: does a generated image keep the pose, the framing and the product size of its gray pose render?

    server\\.venv\\Scripts\\python.exe tools\\scene_qa.py <cases.json> <out.json>

cases.json: [{"id", "gray", "out", "sku", "hair_target"}, ...]  (paths relative to the repo root; "gray", "sku"
and "hair_target" are optional: without a gray render only the hair is measured)

Per case, against the gray render (the measurement plate, product in orange at true size):
  pose_drift   mean distance of 13 body keypoints (MediaPipe Pose), % of the image side
  face_scale   eye distance in the output / eye distance in the gray render (1.0 = same framing)
  face_shift   face centre shift, % of the image side
  product_ratio  product length / eye distance (Grounding DINO box -> SAM mask -> principal axis)
  size_error   product_ratio / the same ratio in the gray render (orange mask) - 1
  hair_end     where the hair ends, in head heights from the top of the head (tools/hair_length.py), plus the
               nearest body landmark; hair_cropped = the hair leaves the frame, so hair_end is a lower bound
  hair_error   hanging hair length / the target length - 1, when the case gives "hair_target" (head heights)

Needs mediapipe (in the server venv) and transformers (Grounding DINO, SAM). MediaPipe task models
are read from SCENE_QA_MODELS (pose.task, face.task, selfie_multiclass.tflite); extra Python packages from SCENE_QA_PYLIBS.
"""

import json
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

if os.environ.get("SCENE_QA_PYLIBS"):
    sys.path.append(os.environ["SCENE_QA_PYLIBS"])
import mediapipe as mp  # noqa: E402
import torch  # noqa: E402
from mediapipe.tasks.python import BaseOptions, vision  # noqa: E402
from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor, SamModel, SamProcessor  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_length  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.environ.get("SCENE_QA_MODELS", ".")
DEV = "cuda" if torch.cuda.is_available() else "cpu"
QUERY = {"auto_curler": "a curling iron.", "thermal_brush": "a round hair brush.",
         "style_switch": "a hair styling tool.", "flat_iron": "a hair straightener."}
BODY = [0, 11, 12, 13, 14, 15, 16, 23, 24, 7, 8, 9, 10]  # nose, shoulders, elbows, wrists, hips, ears, mouth

pose_lm = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(MODELS, "pose.task")), num_poses=1))
face_lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(MODELS, "face.task")), num_faces=1))
segmenter = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
    base_options=BaseOptions(model_asset_path=os.path.join(MODELS, "selfie_multiclass.tflite")), output_category_mask=True))
gd_proc = AutoProcessor.from_pretrained("IDEA-Research/grounding-dino-base")
gd = AutoModelForZeroShotObjectDetection.from_pretrained("IDEA-Research/grounding-dino-base").to(DEV)
sam_proc = SamProcessor.from_pretrained("facebook/sam-vit-base")
sam = SamModel.from_pretrained("facebook/sam-vit-base").to(DEV)


def load(path, side=1024):
    im = Image.open(os.path.join(ROOT, path)).convert("RGB")
    im.thumbnail((side, side))
    return im


def landmarks(im):
    m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im))
    p = pose_lm.detect(m)
    f = face_lm.detect(m)
    body = np.array([[l.x, l.y] for l in p.pose_landmarks[0]]) if p.pose_landmarks else None
    face = np.array([[l.x * im.width, l.y * im.height] for l in f.face_landmarks[0]]) if f.face_landmarks else None
    return body, face


def hair_mask(im):
    """Hair pixels (class 1 of the selfie multiclass segmenter), only the blobs attached to the head mass."""
    m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im))
    mask = np.squeeze(segmenter.segment(m).category_mask.numpy_view()) == 1
    lab, n = ndimage.label(mask)
    if n == 0:
        return None
    sizes = ndimage.sum(mask, lab, range(1, n + 1))
    return np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 0.05 * sizes.max()])


def hair(im, face, case):
    hm = hair_mask(im)
    r = hair_length.measure(hm, face, im.height)
    if "hair_end" in r and case.get("hair_target"):
        d = hair_length.DRAPE
        r["hair_target"] = case["hair_target"]
        r["hair_error"] = round((r["hair_end"] + d) / (case["hair_target"] + d) - 1, 2)
    if hm is not None:
        vis = np.asarray(im).copy()
        vis[hm] = (0.5 * vis[hm] + 0.5 * np.array([0, 160, 255])).astype(np.uint8)
        os.makedirs(os.path.join(ROOT, "outputs", "qa"), exist_ok=True)
        Image.fromarray(vis).save(os.path.join(ROOT, "outputs", "qa", case["id"] + "_hair.jpg"), quality=80)
    return r


def eye_dist(face):
    # outer eye corners 33 / 263, in pixels
    return float(np.linalg.norm(face[33] - face[263])), face[[33, 263]].mean(0)


def solid(mask, rel=0.35):
    """Drop parts much thinner than the product body (the cable) and keep the largest blob.

    Opening with a disk whose radius is a fraction of the mask's own maximum half-thickness, so a thin
    barrel survives while a cable (a few px wide) goes."""
    if mask is None or not mask.any():
        return mask
    dist = ndimage.distance_transform_edt(mask)
    r = max(1.5, rel * float(dist.max()))
    m = (ndimage.distance_transform_edt(~(dist > r)) <= r) & mask
    lab, n = ndimage.label(m)
    if n == 0:
        return m
    # hair wrapped around a barrel splits the product into pieces: keep every large piece, not only the biggest
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    keep = [i + 1 for i, s in enumerate(sizes) if s >= 0.12 * sizes.max()]
    return np.isin(lab, keep)


def elongation(mask):
    length = axis_length(mask)
    return (length ** 2 / mask.sum()) if length else 0


def axis_length(mask):
    ys, xs = np.nonzero(mask)
    if len(xs) < 50:
        return None
    pts = np.stack([xs, ys], 1).astype(float)
    pts -= pts.mean(0)
    v = np.linalg.svd(pts, full_matrices=False)[2][0]
    proj = pts @ v
    return float(np.percentile(proj, 99.5) - np.percentile(proj, 0.5))


def orange_mask(im):
    # the proxy is #FF6A00 under studio light: hue 10-40 deg, saturated; the clay body and hair are gray
    hsv = np.asarray(im.convert("HSV")).astype(int)
    return (hsv[..., 0] >= 7) & (hsv[..., 0] <= 28) & (hsv[..., 1] > 110) & (hsv[..., 2] > 90)


def product_mask(im, sku):
    inp = gd_proc(images=im, text=QUERY[sku], return_tensors="pt").to(DEV)
    with torch.no_grad():
        out = gd(**inp)
    res = gd_proc.post_process_grounded_object_detection(out, inp.input_ids, threshold=0.25, text_threshold=0.2,
                                                         target_sizes=[im.size[::-1]])[0]
    if len(res["boxes"]) == 0:
        return None, None
    box = res["boxes"][int(res["scores"].argmax())].tolist()
    si = sam_proc(im, input_boxes=[[box]], return_tensors="pt").to(DEV)
    with torch.no_grad():
        so = sam(**si)
    masks = sam_proc.image_processor.post_process_masks(so.pred_masks.cpu(), si["original_sizes"].cpu(), si["reshaped_input_sizes"].cpu())[0]
    # of SAM's 3 proposals keep the most elongated one: a hand or arm merged with the product is stubbier
    cands = [solid(masks[0, k].numpy()) for k in range(masks.shape[1])]
    cands = [c for c in cands if c is not None and c.sum() > 400]
    if not cands:
        return None, box
    return max(cands, key=elongation), box


def measure(case):
    o = load(case["out"])
    ob, of = landmarks(o)
    r = {"id": case["id"]}
    r.update(hair(o, of, case))
    if not case.get("gray"):
        return r
    g = load(case["gray"])
    gb, gf = landmarks(g)
    if gb is not None and ob is not None:
        r["pose_drift"] = round(float(np.linalg.norm(gb[BODY] - ob[BODY], axis=1).mean() * 100), 1)
    if gf is not None and of is not None:
        ge, gc = eye_dist(gf)
        oe, oc = eye_dist(of)
        r["face_scale"] = round(oe / ge, 2)
        r["face_shift"] = round(float(np.linalg.norm(gc / g.size - oc / o.size) * 100), 1)
        gm = solid(orange_mask(g))
        gl = axis_length(gm)
        if gm is not None and gm.any():
            vis = np.asarray(g).copy()
            vis[gm] = (0.4 * vis[gm] + 0.6 * np.array([0, 220, 0])).astype(np.uint8)
            os.makedirs(os.path.join(ROOT, "outputs", "qa"), exist_ok=True)
            Image.fromarray(vis).save(os.path.join(ROOT, "outputs", "qa", case["id"] + "_gray_mask.jpg"), quality=80)
        m, box = product_mask(o, case["sku"])
        ol = axis_length(m) if m is not None else None
        if gl and ol:
            r["gray_ratio"] = round(gl / ge, 2)
            r["product_ratio"] = round(ol / oe, 2)
            r["size_error"] = round(ol / oe / (gl / ge) - 1, 2)
        if m is not None:
            vis = np.asarray(o).copy()
            vis[m] = (0.5 * vis[m] + 0.5 * np.array([255, 0, 200])).astype(np.uint8)
            os.makedirs(os.path.join(ROOT, "outputs", "qa"), exist_ok=True)
            Image.fromarray(vis).save(os.path.join(ROOT, "outputs", "qa", case["id"] + "_mask.jpg"), quality=80)
    return r


def main():
    cases = json.load(open(sys.argv[1], encoding="utf-8"))
    res = []
    for c in cases:
        r = measure(c)
        print(r, flush=True)
        res.append(r)
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
