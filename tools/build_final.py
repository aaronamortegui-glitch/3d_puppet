"""Build the clean final folder of the Conair POC (test 20): only the images that were used and the inputs that made them.

    python tools/build_final.py outputs/FINAL_2026-10-27

Reads outputs/jobs_test20_plan.json (looks) and outputs/20_product/ (product images). Never deletes experiments:
everything here is a copy; the tests stay in their own outputs/ folders.
"""
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "outputs", "jobs_test20_plan.json")
LOOKS = os.path.join(ROOT, "outputs", "20_nano_inuse")
PROD = os.path.join(ROOT, "outputs", "20_product")
HERO_DIR = os.path.join(ROOT, "outputs", "21_hero_banners")
AMZ_DIR = os.path.join(ROOT, "outputs", "25_amazon_flora")  # test 23: 4 more Amazon scenes made on Flora
PB_DIR = os.path.join(ROOT, "outputs", "23_product_banners")
CLIP_DIR = os.path.join(ROOT, "outputs", "24_clips")
# test 22: product-only 16:9 banners, after the product fix (p1 and p2 redone lying flat, review 2026-10-27)
PRODUCT_BANNERS = {"p1_auto_curler_orange": "p1_auto_curler_orange_v2__3_fixed.png", "p2_thermal_brush_sky": "p2_thermal_brush_sky_v2__2_fixed.png",
                   "p3_flat_iron_pink_rush": "p3_flat_iron_pink_rush__2_fixed.png", "p4_style_switch_violet": "p4_style_switch_violet__2_fixed.png",
                   "p5_flat_iron_nano_blue_yellow": "p5_flat_iron_nano_blue_yellow__2_fixed.png"}
# Seedance 2.5 clips, 5 s, 720p, that passed QA (the first p1 clip came from the rejected floating banner)
CLIPS = ["clip_c1_a10_diffuser_pink.mp4", "clip_c2_a01_roundbrush_violet.mp4", "clip_c4_a06_flatiron_orange.mp4",
         "clip_p3_flat_iron_pink_rush.mp4", "clip_p4_style_switch_violet.mp4"]
HERO = ["c1_a10_diffuser_pink_v2", "c2_a01_roundbrush_violet_v2",
        "c3_a07_thermalbrush_skyblue_v5_sunburst", "c4_a06_flatiron_orange_v5_sunburst"]

# look: (after plan key, in-use plan key, after file, in-use file after the product fix)
LOOK_FILES = [
    ("a03_after", "a03_inuse_v3", "a03_after_v7.png", "a03_inuse_fixed_v3.png"),
    ("a05_after", "a05_inuse_free", "a05_after_v7.png", "a05_inuse_free_fixed_v2.png"),
    ("a08_after", "a08_inuse_free", "a08_after_v7.png", "a08_inuse_free_fixed_v2.png"),
    ("A01_SS_t2_paddle__after", "A01_SS_t2_paddle__inuse", "a01_paddle_after_v7.png", "a01_paddle_inuse_fixed_v2.png"),
    ("A06_SS_t1_aircurl__after", "A06_SS_t1_aircurl__inuse", "a06_aircurl_after_v7.png", "a06_aircurl_inuse_fixed_v2.png"),
    ("A09_TB_t1__after", "A09_TB_t1__inuse", "a09_tb_after_v7.png", "a09_tb_inuse_fixed_v2.png"),
    ("A10_SS_t3_diffuser__after", "A10_SS_t3_diffuser__inuse", "a10_diffuser_after_v7.png", "a10_diffuser_inuse_fixed_v3.png"),
    ("A08_AC_t2__after", "A08_AC_t2__inuse", "a08_ac_after_v7.png", "a08_ac_inuse_fixed_v2.png"),
    ("A02_FI_t4_silkpress__after", "A02_FI_t4_silkpress__inuse_pose02_v6", "a02_silkpress_after_v7.png", "a02_silkpress_inuse_pose02_v6.png"),
    ("A06_FI_t1__after", "A06_FI_t1__inuse", "a06_fi_after_v7.png", "a06_fi_inuse_fixed_v2.png"),
    ("A01_SS_t2_roundbrush__after", "A01_SS_t2_roundbrush__inuse", "a01_roundbrush_after_v7.png", "a01_roundbrush_inuse_fixed_v3.png"),
    ("A07_TB_t3__after", "A07_TB_t3__inuse", "a07_tb_after_v7.png", "a07_tb_inuse_fixed_v2.png"),
    ("A04_TB_t2__after", "A04_TB_t2__inuse", "a04_tb_after_v7.png", "a04_tb_inuse_fixed_v2.png"),
]
# QA 2026-10-27 (outputs/22_inuse_redo): A03 redone with the hair on the barrel, A01 round brush and A10 logo fixed.
# A02: the test 17 composition (diagonal iron on the chest) redone at 4K from original inputs (+16% hair over the after)
FIX_DIRS = {"a02_silkpress_inuse_fixed_v3.png": os.path.join(LOOKS, "fix_a02_silkpress_v4"),
            "a02_silkpress_inuse_pose02_v6.png": os.path.join(ROOT, "outputs", "22_inuse_redo", "fix_a02_pose02_v6b_4")}
# product images: the inpaint fix is kept only where it improved the product (review 2026-10-27)
NO_FIX = set()  # every product image keeps its fix since the aspect bug was fixed (test 20)
IN_HAND_POSES = {"in_hand__auto_curler_02__a03": "auto_curler/auto_curler_in_hand_02",
                 "in_hand__flat_iron_pink_rush_02__a02": "flat_iron/flat_iron_in_hand_02",
                 "in_hand__thermal_brush_01__a09": "thermal_brush/thermal_brush_in_hand_01"}
PACKSHOTS = ["auto_curler/nano_blue/packshots/01_packshot_white_3q.jpg",
             "flat_iron/nano_blue/packshots/03_packshot_nano_blue_BNT131T-N.jpg",
             "flat_iron/pink_rush/packshots/01_packshot_pink_rush_BNT131THP.jpg",
             "style_switch/nano_blue/packshots/01_packshot_all_attachments.jpg",
             "thermal_brush/nano_blue/packshots/01_packshot_white_front.jpg"]
PROMPTS = ["02_after.txt", "07_in_use_nano.txt", "08_product_inpaint.txt", "03_in_hand.txt", "04_soft_environment.txt"]
DOCS = ["CLAUDE.md", "docs/conair/HAIR_REFS.md", "docs/conair/TEST_20.md", "docs/conair/pipeline.png"]


def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def hero(out):
    """07_hero_banners: the 4 close-ups (test 21) after the product fix, with their prompt json, fix crops and the style reference."""
    for name in HERO:
        cp(os.path.join(HERO_DIR, f"{name}__fixed.png"), os.path.join(out, "07_hero_banners", f"{name[:2]}_{name[3:]}.png"))
        cp(os.path.join(HERO_DIR, f"{name}.json"), os.path.join(out, "05_prompts", "filled", "07_hero_banners", f"{name}.json"))
        fix = os.path.join(HERO_DIR, f"fix_{name}")
        if os.path.isdir(fix):
            shutil.copytree(fix, os.path.join(out, "05_prompts", "filled", "07_hero_banners", f"{name}__product_fix"), dirs_exist_ok=True)
    for f in ("plan_v2.json", "inpaint_plan.json"):
        cp(os.path.join(HERO_DIR, f), os.path.join(out, "05_prompts", "filled", "07_hero_banners", f))
    cp(os.path.join(ROOT, "prompts", "conair", "09_hero_banner.txt"), os.path.join(out, "05_prompts", "09_hero_banner.txt"))
    ref = os.path.join(ROOT, "samples", "web_refs", "conair_home")
    if os.path.isdir(ref):  # internal only, never published
        shutil.copytree(ref, os.path.join(out, "00_inputs", "style_reference_conair_home_INTERNAL"), dirs_exist_ok=True)


def amazon_flora(out):
    for f in sorted(os.listdir(AMZ_DIR)):
        if f.endswith("__2_fixed.png"):
            cp(os.path.join(AMZ_DIR, f), os.path.join(out, "04_product", "soft_environment", f[3:].replace("__2_fixed", "")))
    cp(os.path.join(AMZ_DIR, "plan.json"), os.path.join(out, "05_prompts", "filled", "04_product", "jobs_test23_flora.json"))


def product_banners_and_clips(out):
    for name, f in PRODUCT_BANNERS.items():
        cp(os.path.join(PB_DIR, f), os.path.join(out, "09_product_banners", f"{name}.png"))
    for f in ("plan.json",):
        cp(os.path.join(PB_DIR, f), os.path.join(out, "05_prompts", "filled", "09_product_banners", f))
    cp(os.path.join(ROOT, "prompts", "conair", "10_product_banner.txt"), os.path.join(out, "05_prompts", "10_product_banner.txt"))
    for f in CLIPS:
        cp(os.path.join(CLIP_DIR, f), os.path.join(out, "10_clips", f))
    cp(os.path.join(CLIP_DIR, "plan.json"), os.path.join(out, "10_clips", "jobs.json"))


def variations(out):
    """08_variations: every tried version next to the final, so the choice can be reviewed (copies; the tests stay in place)."""
    v = os.path.join(out, "08_variations")
    for ak, uk, af, uf in LOOK_FILES:
        look = af.replace("_after_v7.png", "")
        for f in sorted(os.listdir(LOOKS)):
            if f.endswith(".png") and (f.startswith(look + "_after_v") or f.startswith(look + "_inuse")):
                cp(os.path.join(LOOKS, f), os.path.join(v, "looks", look, f))
    for f in sorted(os.listdir(HERO_DIR)):
        if f.endswith(".png"):
            cp(os.path.join(HERO_DIR, f), os.path.join(v, "hero_banners", "groups_pending" if f.startswith("g") else "close_ups", f))
    for f in sorted(os.listdir(PROD)):
        if f.endswith(".png"):
            cp(os.path.join(PROD, f), os.path.join(v, "product", f))


def main(out):
    plan = json.load(open(PLAN))
    used = set()
    for ak, uk, af, uf in LOOK_FILES:
        a = plan[ak]["args"]  # [template, avatar, rule, pose, ref, (colour)]
        name = f"{a[1]}__{a[2]}__{a[4]}"
        cp(os.path.join(ROOT, "library", "avatars", a[1], "front.png"), os.path.join(out, "01_before", f"{a[1]}__before.png"))
        cp(os.path.join(LOOKS, af), os.path.join(out, "02_after", f"{name}__after.png"))
        cp(os.path.join(LOOKS, uf), os.path.join(out, "03_in_use", f"{name}__in_use.png"))
        for k in ((ak + "_v7") if ak + "_v7" in plan else (ak + "_v6"), uk):
            used.update(plan[k]["inputs"])
            p = os.path.join(out, "05_prompts", "filled", "02_after" if k.startswith(ak) else "03_in_use", f"{name}.txt")
            os.makedirs(os.path.dirname(p), exist_ok=True)
            e = plan[k]
            open(p, "w", encoding="utf-8").write(
                f"model: {e.get('model', '')}\njob: {e.get('job_id') or e.get('job', '')}\ninputs:\n"
                + "".join(f"  {i + 1}  {x}\n" for i, x in enumerate(e["inputs"])) + "\n" + e["prompt"] + "\n")
        base = uf.replace("_inuse_free_fixed_v2.png", "").replace("_inuse_fixed_v2.png", "")
        fix = os.path.join(LOOKS, "fix_" + (uf.replace("_inuse_fixed_v3.png", "_v3") if uf.endswith("_v3.png") else base))
        fix = FIX_DIRS.get(uf, fix)
        if os.path.isdir(fix):
            shutil.copytree(fix, os.path.join(out, "05_prompts", "filled", "03_in_use", f"{name}__product_fix"), dirs_exist_ok=True)
    for rel in sorted(used):  # every original input of the looks: avatar, real reference, hair cutout, lock, product sheet
        src = os.path.join(ROOT, rel)
        if os.path.exists(src):
            cp(src, os.path.join(out, "00_inputs", os.path.relpath(src, os.path.join(ROOT, "library"))))
            ref = os.path.join(os.path.dirname(src), "ref.json")
            if "hair_styles" in rel and os.path.exists(ref):
                cp(ref, os.path.join(out, "00_inputs", os.path.relpath(ref, os.path.join(ROOT, "library"))))
    for av in os.listdir(os.path.join(out, "00_inputs", "avatars")):
        cp(os.path.join(ROOT, "library", "avatars", av, "meta.json"), os.path.join(out, "00_inputs", "avatars", av, "meta.json"))
    for p in PACKSHOTS:
        cp(os.path.join(ROOT, "library", "products", p), os.path.join(out, "00_inputs", "products", p))
    for sku in ("auto_curler/nano_blue", "flat_iron/nano_blue", "flat_iron/pink_rush", "style_switch/nano_blue", "thermal_brush/nano_blue"):
        cp(os.path.join(ROOT, "library", "products", sku, "card_v2.png"), os.path.join(out, "00_inputs", "products", sku, "card_v2.png"))
    for n, pose in IN_HAND_POSES.items():
        for f in ("gray.png", "pose.txt"):
            src = os.path.join(ROOT, "library", "poses", "in_hand", pose, f)
            if os.path.exists(src):
                cp(src, os.path.join(out, "00_inputs", "poses_3d", "in_hand", pose, f))
    for f in ("hair_change.json", "product_hair_rules.json", "hair_refs.json"):
        src = os.path.join(ROOT, "docs", "products", f)
        if os.path.exists(src):
            cp(src, os.path.join(out, "00_inputs", "rules", f))
    for f in sorted(os.listdir(PROD)):
        if not f.endswith("__1_nano.png"):
            continue
        n = f[: -len("__1_nano.png")]
        fixed = [os.path.join(PROD, f"{n}__2_fixed_{v}.png") for v in ("v3", "v2")]  # v3: re-done at the exact model aspect
        src = os.path.join(PROD, f) if n in NO_FIX else next(x for x in fixed if os.path.exists(x))
        cp(src, os.path.join(out, "04_product", "in_hand" if n.startswith("in_hand") else "soft_environment", f"{n}.png"))
        fix = os.path.join(PROD, f"fix2_{n}") if os.path.isdir(os.path.join(PROD, f"fix2_{n}")) else os.path.join(PROD, f"fix_{n}")
        if os.path.isdir(fix) and n not in NO_FIX:
            shutil.copytree(fix, os.path.join(out, "05_prompts", "filled", "04_product", f"{n}__product_fix"), dirs_exist_ok=True)
    jobs = os.path.join(PROD, "jobs_test20_product.json")
    if os.path.exists(jobs):
        shutil.copy2(jobs, os.path.join(out, "05_prompts", "filled", "04_product", "jobs_and_prompts.json"))
    for f in PROMPTS:
        cp(os.path.join(ROOT, "prompts", "conair", f), os.path.join(out, "05_prompts", f))
    for f in DOCS:
        if os.path.exists(os.path.join(ROOT, f)):
            cp(os.path.join(ROOT, f), os.path.join(out, "06_instructions", os.path.basename(f)))
    hero(out)
    product_banners_and_clips(out)
    amazon_flora(out)
    variations(out)
    cp(PLAN, os.path.join(out, "06_instructions", "jobs", "jobs_test20_plan.json"))
    cp(os.path.join(ROOT, "docs", "conair", "FINAL_README.md"), os.path.join(out, "README.md"))
    wf = os.path.join(ROOT, "docs", "conair", "WORKFLOW_test20.png")
    if os.path.exists(wf):
        cp(wf, os.path.join(out, "WORKFLOW_test20.png"))
    print("built", out)


if __name__ == "__main__":
    main(os.path.abspath(sys.argv[1]))
