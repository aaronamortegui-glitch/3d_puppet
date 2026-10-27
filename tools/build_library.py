"""Build library/ (approved, reusable generation inputs) from samples/.

    server\\.venv\\Scripts\\python.exe tools\\build_library.py

Copies, never moves: samples/ keeps every experiment and the scripts that write there keep working.
Sources are listed in tools/library_manifest.json (products, poses) and docs/products/product_hair_rules.json
(what each product does to each hair type). library/ is rebuilt from scratch on every run, except avatars/.

library/
  products/<sku>/<colour>/      card.png, card_clean.png (the product sheet, model input), hand.png, packshots/
  poses/<category>/<sku>/<id>/  reference.*, gray.png, pose.txt, meta.json   (category: in_use, in_hand;
                                meta.json carries the sculpted-hair tags from tools/pose_hair.json)
  poses/_rejected/<category>/<sku>/<id>/   poses that do not work (tools/pose_status.json), kept for the record
  hair_styles/<sku_slot>/<rule>/<ref_id>/  lock.png, after.png, before.png, ref.json: the real grade A references
                                (docs/products/hair_refs.json, outputs/10_hair_refs); the style input
  hair_styles_generated_v1/     the old generated swatches and back-view heads; no longer used as input
  rules/                        product_hair_rules.json, hair_refs.json, looks_by_product.json
  prompts/                      the prompt templates (prompts/conair/)
  avatars/<avatar_id>/          front.png + meta.json (filled by hand, kept across rebuilds); client_* are the
                                current avatars, avatars/_archive/ holds the earlier ones
"""

import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES = os.path.join(ROOT, "samples")
LIB = os.path.join(ROOT, "library")
MANIFEST = os.path.join(ROOT, "tools", "library_manifest.json")
RULES = os.path.join(ROOT, "docs", "products", "product_hair_rules.json")
# gray renders (A1) are generated per pose into samples/; pose details (A2) are text, kept in git
POSE_GRAY = os.path.join(SAMPLES, "pose_library", "gray")
POSE_GRAY_V2 = os.path.join(SAMPLES, "pose_library", "gray_v2")
POSE_GRAY_LENGTHS = os.path.join(SAMPLES, "pose_library", "gray_length_variants")
POSE_DETAILS = json.load(open(os.path.join(ROOT, "tools", "pose_details.json"), encoding="utf-8"))
# sculpted hair of each gray render (length, texture, volume, body), used by tools/pick_pose.py
POSE_HAIR = json.load(open(os.path.join(ROOT, "tools", "pose_hair.json"), encoding="utf-8"))["poses"]
STYLES = os.path.join(SAMPLES, "products", "style_library")
REJECTED = json.load(open(os.path.join(ROOT, "tools", "pose_status.json"), encoding="utf-8"))["rejected"]
HAIR_REFS = os.path.join(ROOT, "docs", "products", "hair_refs.json")
REF_FILES = os.path.join(ROOT, "outputs", "10_hair_refs")
PROMPTS = os.path.join(ROOT, "prompts", "conair")

missing = []


def copy(src, dst):
    if not os.path.exists(src):
        missing.append(os.path.relpath(src, ROOT))
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def products(m):
    for sku, p in m["products"].items():
        for colour, c in p["colours"].items():
            out = os.path.join(LIB, "products", sku, colour)
            copy(os.path.join(SAMPLES, c["card"]), os.path.join(out, "card.png"))
            copy(os.path.join(SAMPLES, c["card_clean"]), os.path.join(out, "card_clean.png"))
            copy(os.path.join(SAMPLES, c["hand"]), os.path.join(out, "hand.png"))
            for f in c["packshots"]:
                copy(os.path.join(SAMPLES, f), os.path.join(out, "packshots", os.path.basename(f)))
            meta = {"sku": sku, "colour": colour, "model": c.get("model", p["model"]), "sources": c}
            json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=2)


def poses(m):
    for po in m["poses"]:
        out = os.path.join(LIB, "poses", *(["_rejected"] if po["id"] in REJECTED else []), po["category"], po["sku"], po["id"])
        ref =os.path.join(SAMPLES, po["reference"])
        copy(ref, os.path.join(out, "reference" + os.path.splitext(ref)[1]))
        gray = os.path.join(SAMPLES, po["gray"]) if "gray" in po else os.path.join(POSE_GRAY, po["id"] + ".png")
        v2 = os.path.join(POSE_GRAY_V2, po["id"] + ".png")
        if os.path.exists(v2):  # neutral moderate hair (test 13): the v2 render is the input, the first one is kept
            copy(gray, os.path.join(out, "gray_v1.png"))
            gray = v2
        copy(gray, os.path.join(out, "gray.png"))
        for length in ("short", "long"):  # sculpted-hair length variants (test 18); gray.png is the medium one
            var = os.path.join(POSE_GRAY_LENGTHS, f"{po['id']}__{length}.png")
            if os.path.exists(var):
                copy(var, os.path.join(out, f"gray_{length}.png"))
        if po["id"] in POSE_DETAILS:
            open(os.path.join(out, "pose.txt"), "w", encoding="utf-8").write(POSE_DETAILS[po["id"]] + "\n")
        else:
            missing.append(f"pose details for {po['id']} (tools/pose_details.json)")
        if po["id"] not in POSE_HAIR:
            missing.append(f"sculpted hair tags for {po['id']} (tools/pose_hair.json)")
        meta = {**po, **POSE_HAIR.get(po["id"], {})}
        if po["id"] in REJECTED:
            meta["rejected"] = REJECTED[po["id"]]
        json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=2)


def real_hair_styles():
    """The style input: grade A real references, one folder per reference, under the SKU slot and rule."""
    doc = json.load(open(HAIR_REFS, encoding="utf-8"))
    for r in doc["refs"]:
        if r["grade"] != "A":
            continue
        out = os.path.join(LIB, "hair_styles", r["sku"], r["rule"], r["id"])
        copy(os.path.join(REF_FILES, "locks", f"{r['id']}_lock.png"), os.path.join(out, "lock.png"))
        copy(os.path.join(REF_FILES, "split", f"{r['id']}_after.png"), os.path.join(out, "after.png"))
        copy(os.path.join(REF_FILES, "split", f"{r['id']}_before.png"), os.path.join(out, "before.png"))
        json.dump(r, open(os.path.join(out, "ref.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def hair_styles(rules):
    """The old generated swatches and back-view heads, kept for the record; no longer an input."""
    for t in "1234":
        out = os.path.join(LIB, "hair_styles_generated_v1", "_before", f"type{t}")
        copy(os.path.join(STYLES, "swatches", f"before_t{t}.png"), os.path.join(out, "swatch_before.png"))
        copy(os.path.join(STYLES, "backview", f"before_t{t}.png"), os.path.join(out, "back_before.png"))
    for r in rules["rules"]:
        if not r["allowed"]:
            continue
        out = os.path.join(LIB, "hair_styles_generated_v1", r["sku"], f"type{r['hair_type']}", r["key"])
        copy(os.path.join(STYLES, "swatches", r["key"] + ".png"), os.path.join(out, "swatch_after.png"))
        copy(os.path.join(STYLES, "backview", r["key"] + ".png"), os.path.join(out, "back_after.png"))
        json.dump(r, open(os.path.join(out, "rule.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    rules = json.load(open(RULES, encoding="utf-8"))
    subs = ("products", "poses", "hair_styles", "hair_styles_generated_v1", "rules", "prompts")
    for sub in subs:
        shutil.rmtree(os.path.join(LIB, sub), ignore_errors=True)
    os.makedirs(os.path.join(LIB, "avatars"), exist_ok=True)
    products(m)
    poses(m)
    real_hair_styles()
    hair_styles(rules)
    copy(RULES, os.path.join(LIB, "rules", "product_hair_rules.json"))
    copy(HAIR_REFS, os.path.join(LIB, "rules", "hair_refs.json"))
    copy(os.path.join(ROOT, "docs", "products", "looks_by_product.json"), os.path.join(LIB, "rules", "looks_by_product.json"))
    shutil.copytree(PROMPTS, os.path.join(LIB, "prompts"))
    counts = {sub: sum(len(f) for _, _, f in os.walk(os.path.join(LIB, sub))) for sub in subs + ("avatars",)}
    print("files:", counts)
    print(f"missing ({len(missing)}):")
    for f in missing:
        print("  ", f)


if __name__ == "__main__":
    main()
