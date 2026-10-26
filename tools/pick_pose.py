"""Pick in-use poses whose sculpted hair matches the avatar's hair, the way the rules pick the style.

    python tools/pick_pose.py <avatar_id> <rule_key>     ranked poses for that rule's SKU
    python tools/pick_pose.py --matrix                   best pose per avatar x SKU (allowed rules only)

The gray render's sculpted hair leaks into the output (test 6: a curly mane on a coily avatar, a short bob on a
long-haired one), so a pose is only as good as the match between its hair and hers. Per pose (tools/pose_hair.json):
  length   |pose end - her end| in head heights, against her BEFORE length: in an in-use shot most of the hair is
           still unstyled, so the mass of hair must be hers (test 6: matching the styled length let the coily avatar
           through on a long curly mane); when the pose's hair leaves the frame its end is a lower bound, so only a
           pose that shows MORE hair than she has is penalised
  texture  curl-type distance to the nearer of her natural pattern and the rule's result style
           (in-use shots are mid-process, so the sculpted hair may show either)
  volume   flat / medium / big, one step = 1
  body     a curvy sculpted body on a slim avatar (or the reverse) changes her body (test 4)
  view     front and three-quarter are preferred; profile and back views break identity and hair more often
           (review 2026-10-23): profile 0.6, back 1.2
score = length + 0.6 texture + 0.5 volume + 0.5 body + view; ok < 0.6, check < 1.2, avoid above. Pose notes (e.g. the
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
REJECTED = json.load(open(os.path.join(ROOT, "tools", "pose_status.json"), encoding="utf-8"))["rejected"]


def avatar_meta(avatar_id):
    """library/avatars/<id>/meta.json, or the earlier avatars kept in library/avatars/_archive/."""
    for d in (AVATARS, os.path.join(AVATARS, "_archive")):
        f = os.path.join(d, avatar_id, "meta.json")
        if os.path.exists(f):
            return json.load(open(f, encoding="utf-8"))
    raise FileNotFoundError(f"no avatar {avatar_id} in library/avatars")
VOLUME = {"flat": 0, "medium": 1, "big": 2}
DEFAULT_VOLUME = {"1": "flat", "2": "medium", "3": "big", "4": "big"}
VIEW = {"front": 0.0, "three_quarter": 0.0, "profile": 0.6, "back": 1.2}
SUB = ["1", "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C"]


def curl(subtype):
    """Curl subtype on a line: 1 -> 1.0, 2A -> 2.0, 2B -> 2.33 ... 4C -> 4.67."""
    if subtype == "1" or subtype.startswith("1"):
        return 1.0
    return int(subtype[0]) + "ABC".index(subtype[1:2] or "B") / 3


def result_curl(rule, avatar, doc):
    """Curl type of the rule's result style: after_texture when the rule sets it (straightening and blowouts),
    else from its shrinkage (the nearest subtype with that shrinkage)."""
    if rule.get("after_texture"):
        return curl(rule["after_texture"])
    s = rule.get("after_shrinkage")
    if s is None:
        return curl(avatar["hair_subtype"])
    table = doc["hair_length"]["shrinkage"]
    return curl(min(SUB, key=lambda t: abs(table[t] - s)))


def score(pose, avatar, rule, doc, finished=False):
    """finished=True: the shot shows the finished style (the in-use template), so the sculpted hair must match
    the AFTER: its texture and its length. Test 11: wavy sculpted hair beat the lock on every straightening rule.
    finished=False: a mid-process shot, where her natural hair (the before) is still most of what shows."""
    h = pose["hair"]
    her_end = avatar.get("hair_end") or HL.landmark_value(avatar["hair_end_landmark"], doc)
    if finished:
        her_end = HL.target(avatar, rule, doc)["after"]
    diff = h["end"] - her_end
    length = max(0.0, diff) if h["cropped"] else abs(diff)
    pc = curl(h["texture"])
    after_curl = result_curl(rule, avatar, doc)
    if finished:
        texture = abs(pc - after_curl)
    else:
        texture = min(abs(pc - curl(avatar["hair_subtype"])), abs(pc - after_curl))
    vol = avatar.get("hair_volume") or DEFAULT_VOLUME[avatar["hair_type"]]
    if finished and rule.get("after_volume"):
        vol = rule["after_volume"]  # straightened hair lies flatter than her natural hair
    volume = abs(VOLUME[h["volume"]] - VOLUME[vol])
    body = 0 if pose.get("body") == avatar.get("body", "slim") else 1
    view = VIEW[pose.get("view", "front")]
    total = length + 0.6 * texture + 0.5 * volume + 0.5 * body + view
    why = []
    if length >= 0.3:
        why.append(f"sculpted hair {'at least ' if h['cropped'] else ''}to the {h['end_landmark']}, hers to the {HL.nearest(her_end, doc)}")
    if texture >= 0.6:
        why.append(f"texture {h['texture']} vs " + (f"the after (curl {after_curl:.1f})" if finished else f"hers {avatar['hair_subtype']}"))
    if volume:
        why.append(f"volume {h['volume']} vs hers {vol}")
    if body:
        why.append(f"{pose.get('body')} body vs her {avatar.get('body', 'slim')} body")
    if view:
        why.append(f"{pose['view']} view (prefer front or three-quarter)")
    return {"score": round(total, 2), "verdict": "ok" if total < 0.6 else "check" if total < 1.2 else "avoid",
            "why": why, "warning": pose.get("note") if pose.get("note") and "proxy" in pose.get("note") else ""}


def rank(avatar_id, rule_key, doc=None, poses=None, finished=False):
    doc = doc or HL.load_rules()
    poses = poses or json.load(open(POSES, encoding="utf-8"))["poses"]
    rule = next(r for r in doc["rules"] if r["key"] == rule_key)
    if not rule["allowed"]:
        raise ValueError(f"{rule_key} is forbidden: {rule['sku']} on type {rule['hair_type']} hair")
    avatar = avatar_meta(avatar_id)
    if avatar["hair_type"] != rule["hair_type"]:
        raise ValueError(f"{rule_key} is for type {rule['hair_type']} hair; {avatar_id} is type {avatar['hair_type']}")
    out = [{"pose": pid, **score(p, avatar, rule, doc, finished)} for pid, p in poses.items()
           if p["category"] == "in_use" and pid.startswith(rule["sku"] + "_") and pid not in REJECTED]
    return sorted(out, key=lambda r: r["score"])


def matrix(finished=False):
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
            best = rank(av, r["key"], doc, poses, finished)[0]
            print(f"  {r['key']:<18} {best['pose']:<26} {best['score']:<5} {best['verdict']:<6} {'; '.join(best['why'])}"
                  + (f"  [!] {best['warning']}" if best["warning"] else ""))


if __name__ == "__main__":
    fin = "--finished" in sys.argv  # in-use shots of the finished style (prompts/conair/01_in_use.txt)
    args = [a for a in sys.argv[1:] if a != "--finished"]
    if args[:1] == ["--matrix"]:
        matrix(fin)
    else:
        for r in rank(args[0], args[1], finished=fin):
            print(f"{r['pose']:<26} {r['score']:<5} {r['verdict']:<6} {'; '.join(r['why'])}" + (f"  [!] {r['warning']}" if r["warning"] else ""))
