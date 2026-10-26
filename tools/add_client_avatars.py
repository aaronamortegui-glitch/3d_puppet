"""Adds the 10 client avatars (new_client/Avatars - After, A01-A10) to library/avatars/.

Copies front.png, measures where the hair ends (tools/scene_qa.py, MediaPipe on the photo) and writes
meta.json with the hair tags read by eye. library/avatars/ is kept across build_library.py rebuilds.
Usage: python tools/add_client_avatars.py "E:/Superside/3d_puppet/new_client/Avatars - After"
"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import hair_length  # noqa: E402

# id, source file, hair type, subtype, colour, skin, volume, body, note
AVATARS = [
    ("client_a01_bob_black", "A01_seedream_a_zimage.png", "2", "2A", "black", "light, East Asian", "medium", "slim", "jaw-length choppy bob"),
    ("client_a02_coily", "A02_seedream_b_zimage.png", "4", "4B", "black", "deep", "big", "slim", "rounded afro, short"),
    ("client_a03_red_wavy", "A03_orig_zimage.png", "2", "2B", "copper red", "fair, freckles", "medium", "slim", "long, past the chest"),
    ("client_a04_wavy_dark", "A04_orig_zimage.png", "2", "2C", "dark brown", "medium, tan", "big", "average", "shoulder to chest, defined S-waves"),
    ("client_a05_long_curly", "A05_seedream_a_zimage.png", "3", "3A", "black-brown", "brown, South Asian", "big", "slim", "very long, to the waist"),
    ("client_a06_platinum", "A06_seedream_a_zimage.png", "1", "1", "platinum blonde, dark roots", "light", "medium", "slim", "lob, slight bend at the ends"),
    ("client_a07_burgundy_curls", "A07_orig_zimage.png", "3", "3B", "burgundy red", "light brown", "big", "slim", "shoulder-length ringlets"),
    ("client_a08_shag_bangs", "A08_seedream_b_zimage.png", "2", "2A", "warm brown", "light", "medium", "slim", "layered shag with curtain bangs"),
    ("client_a09_blonde_straight", "A09_seedream_b_zimage.png", "1", "1", "dark blonde", "fair", "low", "average", "shoulder to collarbone"),
    ("client_a10_long_curly", "A10_seedream_b_zimage.png", "3", "3B", "black", "medium brown", "big", "slim", "long, to the waist"),
]


def mediapipe_tools():
    """Face mesh and hair mask, the same models and mask rule as scene_qa.py (without its DINO/SAM imports)."""
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks.python import BaseOptions, vision
    from PIL import Image
    from scipy import ndimage
    models = os.environ.get("SCENE_QA_MODELS", ".")
    face_lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(models, "face.task")), num_faces=1))
    seg = vision.ImageSegmenter.create_from_options(vision.ImageSegmenterOptions(
        base_options=BaseOptions(model_asset_path=os.path.join(models, "selfie_multiclass.tflite")), output_category_mask=True))

    def run(path):
        im = Image.open(path).convert("RGB")
        im.thumbnail((1024, 1024))
        m = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.asarray(im))
        f = face_lm.detect(m)
        face = np.array([[p.x * im.width, p.y * im.height] for p in f.face_landmarks[0]]) if f.face_landmarks else None
        mask = np.squeeze(seg.segment(m).category_mask.numpy_view()) == 1
        lab, n = ndimage.label(mask)
        if n:
            sizes = ndimage.sum(mask, lab, range(1, n + 1))
            mask = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s >= 0.05 * sizes.max()])
        return hair_length.measure(mask if n else None, face, im.height)
    return run


def main(src):
    measure = mediapipe_tools()
    lib = os.path.join(os.path.dirname(__file__), "..", "library", "avatars")
    for aid, fn, t, sub, colour, skin, vol, body, note in AVATARS:
        d = os.path.join(lib, aid)
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(src, fn), os.path.join(d, "front.png"))
        m = measure(os.path.join(d, "front.png"))
        meta = {
            "status": "client avatar (new_client/Avatars - After), 2026-10-26",
            "source_file": fn,
            "hair_type": t, "hair_subtype": sub, "hair_colour": colour, "skin": skin,
            "hair_end": m.get("hair_end"), "hair_end_landmark": m.get("hair_landmark"),
            "hair_end_note": "measured on front.png by tools/scene_qa.py; a lower bound when the hair leaves the frame"
                             + (" (it does here)" if m.get("hair_cropped") else ""),
            "hair_volume": vol, "body": body, "note": note,
        }
        with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        print(aid, meta["hair_subtype"], meta["hair_end"], meta["hair_end_landmark"], m.get("hair_cropped"))


if __name__ == "__main__":
    main(sys.argv[1])
