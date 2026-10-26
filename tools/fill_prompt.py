"""Fills a prompt template of prompts/conair/ and lists its inputs, in order, as library paths.

    python tools/fill_prompt.py in_use  <avatar_id> <rule> <pose_id> <ref_id> [colour]
    python tools/fill_prompt.py after   <avatar_id> <rule> -         <ref_id>
    python tools/fill_prompt.py in_hand <avatar_id> -      <pose_id> -        [colour]
    python tools/fill_prompt.py soft_env -          -      -         -        [colour] --sku <sku> --set "<set>"

It refuses what the reviews ruled out: a forbidden rule, a rule for another hair type, a rejected pose
(tools/pose_status.json) and a reference that is not grade A (docs/products/hair_refs.json). The HAIR LENGTH
and HAIR AMOUNT lines come from tools/hair_length.py, so the hair never grows or shrinks more than the curl
pattern explains; the pose verdict comes from tools/pick_pose.py.
"""
import argparse
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hair_length as HL  # noqa: E402
import pick_pose  # noqa: E402
import prompt_rules as PR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = {"in_use": "01_in_use.txt", "after": "02_after.txt", "in_hand": "03_in_hand.txt",
             "soft_env": "04_soft_environment.txt"}
SS_BODY = "the slim Style/Switch body from image 3 with its "
PRODUCTS = {
    "auto_curler": {"name": "BaBylissPRO Auto Curler 1-inch automatic rotating curling iron (BNTAC100)",
                    "size": "36.5 cm long overall, barrel 2.5 cm (1 inch) thick and 14 cm long, handle about 3 cm thick"},
    "thermal_brush": {"name": "BaBylissPRO Thermal Round Brush 1¼-inch heated styling brush (BNTHTB125)",
                      "size": "barrel 3.2 cm (1¼ inch) thick, bristle section about 16-17 cm long"},
    "style_switch": {"name": "BaBylissPRO Style/Switch air styler",
                     "size": "body 20 cm long and 5 cm thick, about 34 cm long with the attachment"},
    "flat_iron": {"name": "BaBylissPRO Nano Titanium Ultra-Sleek 1½-inch flat iron (BNT131T)",
                  "size": "plates 3.8 cm (1½ inch) wide and about 14 cm long"},
}
IN_HAND = {  # what replaces the orange proxy, per SKU slot
    "style_switch_paddle": SS_BODY + "PADDLE BRUSH attachment (a flat rectangular cushion brush with black bristles) on top",
    "style_switch_round_brush": SS_BODY + "ROUND BRUSH attachment (black bristles all around a blue-tipped barrel) on top",
    "style_switch_air_curl": SS_BODY + "1½-inch AIR-CURLING BARREL attachment on top, a strand of her hair wrapping around the barrel",
    "style_switch_diffuser": SS_BODY + "blue DIFFUSER attachment (round bowl with prongs) on top",
}


def sku_slot(rule_key):
    k = rule_key
    if k.startswith("AC"):
        return "auto_curler"
    if k.startswith("TB"):
        return "thermal_brush"
    if k.startswith("FI"):
        return "flat_iron"
    for part, slot in (("roundbrush", "style_switch_round_brush"), ("paddle", "style_switch_paddle"),
                       ("aircurl", "style_switch_air_curl"), ("diffuser", "style_switch_diffuser")):
        if part in k:
            return slot
    raise ValueError(f"unknown rule {rule_key}")


TOOL_WORDS = re.compile(r"\b(styler|iron|brush|barrel|tool|hand|plates|curler|attachment|grip|arm|holds|held)\b", re.I)
HAIR_WORDS = re.compile(r"\b(hair|curls?|waves?|wavy|curly|mane|locks?)\b", re.I)
HAIR_ADJ = re.compile(r"\b(voluminous|big|long|medium-length|wavy|curly|straight)\s+(?=(lock of |section of )?(\w+ )?hair)", re.I)
RESULT_TEXTURE = {  # test 11: the sculpted waves of the gray pose beat the lock unless the result is spelled out
    "1": ("RESULT TEXTURE: her hair is now completely straight and sleek from root to tip, with no waves, curls or bends left; "
          "ignore any waves in the sculpted hair of image 1."),
    "2A": ("RESULT TEXTURE: a smooth blowout: straight and polished through the lengths with only a soft bend at the ends; "
           "no waves or curls along the lengths; ignore any waves in the sculpted hair of image 1."),
}


def pose_without_hair(details):
    """Pose details without the sculpted-hair description: a sentence only about hair goes, hair adjectives go.
    The style comes from the lock and the after, never from the pose (test 11)."""
    keep = []
    for sent in re.split(r"(?<=\.)\s+", details.strip()):
        if HAIR_WORDS.search(sent) and not TOOL_WORDS.search(sent):
            continue
        keep.append(HAIR_ADJ.sub("", sent))
    return " ".join(keep)


AMOUNT = ("Same amount and density of hair as in her before photo: no extensions, no extra hair, never fuller or "
          "flatter than the real change shown by the reference pair.")


def hair_change_line(avatar, ref, doc):
    """Length and volume of her after, calibrated on the real before/after of the reference
    (docs/products/hair_change.json, tools/measure_ref_change.py): the same change, never more and never less.
    Falls back to the median of the reference's SKU slot, then to the shrinkage model of hair_length.py."""
    ch = json.load(open(os.path.join(ROOT, "docs", "products", "hair_change.json"), encoding="utf-8"))
    m = ch["refs"].get(ref["id"], {})
    src = f"the real reference pair ({ref['id']}: {ref['before']} -> {ref['after']})"
    if "length_ratio" not in m:
        m, src = ch["slots"].get(ref["sku"], {}), "real before/after photos of this style"
    before = avatar.get("hair_end") or HL.landmark_value(avatar["hair_end_landmark"], doc)
    vol = avatar.get("hair_volume", "medium")
    if "length_ratio" not in m:
        return HL.prompt_line(HL.target(avatar, next(r for r in doc["rules"] if r["key"] == ref["rule"]), doc))
    lr, wr = m["length_ratio"], m["width_ratio"]
    after = before * lr
    length = ("the SAME length as before" if abs(lr - 1) < 0.05 else
              f"about {round(abs(lr - 1) * 100)}% {'longer' if lr > 1 else 'shorter'} than before")
    width = ("the same width and volume as before" if abs(wr - 1) < 0.05 else
             f"about {round(abs(wr - 1) * 100)}% {'wider and fuller' if wr > 1 else 'narrower and flatter'} than before")
    return (f"HAIR LENGTH AND VOLUME, calibrated on {src}, where the real hair kept {round(lr * 100)}% of its length and "
            f"{round(wr * 100)}% of its width: apply exactly the same change to her. Her hair now ends at the "
            f"{HL.nearest(after, doc)} (before: at the {HL.nearest(before, doc)}): {length}; it is {width} "
            f"(before: {vol} volume). " + AMOUNT)


class Keep(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=TEMPLATES)
    ap.add_argument("avatar")
    ap.add_argument("rule")
    ap.add_argument("pose")
    ap.add_argument("ref")
    ap.add_argument("colour", nargs="?", default="nano_blue")
    ap.add_argument("--sku")
    ap.add_argument("--set", default="{set_description}")
    a = ap.parse_args()

    doc = HL.load_rules()
    v = {"HAIR_FROM_AVATAR": PR.HAIR_FROM_AVATAR, "IN_HAND_REAL": PR.IN_HAND_REAL, "STAGING": PR.STAGING,
         "set_description": a.set, "colour": a.colour, "avatar_id": a.avatar, "rule": a.rule,
         "pose_id": a.pose, "ref_id": a.ref}
    notes = []
    sku = a.sku
    if a.rule != "-":
        rule = next((r for r in doc["rules"] if r["key"] == a.rule), None)
        if rule is None or not rule["allowed"]:
            sys.exit(f"{a.rule}: forbidden or unknown rule; see docs/products/product_hair_rules.json")
        sku = rule["sku"]
        v["sku_slot"] = sku_slot(a.rule)
        v["style_result"] = rule["result_style"][0].lower() + rule["result_style"][1:]
        v["result_texture_line"] = RESULT_TEXTURE.get(rule.get("after_texture"), "")
        if a.kind == "after":  # image 1 is her photo here, not a gray render
            v["result_texture_line"] = v["result_texture_line"].replace("; ignore any waves in the sculpted hair of image 1", "")
    if a.avatar != "-":
        av = pick_pose.avatar_meta(a.avatar)
        v["hair_colour"] = av.get("hair_colour", "")
        if a.rule != "-":
            if av["hair_type"] != rule["hair_type"]:
                sys.exit(f"{a.rule} is for type {rule['hair_type']} hair; {a.avatar} is type {av['hair_type']}")
            v["hair_length_line"] = HL.prompt_line(HL.target(av, rule, doc))
    if a.pose != "-":
        if a.pose in pick_pose.REJECTED:
            sys.exit(f"{a.pose} is rejected: {pick_pose.REJECTED[a.pose]}")
        sku = sku or a.pose.split("_in_")[0]
        v["pose_details"] = pose_without_hair(json.load(open(os.path.join(ROOT, "tools", "pose_details.json"), encoding="utf-8"))[a.pose])
        if a.kind == "in_use" and a.avatar != "-":
            r = next(x for x in pick_pose.rank(a.avatar, a.rule, doc, finished=True) if x["pose"] == a.pose)
            notes.append(f"pose verdict: {r['verdict']} ({r['score']}): {'; '.join(r['why'])}")
            if r["verdict"] == "avoid":
                notes.append("pick another pose: python tools/pick_pose.py " + f"{a.avatar} {a.rule} --finished")
    if a.ref != "-":
        refs = {r["id"]: r for r in json.load(open(os.path.join(ROOT, "docs", "products", "hair_refs.json"), encoding="utf-8"))["refs"]}
        ref = refs[a.ref]
        if ref["grade"] != "A":
            sys.exit(f"{a.ref} is grade {ref['grade']}; only grade A references are style inputs")
        v["ref_dir"] = f"{ref['sku']}/{ref['rule']}/{a.ref}"  # a reference can serve a neighbour rule of the same slot
        if a.avatar != "-":
            v["hair_change_line"] = hair_change_line(av, ref, doc)
        if a.rule != "-" and ref["sku"] != v["sku_slot"]:
            notes.append(f"{a.ref} is a {ref['sku']} reference ({ref['rule']}), not {v['sku_slot']}")
    if not sku:
        sys.exit("give a rule, a pose or --sku")
    v["sku"] = sku
    v["product_name"] = PRODUCTS[sku]["name"]
    v["product_size"] = PRODUCTS[sku]["size"]
    v["product_in_hand"] = IN_HAND.get(v.get("sku_slot"), "the product from image 3")

    text = open(os.path.join(ROOT, "prompts", "conair", TEMPLATES[a.kind]), encoding="utf-8").read()
    head, body = text.split("\n---\n", 1)
    print("INPUTS")
    for line in head.splitlines():
        if line.startswith("#   "):
            print("  " + line[4:].format_map(Keep(v)))
    print("\nPROMPT")
    print(body.strip().format_map(Keep(v)))
    for n in notes:
        print("\nNOTE", n)


if __name__ == "__main__":
    main()
