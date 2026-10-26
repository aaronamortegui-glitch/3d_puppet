"""Draws docs/conair/pipeline.png: how one Conair image is made (inputs -> logic -> prompt -> model -> QA -> output).

Uses real library files as thumbnails (example: avatar A03, Style/Switch round brush, reference r47).
    python tools/draw_pipeline.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
W, H = 3000, 1400
BG, INK, GREY, LINE = (250, 250, 248), (30, 30, 30), (95, 95, 95), (160, 160, 160)
F = {s: ImageFont.truetype("arial.ttf", s) for s in (22, 24, 26, 30, 38, 56)}
B = {s: ImageFont.truetype("arialbd.ttf", s) for s in (26, 30, 38, 56)}
COL = {"in": (225, 238, 252), "logic": (255, 241, 214), "gen": (225, 245, 230), "out": (240, 230, 250)}

im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)


def box(x, y, w, h, title, lines, kind, thumb=None):
    d.rounded_rectangle([x, y, x + w, y + h], 18, fill=COL[kind], outline=LINE, width=2)
    tx = x + 20
    if thumb and os.path.exists(thumb):
        t = Image.open(thumb).convert("RGB")
        t.thumbnail((h - 30, h - 30))
        im.paste(t, (x + 15, y + (h - t.height) // 2))
        tx = x + 30 + t.width
    d.text((tx, y + 16), title, font=B[30], fill=INK)
    yy = y + 58
    for ln in lines:
        d.text((tx, yy), ln, font=F[22], fill=GREY)
        yy += 30
    return (x, y, w, h)


def arrow(x0, y0, x1, y1):
    d.line([x0, y0, x1, y1], fill=(90, 90, 90), width=4)
    import math
    a = math.atan2(y1 - y0, x1 - x0)
    p = [(x1, y1), (x1 - 22 * math.cos(a - 0.4), y1 - 22 * math.sin(a - 0.4)), (x1 - 22 * math.cos(a + 0.4), y1 - 22 * math.sin(a + 0.4))]
    d.polygon(p, fill=(90, 90, 90))


d.text((60, 40), "Conair POC: how one look is made (before -> after -> in use)", font=B[56], fill=INK)
d.text((60, 115), "All inputs come from library/ (tools/build_library.py). Example: avatar A08 (2A) + Style/Switch round brush (SS_t2_roundbrush) + real reference r47.", font=F[26], fill=GREY)

ex = {
    "avatar": f"{LIB}/avatars/client_a08_shag_bangs/front.png",
    "refpair": f"{LIB}/hair_styles/style_switch_round_brush/SS_t2_roundbrush/r47/after.png",
    "lock": f"{LIB}/hair_styles/style_switch_round_brush/SS_t2_roundbrush/r47/lock.png",
    "after": f"{LIB}/avatars/client_a08_shag_bangs/after/SS_t2_roundbrush__r47.png",
    "pose": f"{LIB}/poses/in_use/style_switch/style_switch_in_use_04/gray.png",
    "product": f"{LIB}/products/style_switch/nano_blue/card_clean.png",
    "inuse": os.path.join(ROOT, "outputs", "13_final", "client_a08_shag_bangs__SS_t2_roundbrush__use_04__r47.png"),
}
X0, BW, BH, GAP = 60, 880, 200, 22
inputs = [
    ("Avatar = the BEFORE", ["library/avatars/client_aNN_<look>/front.png", "identity, colour, background, length, volume", "meta.json: hair type, where the hair ends"], ex["avatar"]),
    ("Real reference pair (grade A)", ["library/hair_styles/<sku_slot>/<rule>/rNN/", "before.png + after.png: HOW MUCH hair changes", "lock.png: curl pattern, texture, shine"], ex["refpair"]),
    ("Gray pose v2 (approved)", ["library/poses/in_use/<sku>/<sku>_in_use_NN/gray.png", "neutral moderate hair; orange proxy = product", "rejected: library/poses/_rejected/"], ex["pose"]),
    ("Product sheet", ["library/products/<sku>/<colour>/card_clean.png", "the exact product, its colours and size"], ex["product"]),
]
y = 190
for t, ls, th in inputs:
    box(X0, y, BW, BH, t, ls, "in", th)
    y += BH + GAP

SX, SW = 1060, 900
box(SX, 190, SW, 300, "STEP 1 · AFTER (prompts/conair/02_after.txt)", ["inputs: avatar + real before + real after + lock",
    "length + width change = the real pair (hair_change.json)", "same face, clothes, framing and BACKGROUND", "save: library/avatars/<avatar>/after/<rule>__rNN.png"], "logic", ex["after"])
box(SX, 520, SW, 300, "STEP 2 · IN USE (prompts/conair/01_in_use.txt)", ["inputs: gray pose v2 + the step-1 AFTER + product sheet + lock",
    "hair exactly as in the after (no longer, no fuller)", "background as in the after; product held for real", "save: outputs/<test>/<avatar>__<rule>__<pose>__rNN.png"], "logic", ex["inuse"])
box(SX, 850, SW, 250, "Rules before generating", ["tools/fill_prompt.py stops: forbidden product x hair,", "rule for another hair type, rejected pose, ref not grade A",
    "tools/pick_pose.py <avatar> <rule> --finished: ok / check / avoid"], "logic")
arrow(X0 + BW, 290, SX, 300)
arrow(X0 + BW, 512, SX, 340)
arrow(X0 + BW, 734, SX, 640)
arrow(X0 + BW, 956, SX, 680)
arrow(SX + SW // 2, 490, SX + SW // 2, 520)

GX, GW = 2100, 840
box(GX, 190, GW, 230, "Model", ["GPT Image 2.5 Sunburst on Krea", "quality high, 2K, 3:4", "Nano Banana 2.1: gray poses, relight test"], "gen")
box(GX, 450, GW, 230, "QA (by eye + tools/scene_qa.py)", ["same identity and background as the avatar", "hair length / width as the real pair",
    "product size and grip right"], "gen")
box(GX, 710, GW, 390, "Where the results go", ["boards: FigJam CONAIR page 'study', section", "FINAL RESULTS (table: before -> after -> in use + ref)",
    "workflow: design file, page 'workflow'", "prompts: prompts/conair/ (copy: library/prompts/)", "plans + job ids: outputs/jobs_testNN_*_plan.json",
    "each image has its .prompt.txt next to it"], "out")
arrow(SX + SW, 640, GX, 300)
arrow(GX + GW // 2, 420, GX + GW // 2, 450)
arrow(GX + GW // 2, 680, GX + GW // 2, 710)

d.text((60, 1150), "Rules learned (CLAUDE.md, docs/conair/TEST_11-13.md)", font=B[30], fill=INK)
rules = ["Before -> after -> in use: the in-use image takes the hair from the generated after, never from the pose.",
         "Length and volume change exactly as in the real reference pair: never exaggerated, never less than real.",
         "Keep the avatar's background in the after and in use.  No pose with big or abundant sculpted hair.",
         "Never a forbidden product x hair combination.  Front or 3/4 poses; the orange proxy is the real silhouette.",
         "Product held for real; on a set it rests on a support.  Sunburst for everything."]
yy = 1200
for r in rules:
    d.text((60, yy), "- " + r, font=F[24], fill=GREY)
    yy += 36

os.makedirs(os.path.join(ROOT, "docs", "conair"), exist_ok=True)
im.save(os.path.join(ROOT, "docs", "conair", "pipeline.png"))
print("docs/conair/pipeline.png")
