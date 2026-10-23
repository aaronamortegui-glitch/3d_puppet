"""Build library/ (approved, reusable generation inputs) from samples/.

    server\\.venv\\Scripts\\python.exe tools\\build_library.py

Copies, never moves: samples/ keeps every experiment and the scripts that write there keep working.
Sources are listed in tools/library_manifest.json (products, poses) and docs/products/product_hair_rules.json
(what each product does to each hair type). library/ is rebuilt from scratch on every run, except avatars/.

library/
  products/<sku>/<colour>/      card.png, card_clean.png, hand.png, packshots/
  poses/<category>/<sku>/<id>/  reference.*, gray.png, pose.txt, meta.json   (category: in_use, in_hand)
  hair_styles/_before/type<n>/  swatch_before.png, back_before.png
  hair_styles/<sku>/type<n>/<key>/  swatch_after.png, back_after.png, rule.json
  rules/product_hair_rules.json
  avatars/<avatar_id>/          front, three_quarter, profile, back + meta.json (filled by hand, kept across rebuilds)
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
POSE_DETAILS = json.load(open(os.path.join(ROOT, "tools", "pose_details.json"), encoding="utf-8"))
STYLES = os.path.join(SAMPLES, "products", "style_library")

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
        out = os.path.join(LIB, "poses", po["category"], po["sku"], po["id"])
        ref = os.path.join(SAMPLES, po["reference"])
        copy(ref, os.path.join(out, "reference" + os.path.splitext(ref)[1]))
        gray = os.path.join(SAMPLES, po["gray"]) if "gray" in po else os.path.join(POSE_GRAY, po["id"] + ".png")
        copy(gray, os.path.join(out, "gray.png"))
        if po["id"] in POSE_DETAILS:
            open(os.path.join(out, "pose.txt"), "w", encoding="utf-8").write(POSE_DETAILS[po["id"]] + "\n")
        else:
            missing.append(f"pose details for {po['id']} (tools/pose_details.json)")
        json.dump(po, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=2)


def hair_styles(rules):
    for t in "1234":
        out = os.path.join(LIB, "hair_styles", "_before", f"type{t}")
        copy(os.path.join(STYLES, "swatches", f"before_t{t}.png"), os.path.join(out, "swatch_before.png"))
        copy(os.path.join(STYLES, "backview", f"before_t{t}.png"), os.path.join(out, "back_before.png"))
    for r in rules["rules"]:
        if not r["allowed"]:
            continue
        out = os.path.join(LIB, "hair_styles", r["sku"], f"type{r['hair_type']}", r["key"])
        copy(os.path.join(STYLES, "swatches", r["key"] + ".png"), os.path.join(out, "swatch_after.png"))
        copy(os.path.join(STYLES, "backview", r["key"] + ".png"), os.path.join(out, "back_after.png"))
        json.dump(r, open(os.path.join(out, "rule.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    rules = json.load(open(RULES, encoding="utf-8"))
    for sub in ("products", "poses", "hair_styles", "rules"):
        shutil.rmtree(os.path.join(LIB, sub), ignore_errors=True)
    os.makedirs(os.path.join(LIB, "avatars"), exist_ok=True)
    products(m)
    poses(m)
    hair_styles(rules)
    copy(RULES, os.path.join(LIB, "rules", "product_hair_rules.json"))
    counts = {sub: sum(len(f) for _, _, f in os.walk(os.path.join(LIB, sub))) for sub in ("products", "poses", "hair_styles", "rules", "avatars")}
    print("files:", counts)
    print(f"missing ({len(missing)}):")
    for f in missing:
        print("  ", f)


if __name__ == "__main__":
    main()
