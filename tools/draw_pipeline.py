"""Draws docs/conair/pipeline.png: how one Conair image is made (inputs -> logic -> prompt -> model -> QA -> output).

Uses real library files as thumbnails (example: avatar A03, Style/Switch round brush, reference r47).
    python tools/draw_pipeline.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "library")
W, H = 3000, 1460
BG, INK, GREY, LINE = (250, 250, 248), (30, 30, 30), (95, 95, 95), (160, 160, 160)
F = {s: ImageFont.truetype("arial.ttf", s) for s in (22, 26, 30, 38, 56)}
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


d.text((60, 40), "Conair POC: how one image is made", font=B[56], fill=INK)
d.text((60, 115), "Inputs come from library/ (built by tools/build_library.py). Example: avatar A03 (2B waves) + Style/Switch round brush (SS_t2_roundbrush) + reference r47.", font=F[26], fill=GREY)

ex = {
    "avatar": f"{LIB}/avatars/client_a03_red_wavy/front.png",
    "pose": f"{LIB}/poses/in_use/style_switch/style_switch_in_use_01/gray.png",
    "product": f"{LIB}/products/style_switch/nano_blue/card_clean.png",
    "lock": f"{LIB}/hair_styles/style_switch_round_brush/SS_t2_roundbrush/r47/lock.png",
    "after": f"{LIB}/hair_styles/style_switch_round_brush/SS_t2_roundbrush/r47/after.png",
}
X0, BW, BH, GAP = 60, 900, 200, 22
inputs = [
    ("1  Avatar (who)", ["library/avatars/client_aNN_<look>/", "front.png + meta.json: hair type, colour,", "where the hair ends (measured)"], ex["avatar"]),
    ("2  Pose (how)", ["library/poses/in_use/<sku>/<sku>_in_use_NN/", "gray.png (orange proxy = true product size),", "pose.txt; only approved poses (front, 3/4)"], ex["pose"]),
    ("3  Product sheet (what)", ["library/products/<sku>/<colour>/", "card_clean.png, packshots/"], ex["product"]),
    ("4  Hair lock (texture)", ["library/hair_styles/<sku_slot>/<rule>/rNN/lock.png", "real hair, grade A only: curl pattern,", "texture, shine. No wig, no colour."], ex["lock"]),
    ("5  Real after (shape)", ["library/hair_styles/<sku_slot>/<rule>/rNN/after.png", "the finished style on a real person"], ex["after"]),
]
y = 190
for t, ls, th in inputs:
    box(X0, y, BW, BH, t, ls, "in", th)
    y += BH + GAP

LX, LW = 1120, 820
logic = [
    ("Product x hair rule", ["docs/products/product_hair_rules.json", "allowed? which style? forbidden combos stop", "(Auto Curler, Thermal Brush on coily)"]),
    ("Pose picker", ["tools/pick_pose.py <avatar> <rule>", "sculpted hair must match hers: ok/check/avoid;", "rejected poses: tools/pose_status.json"]),
    ("Hair length + amount", ["tools/hair_length.py", "after length = curl shrinkage model,", "same amount of hair, no added volume"]),
    ("Prompt template", ["prompts/conair/01_in_use.txt ...", "filled by tools/fill_prompt.py with", "prompt_rules (hair from avatar, held for real)"]),
]
ly = 230
for t, ls in logic:
    box(LX, ly, LW, 230, t, ls, "logic")
    ly += 260
for i in range(3):
    arrow(LX + LW // 2, 460 + 260 * i, LX + LW // 2, 490 + 260 * i)
for i in range(5):
    arrow(X0 + BW, 290 + i * (BH + GAP), LX, 345 + 260 * 3 + 0 * i)

GX, GW = 2080, 860
box(GX, 230, GW, 230, "Generate", ["GPT Image 2.5 Sunburst (Krea)", "quality high, 2K, 3:4 (in use) or 1:1", "soft environment: + Nano Banana 2.1 relight (test)"], "gen")
box(GX, 560, GW, 230, "QA gate", ["tools/scene_qa.py: pose drift, face scale,", "product size error <= 25%,", "hair length error <= 15%; else regenerate"], "gen")
box(GX, 890, GW, 230, "Output", ["outputs/<category>/<sku>/", "prompt .txt + job id kept next to each image", "then Figma / FigJam boards"], "out")
arrow(LX + LW, 345 + 260 * 3, GX, 345)
arrow(GX + GW // 2, 460, GX + GW // 2, 560)
arrow(GX + GW // 2, 790, GX + GW // 2, 890)

d.text((GX, 1180), "Rules learned (CLAUDE.md, HANDOFF.md)", font=B[30], fill=INK)
rules = ["Never a forbidden product x hair combination.", "Front or 3/4 poses; the orange proxy must be the real silhouette.",
         "Hair: identity, colour and length from the avatar; texture from the real lock.", "Product held for real (contact shadows, fingers around it).",
         "On a set the product rests on a support, never floats.", "Sunburst for everything; Nano Banana only as fallback / relight test."]
yy = 1230
for r in rules:
    d.text((GX, yy), "- " + r, font=F[22], fill=GREY)
    yy += 34

os.makedirs(os.path.join(ROOT, "docs", "conair"), exist_ok=True)
im.save(os.path.join(ROOT, "docs", "conair", "pipeline.png"))
print("docs/conair/pipeline.png")
