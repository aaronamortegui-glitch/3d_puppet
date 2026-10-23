"""Export the Conair POC as a self-contained folder for someone else to continue (assets, prompts, rules, docs).

    python tools/export_handoff.py D:/Superside/Conair_POC_handoff

Copies, never moves. Layout:
  00_README.md                      start here (written from docs/conair/HANDOFF.md)
  01_library/                       approved inputs: products, poses (+ hair tags), hair styles, avatars, rules
  02_rules_and_tools/               rules JSON, pose tags, the Python tools, every doc of the POC
  03_tests/test_NN_<name>/          images/ + prompts/<image>.txt (model, settings, input images, prompt) + jobs.json + TEST_NN.md
Input images in the prompt files are named by their library path (the Krea upload URLs are mapped back with outputs/uploads*.txt).
"""

import glob
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NANO, SUNBURST = "google/nano-banana-2.1", "openai/gpt-image-2.5-sunburst"


def rel(*p):
    return os.path.join(ROOT, *p)


def uploads():
    rev = {}
    for fn in sorted(glob.glob(rel("outputs", "uploads*.txt"))):
        for line in open(fn, encoding="utf-8").read().splitlines():
            p = line.strip().split(" ")
            if len(p) == 2 and p[1].startswith("http"):
                rev[p[1]] = "library/" + p[0]
    return rev


def copy(src, dst):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        return True
    return False


def prompt_file(path, model, settings, inputs, prompt, extra=""):
    lines = [f"MODEL: {model}", f"SETTINGS: {settings}", "INPUT IMAGES (in order):"]
    lines += [f"  {i + 1}. {x}" for i, x in enumerate(inputs)] or ["  (none)"]
    if extra:
        lines.append(extra)
    lines += ["", "PROMPT:", prompt, ""]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write("\n".join(lines))


def tests(out, rev):
    def name(o):
        return os.path.basename(o)[:-4]

    def emit(test, jobs, get):
        d = os.path.join(out, "03_tests", test)
        n = 0
        for j in jobs:
            o, model, settings, urls, prompt, extra = get(j)
            if not copy(rel(o), os.path.join(d, "images", os.path.basename(o))):
                continue
            prompt_file(os.path.join(d, "prompts", name(o) + ".txt"), model, settings, [rev.get(u, u) for u in urls], prompt, extra)
            n += 1
        return d, n

    done = {}
    # tests 1-2: only job ids were kept; prompts follow the templates in TEST_01/02.md (same structure as test 3)
    for test, tsv, md in (("test_01_first_in_use_and_before_after", "jobs_test1.tsv", "TEST_01.md"),
                          ("test_02_in_hand_and_soft_environment", "jobs_test2.tsv", "TEST_02.md")):
        d = os.path.join(out, "03_tests", test)
        n = 0
        for line in open(rel("outputs", tsv), encoding="utf-8").read().splitlines():
            o = line.split("\t")[0]
            if o.startswith("outputs/") and copy(rel(o), os.path.join(d, "images", os.path.basename(o))):
                n += 1
        copy(rel("outputs", tsv), os.path.join(d, tsv))
        copy(rel("docs", "conair", md), os.path.join(d, md))
        open(os.path.join(d, "prompts_NOTE.txt"), "w", encoding="utf-8").write(
            "Only the Krea job ids of this test were kept (jobs file). The prompts follow the templates described in "
            f"{md}; test 3 (folder test_03) uses the same structure with every prompt saved.\n")
        done[test] = n
    # test 3: Nano Banana 2.1, 4 categories
    j3 = json.load(open(rel("outputs", "jobs_test3_plan.json"), encoding="utf-8"))
    d, n = emit("test_03_four_categories_nano", j3, lambda j: (j["out"], NANO, f"aspect {j['ar']}, 2K", j["urls"], j["prompt"],
                                                                 f"BEFORE IMAGE: {j['before']}" if j.get("before") else ""))
    copy(rel("docs", "conair", "TEST_03.md"), os.path.join(d, "TEST_03.md")); done["test_03"] = n
    # tests 4-6: model compare, hair length, architecture
    for test, plan, md in (("test_04_nano_vs_sunburst", "jobs_test4_plan.json", "TEST_04.md"),
                           ("test_05_hair_length", "jobs_test5_plan.json", "TEST_05.md"),
                           ("test_06_architecture_per_device", "jobs_test6_plan.json", "TEST_06.md")):
        jobs = json.load(open(rel("outputs", plan), encoding="utf-8"))
        d, n = emit(test, jobs, lambda j: (j["out"], j["model"],
                                           f"aspect {j['input'].get('aspect_ratio')}, {j['input'].get('resolution')}" + (", quality high" if "quality" in j["input"] else ""),
                                           j["input"]["image_urls"], j["input"]["prompt"],
                                           f"TARGET HAIR LENGTH: {j['target']}" if j.get("target") else ""))
        copy(rel("outputs", plan), os.path.join(d, "jobs.json"))
        copy(rel("docs", "conair", md), os.path.join(d, md))
        done[test] = n
    # test 7: no images, the pose tags and the picker matrix
    d = os.path.join(out, "03_tests", "test_07_pose_by_hair")
    copy(rel("docs", "conair", "TEST_07.md"), os.path.join(d, "TEST_07.md"))
    copy(rel("docs", "conair", "POSE_HAIR.md"), os.path.join(d, "POSE_HAIR.md"))
    # test 8: products on Sunburst, then with the support rule
    j8 = json.load(open(rel("outputs", "jobs_test8_plan.json"), encoding="utf-8")) + json.load(open(rel("outputs", "jobs_test8b_plan.json"), encoding="utf-8"))
    d, n = emit("test_08_products_sunburst_support_rule", j8, lambda j: (j["out"], SUNBURST, "aspect 1:1, 2K, quality high", j["urls"], j["prompt"],
                                                                           f"NANO BANANA VERSION (test 3): {j['nano_out']}"))
    for j in j8:  # the Nano version next to it, for the comparison
        copy(rel(j["nano_out"]), os.path.join(d, "images_nano_test3", os.path.basename(j["nano_out"])))
    copy(rel("docs", "conair", "TEST_08.md"), os.path.join(d, "TEST_08.md")); done["test_08"] = n
    return done


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rev = uploads()
    shutil.copytree(rel("library"), os.path.join(out, "01_library"), dirs_exist_ok=True)
    t = os.path.join(out, "02_rules_and_tools")
    for f in ("docs/products/product_hair_rules.json", "tools/pose_hair.json", "tools/pose_details.json", "tools/library_manifest.json",
              "tools/hair_length.py", "tools/pick_pose.py", "tools/prompt_rules.py", "tools/scene_qa.py", "tools/build_library.py",
              "tools/product_cards.py", "tools/export_handoff.py"):
        copy(rel(f), os.path.join(t, f))
    for f in glob.glob(rel("docs", "conair", "*.md")) + glob.glob(rel("docs", "products", "*.md")):
        copy(f, os.path.join(t, os.path.relpath(f, ROOT)))
    done = tests(out, rev)
    shutil.copy2(rel("docs", "conair", "HANDOFF.md"), os.path.join(out, "00_README.md"))
    print(json.dumps(done, indent=1))


if __name__ == "__main__":
    main()
