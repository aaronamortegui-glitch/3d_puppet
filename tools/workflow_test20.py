"""Draw docs/conair/WORKFLOW_test20.png: the test 20 workflow with real inputs and outputs of one look and one product image.

    python tools/workflow_test20.py
"""
from PIL import Image, ImageDraw, ImageFont

F = lambda s, b=False: ImageFont.truetype("arialbd.ttf" if b else "arial.ttf", s)
L = "library/"
R36 = L + "hair_styles/flat_iron/FI_t1/r36/"
OUT = "outputs/20_nano_inuse/"
PR = "outputs/20_product/"

c = Image.new("RGB", (3200, 1900), (248, 248, 246))
d = ImageDraw.Draw(c)


def card(x, y, p, label, w=230, h=290):
    i = Image.open(p).convert("RGB")
    i.thumbnail((w, h))
    d.rounded_rectangle((x - 6, y - 6, x + w + 6, y + h + 44), 12, fill="white", outline=(220, 220, 220), width=2)
    c.paste(i, (x + (w - i.width) // 2, y + (h - i.height) // 2))
    d.text((x, y + h + 8), label, font=F(22), fill=(60, 60, 60))
    return (x + w + 6, y + h // 2)


def box(x, y, w, h, title, lines, col):
    d.rounded_rectangle((x, y, x + w, y + h), 16, fill=col)
    d.text((x + 20, y + 16), title, font=F(30, True), fill="white")
    for n, t in enumerate(lines):
        d.text((x + 20, y + 60 + 30 * n), t, font=F(22), fill="white")
    return (x, y + h // 2), (x + w, y + h // 2)


def arrow(a, b):
    d.line([a, b], fill=(80, 80, 80), width=5)
    x, y = b
    d.polygon([(x, y), (x - 18, y - 10), (x - 18, y + 10)], fill=(80, 80, 80))


ORANGE, BLUE, GREEN, PURPLE = (255, 106, 0), (40, 90, 160), (20, 130, 90), (150, 60, 140)
d.text((60, 30), "Conair POC · test 20 workflow (example: client_a06_platinum · flat iron · FI_t1 · r36)", font=F(44, True), fill=(20, 20, 20))
d.text((60, 90), "Only original inputs go into the models. No generated image is chained, except the product crop in the fix, "
       "and only the product is pasted back.", font=F(26), fill=(90, 90, 90))

y = 190
d.text((60, y), "1 · AFTER", font=F(32, True), fill=ORANGE)
card(60, y + 50, L + "avatars/client_a06_platinum/front.png", "avatar (before)")
card(320, y + 50, R36 + "before.png", "real ref before")
card(580, y + 50, R36 + "after.png", "real ref after")
e = card(840, y + 50, R36 + "lock.png", "real lock")
i, o = box(1180, y + 90, 560, 220, "Sunburst · 02_after.txt", ["new photo: other direction (mirrored input)", "hand on waist or behind back, light smile",
                                                            "length/width change = real pair", "quality high · 4K · 3:4"], BLUE)
arrow(e, i)
card(1830, y + 50, OUT + "a06_fi_after_v7.png", "AFTER (4K)")
arrow(o, (1824, o[1]))

y = 760
d.text((60, y), "2 · IN USE  →  3 · PRODUCT FIX (crop → inpaint → register + stitch)", font=F(32, True), fill=ORANGE)
card(60, y + 50, L + "avatars/client_a06_platinum/front.png", "avatar")
card(320, y + 50, R36 + "after_hair.png", "real after, hair only")
card(580, y + 50, R36 + "lock.png", "real lock")
e = card(840, y + 50, L + "products/flat_iron/nano_blue/card_v2.png", "card_v2 (6K sheet)")
i, o = box(1180, y + 90, 500, 220, "Nano Banana 2.1 · 07", ["original inputs only", "dynamic pose, product in use",
                                                          "HOW IT TOUCHES THE HAIR", "2K · 3:4 · thinking high"], GREEN)
arrow(e, i)
e2 = card(1760, y + 50, OUT + "a06_fi_inuse_free.png", "in use (Nano)")
arrow(o, (1754, o[1]))
i2, o2 = box(2060, y + 90, 420, 220, "Sunburst · 08 inpaint", ["crop at the model's exact shape", "+ card_v2 · fix logo/buttons",
                                                             "register, paste only the product", "feathered · colour matched"], PURPLE)
arrow(e2, i2)
card(2560, y + 50, OUT + "a06_fi_inuse_fixed_v2.png", "FINAL IN USE")
arrow(o2, (2554, o2[1]))

y = 1330
d.text((60, y), "4 · PRODUCT IMAGES (soft environment / in hand)", font=F(32, True), fill=ORANGE)
card(60, y + 50, L + "products/flat_iron/pink_rush/packshots/01_packshot_pink_rush_BNT131THP.jpg", "real packshot")
e = card(320, y + 50, L + "products/flat_iron/pink_rush/card_v2.png", "card_v2")
i, o = box(660, y + 90, 460, 220, "Nano Banana 2.1 · 04 / 03", ["set or gray hand pose", "logo side from card_v2", "2K · 1:1 (in hand 3:4)"], GREEN)
arrow(e, i)
e2 = card(1200, y + 50, PR + "flat_iron_pink_rush__velvet__1_nano.png", "scene (Nano)", w=290, h=290)
arrow(o, (1194, o[1]))
i2, o2 = box(1580, y + 90, 460, 220, "Sunburst · 08 inpaint", ["same crop → inpaint → stitch", "exact model shape, registered", "compare with step 1"], PURPLE)
arrow(e2, i2)
card(2120, y + 50, PR + "flat_iron_pink_rush__velvet__2_fixed_v3.png", "FINAL PRODUCT", w=290, h=290)
arrow(o2, (2114, o2[1]))
c.save("docs/conair/WORKFLOW_test20.png")
print("docs/conair/WORKFLOW_test20.png")
