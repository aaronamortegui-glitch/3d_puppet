"""Hair length that stays proportional across scenes.

A styled curl gains or loses visible length in proportion to its shrinkage: visible = stretched x (1 - shrinkage).
So for one avatar  after_visible / before_visible = (1 - after_shrinkage) / (1 - before_shrinkage),
with before_shrinkage from her curl pattern and after_shrinkage from the rule's result style
(docs/products/product_hair_rules.json -> "hair_length" and each rule's "after_shrinkage").

Length unit: head heights (top of the head to the chin) measured from the top of the head, so it is the
same whatever the framing. The hanging strand is longer than that by the drape over the skull (DRAPE).

    target(avatar_meta, rule, rules_doc) -> {"before", "after", "factor", "before_landmark", "after_landmark"}
    prompt_line(target)                  -> sentence for the prompt
    measure(image, face_landmarks)       -> {"hair_end", "hair_landmark", "hair_cropped"}  (used by scene_qa.py)
"""

import json
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES = os.path.join(ROOT, "docs", "products", "product_hair_rules.json")
DRAPE = 0.3  # head heights of hair lying over the skull before it starts to hang
HEAD_PER_FACE = 1.3  # head height / face-mesh forehead(10)-to-chin(152) distance


def load_rules():
    return json.load(open(RULES, encoding="utf-8"))


def landmarks(doc=None):
    doc = doc or load_rules()
    return doc["hair_length"]["landmarks"]


def nearest(value, doc=None):
    """Name of the body landmark closest to a length in head heights."""
    lm = landmarks(doc)
    return min(lm, key=lambda l: abs(l["at"] - value))["name"]


def landmark_value(name, doc=None):
    for l in landmarks(doc):
        if l["name"] == name:
            return l["at"]
    raise KeyError(name)


def shrinkage(subtype, doc=None):
    doc = doc or load_rules()
    table = doc["hair_length"]["shrinkage"]
    return table.get(subtype, table.get(subtype[:1]))


def target(avatar, rule, doc=None):
    """avatar: meta.json dict with hair_subtype ("3C") and hair_end (head heights) or hair_end_landmark."""
    doc = doc or load_rules()
    before = avatar.get("hair_end") or landmark_value(avatar["hair_end_landmark"], doc)
    s0 = shrinkage(avatar["hair_subtype"], doc)
    s1 = rule.get("after_shrinkage")
    s1 = s0 if s1 is None else s1  # styles that keep the curl pattern (diffuser) keep the length
    factor = (1 - s1) / (1 - s0)
    after = (before + DRAPE) * factor - DRAPE
    return {"before": round(before, 2), "after": round(after, 2), "factor": round(factor, 2),
            "before_landmark": nearest(before, doc), "after_landmark": nearest(after, doc)}


def prompt_line(t, in_progress=False):
    """in_progress: an in-use shot, where only the sections already styled have the new length."""
    amount = ("HAIR AMOUNT: exactly the same amount and density of hair as in her before photo: no added volume, no extensions, "
              "no extra hair, realistic volume (never fuller than in her before photo unless the style itself adds root lift); "
              "any change of length comes only from stretching or curling her own hair.")
    if in_progress and abs(t["factor"] - 1) >= 0.06:
        return (f"HAIR LENGTH: the sections not styled yet keep her natural texture and end at the {t['before_landmark']}, as in her before photo; "
                f"the sections already styled end at the {t['after_landmark']}. " + amount)
    if abs(t["factor"] - 1) < 0.06:
        change = "the SAME length as in her before photo"
    elif t["factor"] > 1:
        change = f"about {round((t['factor'] - 1) * 100)}% longer than in her before photo, because the curl pattern is stretched out"
    else:
        change = f"about {round((1 - t['factor']) * 100)}% shorter than in her before photo, because the curls take up length"
    return (f"HAIR LENGTH: her hair now ends at the {t['after_landmark']} (before: at the {t['before_landmark']}); "
            f"it is {change}. Keep exactly this length; do not make it longer or shorter. " + amount)


def measure(hair_mask, face, height):
    """hair_mask: bool HxW; face: face-mesh landmarks in pixels; height: image height in px."""
    out = {}
    if face is None or hair_mask is None or hair_mask.sum() < 500:
        return out
    chin, brow = face[152], face[10]
    head = HEAD_PER_FACE * float(np.linalg.norm(chin - brow))
    top = chin[1] - head
    ys = np.nonzero(hair_mask)[0]
    end = float(np.percentile(ys, 99.5))
    out["hair_end"] = round((end - top) / head, 2)
    out["hair_landmark"] = nearest(out["hair_end"])
    out["hair_cropped"] = bool(end > height * 0.985)  # hair leaves the frame: hair_end is a lower bound
    return out
