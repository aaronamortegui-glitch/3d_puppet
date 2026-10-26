"""Measures how much the hair really changes in the real before/after references (grade A, docs/products/hair_refs.json).

Per reference, from the MediaPipe hair mask of split/<id>_before.png and split/<id>_after.png:
  width_ratio   widest hair row after / before (volume), in face widths when a face is found, else in image widths
  length_ratio  hair end after / before, in head heights from the top of the head when a face is found,
                else hair height / image height (back views: the pair shares the framing)
Writes the median per SKU slot into docs/products/hair_change.json; fill_prompt.py uses it so the after keeps
the real change of volume and length, never more and never less than the real photos show.
Usage: SCENE_QA_MODELS=<dir> server/.venv/Scripts/python.exe tools/measure_ref_change.py outputs/10_hair_refs
"""
import json
import os
import statistics
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from add_client_avatars import mediapipe_tools  # noqa: E402

HEAD_PER_FACE = 1.35  # head height / chin-to-brow distance, as in hair_length.measure


def stats(seg, path):
    im = Image.open(path).convert("RGB")
    im.thumbnail((1024, 1024))
    mask, face = seg(im)
    if mask is None or mask.sum() < 500:
        return None
    rows = np.nonzero(mask.any(axis=1))[0]
    width = float(np.percentile(mask.sum(axis=1)[rows], 95))
    out = {"has_face": face is not None}
    if face is not None:
        fw = float(face[:, 0].max() - face[:, 0].min())
        head = HEAD_PER_FACE * float(np.linalg.norm(face[152] - face[10]))
        top = face[152][1] - head
        out["width"] = width / fw
        out["end"] = (float(np.percentile(rows, 99.5)) - top) / head
    else:
        out["width"] = width / im.width
        out["end"] = (rows.max() - rows.min()) / im.height
    return out


def main(base):
    seg = mediapipe_tools(raw=True)
    doc = json.load(open("docs/products/hair_refs.json", encoding="utf-8"))
    per_ref, per_slot = {}, {}
    for r in doc["refs"]:
        if r["grade"] != "A":
            continue
        b = stats(seg, os.path.join(base, "split", f"{r['id']}_before.png"))
        a = stats(seg, os.path.join(base, "split", f"{r['id']}_after.png"))
        if not a or not b or a["has_face"] != b["has_face"]:
            per_ref[r["id"]] = {"skipped": "no hair mask or face in only one of the pair"}
            continue
        m = {"width_ratio": round(a["width"] / b["width"], 2), "length_ratio": round(a["end"] / b["end"], 2),
             "by": "face" if a["has_face"] else "frame"}
        per_ref[r["id"]] = m
        per_slot.setdefault(r["sku"], []).append(m)
    slots = {k: {"width_ratio": round(statistics.median(x["width_ratio"] for x in v), 2),
                 "length_ratio": round(statistics.median(x["length_ratio"] for x in v), 2), "n": len(v)}
             for k, v in per_slot.items()}
    out = {"_note": "Real change of hair volume (width) and length from before to after, measured on the grade A real "
                    "references (tools/measure_ref_change.py). 1.0 = unchanged.", "slots": slots, "refs": per_ref}
    json.dump(out, open("docs/products/hair_change.json", "w", encoding="utf-8"), indent=1)
    print(json.dumps(slots, indent=1))
    for k, v in per_ref.items():
        print(k, v)


if __name__ == "__main__":
    main(sys.argv[1])
