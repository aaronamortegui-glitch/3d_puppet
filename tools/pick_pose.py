"""Pick in-use poses whose sculpted hair matches the avatar's hair, the way the rules pick the style.

    python tools/pick_pose.py <avatar_id> <rule_key>     ranked poses for that rule's SKU
    python tools/pick_pose.py --matrix                   best pose per avatar x SKU (allowed rules only)

The gray render's sculpted hair leaks into the output (test 6: a curly mane on a coily avatar, a short bob on a
long-haired one), so a pose is only as good as the match between its hair and hers. Per pose (tools/pose_hair.json):
  length   |pose end - her end| in head heights, against the nearer of her before length and her styled length
           (tools/hair_length.py target); when the pose's hair leaves the frame its end is a lower bound, so only a
           pose that shows MORE hair than she has is penalised
  texture  curl-type distance to the nearer of her natural pattern and the rule's result style
           (in-use shots are mid-process, so the sculpted hair may show either)
  volume   flat / medium / big, one step = 1
  body     a curvy sculpted body on a slim avatar (or the reverse) changes her body (test 4)
score = length + 0.6 texture + 0.5 volume + 0.5 body; ok < 0.6, check < 1.2, avoid above. Pose notes (e.g. the
orange proxy is another tool) are listed as warnings, not scored.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_length as HL  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSES = os.path.join(ROOT, "tools", "pose_hair.json")
AVATARS = os.path.join(ROOT, "library", "avatars")
VOLUME = {"flat": 0, "medium": 1, "big": 2}
DEFAULT_VOLUME = {"1": "flat", "2": "medium", "3": "big", "4": "big"}
SUB = ["1", "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C"]


def curl(subtype):
    """Curl subtype on a line: 1 -> 1.0, 2A -> 2.0, 2B -> 2.33 ... 4C -> 4.67."""
    if subtype == "1" or subtype.startswith("1"):
        return 1.0
    return int(subtype[0]) + "ABC".index(subtype[1:2] or "B") / 3


def result_curl(rule, avatar, doc):
    """Curl type of the rule's result style, from its shrinkage (the nearest subtype with that shrinkage)."""
    s = rule.get("after_shrinkage")
    if s is None:
        return curl(avatar["hair_subtype"])
    table = doc["hair_length"]["shrinkage"]
    return curl(min(SUB, key=lambda t: abs(table[t] - s)))


def score(pose, avatar, rule, doc):
    h = pose["hair"]
    her_end = avatar.get("hair_end") or HL.landmark_value(avatar["hair_end_landmark"], doc)
    ends = (her_end, HL.target(avatar, rule, doc)["after"])
    length = min(max(0.0, h["end"] - e) if h["cropped"] else abs(h["end"] - e) for e in ends)
    pc = curl(h["texture"])
    texture = min(abs(pc - curl(avatar["hair_subtype"])), abs(pc - result_curl(rule, avatar, doc)))
    vol = avatar.get("hair_volume") or DEFAULT_VOLUME[avatar["hair_type"]]
    volume = abs(VOLUME[h["volume"]] - VOLUME[vol])
    body = 0 if pose.get("body") == avatar.get("body", "slim") else 1
    total = length + 0.6 * texture + 0.5 * volume + 0.5 * body
    why = []
    if length >= 0.3:
        why.append(f"sculpted hair {'at least ' if h['cropped'] else ''}to the {h['end_landmark']}, hers to the {HL.nearest(her_end, doc)}")
    if texture >= 0.6:
        why.append(f"texture {h['texture']} vs hers {avatar['hair_subtype']}")
    if volume:
        why.append(f"volume {h['volume']} vs hers {vol}")
    if body:
        why.append(f"{pose.get('body')} body vs her {avatar.get('body', 'slim')} body")
    return {"score": round(total, 2), "verdict": "ok" if total < 0.6 else "check" if total < 1.2 else "avoid",
            "why": why, "warning": pose.get("note") if pose.get("note") and "proxy" in pose.get("note") else ""}


def rank(avatar_id, rule_key, doc=None, poses=None):
    doc = doc or HL.load_rules()
    poses = poses or json.load(open(POSES, encoding="utf-8"))["poses"]
    rule = next(r for r in doc["rules"] if r["key"] == rule_key)
    if not rule["allowed"]:
        raise ValueError(f"{rule_key} is forbidden: {rule['sku']} on type {rule['hair_type']} hair")
    avatar = json.load(open(os.path.join(AVATARS, avatar_id, "meta.json"), encoding="utf-8"))
    if avatar["hair_type"] != rule["hair_type"]:
        raise ValueError(f"{rule_key} is for type {rule['hair_type']} hair; {avatar_id} is type {avatar['hair_type']}")
    out = [{"pose": pid, **score(p, avatar, rule, doc)} for pid, p in poses.items()
           if p["category"] == "in_use" and pid.startswith(rule["sku"] + "_")]
    return sorted(out, key=lambda r: r["score"])


def matrix():
    doc = HL.load_rules()
    poses = json.load(open(POSES, encoding="utf-8"))["poses"]
    for av in sorted(os.listdir(AVATARS)):
        mf = os.path.join(AVATARS, av, "meta.json")
        if not os.path.exists(mf) or "hair_end" not in json.load(open(mf, encoding="utf-8")):
            continue  # temporary avatars without a measured hair length
        t = json.load(open(mf, encoding="utf-8"))["hair_type"]
        print(f"\n{av} (type {t})")
        for r in doc["rules"]:
            if r["hair_type"] != t:
                continue
            if not r["allowed"]:
                print(f"  {r['key']:<18} FORBIDDEN")
                continue
            best = rank(av, r["key"], doc, poses)[0]
            print(f"  {r['key']:<18} {best['pose']:<26} {best['score']:<5} {best['verdict']:<6} {'; '.join(best['why'])}"
                  + (f"  [!] {best['warning']}" if best["warning"] else ""))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--matrix"]:
        matrix()
    else:
        for r in rank(sys.argv[1], sys.argv[2]):
            print(f"{r['pose']:<26} {r['score']:<5} {r['verdict']:<6} {'; '.join(r['why'])}" + (f"  [!] {r['warning']}" if r["warning"] else ""))
