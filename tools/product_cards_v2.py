"""Product sheet v2 (test 20): the model input for every generation and product fix.

    python tools/product_cards_v2.py

What changed from tools/product_cards.py (kept as is):
  - 6000 x 3600 px (long side >= 5K), so the logo, LEDs and buttons stay readable after the model downscales;
  - every photo comes from samples/products/research_6k/: the same real photos, upscaled x4 by Topaz Standard
    High Fidelity V2 (faithful, no invented detail; job ids in outputs/uploads_card_sources.json);
  - it is labelled: sizes, colours and a LOGO line saying where the wordmark sits and which way it reads,
    because the products kept coming out with the logo on the wrong side (review of 2026-10-27);
  - a dedicated LOGO detail tile.
Writes samples/products/cards_v2/<id>_card_v2.png; build_library.py copies it to library/products/<sku>/<colour>/card_v2.png.
"""
import os

from PIL import Image, ImageDraw, ImageFont

import product_cards as V1

ROOT = V1.ROOT
RES6K = os.path.join(ROOT, "samples", "products", "research_6k")
OUT = os.path.join(ROOT, "samples", "products", "cards_v2")
S = 1.5
W, H = 6000, 3600
M, GAP, PAD = int(60 * S), int(28 * S), int(26 * S)

LOGO = {  # where the wordmark sits, read on the packshots (review 2026-10-27: the logo kept moving sides)
    "01_auto_curler": ("LOGO", "White BaBylissPRO wordmark lengthwise on the front face of the blue handle, reading from the barrel toward the cord; "
                               "heat LEDs and the +/- buttons on the same face below it."),
    "02_thermal_brush": ("LOGO", "White BaBylissPRO wordmark lengthwise on the front face of the blue handle, reading from the collar toward the cord."),
    "03_style_switch": ("LOGO", "BaBylissPRO wordmark lengthwise on the blue body; the buttons sit on the mirror-chrome front panel."),
    "05_flat_iron_pink": ("LOGO", "White BaBylissPRO / NANO TITANIUM wordmark on the outer face of one arm, between the plates and the hinge, "
                                  "reading toward the plates; LED heat dots and 3 buttons on the side of the same arm."),
    "05_flat_iron_blue": ("LOGO", "White BaBylissPRO / NANO TITANIUM wordmark on the outer face of one arm, between the plates and the hinge, "
                                  "reading toward the plates; red LED heat dots and 3 buttons on the side of the same arm."),
    "05_flat_iron_iced": ("LOGO", "White BaBylissPRO / NANO TITANIUM wordmark on the outer face of one arm, between the plates and the hinge, "
                                  "reading toward the plates; LED heat dots and 3 buttons on the side of the same arm."),
}
LOGO_CROP = {  # detail tile on the wordmark: (relative path, crop)
    "01_auto_curler": ("01_curling_iron/01_packshot_white_3q.jpg", (0.45, 0.35, 0.95, 0.95)),
    "02_thermal_brush": ("02_round_brush/01_packshot_white_front.jpg", (0.3, 0.45, 0.7, 0.9)),
    "03_style_switch": ("03_style_switch/01_packshot_all_attachments.jpg", (0.31, 0.12, 0.41, 0.98)),
    "05_flat_iron_pink": ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", (0.35, 0.25, 0.8, 0.7)),
    "05_flat_iron_blue": ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", (0.35, 0.25, 0.8, 0.7)),
    "05_flat_iron_iced": ("05_flat_iron/iced_blue/01_packshot_iced_blue_BNT131TLB_amazon.jpg", (0.4, 0.3, 0.9, 0.75)),
}


def load(rel, crop):
    """The x4 upscale when it exists, else the original photo."""
    p6 = os.path.join(RES6K, os.path.splitext(rel)[0] + ".png")
    im = Image.open(p6 if os.path.exists(p6) else os.path.join(V1.RES, rel)).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    return im


def F(path, size):
    return ImageFont.truetype(path, int(size * S))


def tile(c, d, im, box, tag, label):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, radius=int(22 * S), fill=V1.background(im), outline=(222, 224, 228), width=4)
    top = y0 + int(64 * S)
    k = min((x1 - x0 - 2 * PAD) / im.width, (y1 - top - 2 * PAD) / im.height, 2.5)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    c.paste(im, (x0 + (x1 - x0 - im.width) // 2, top + (y1 - top - im.height) // 2))
    f_tag, f_cap = F(V1.BOLD, 24), F(V1.FONT, 26)
    tw = d.textlength(tag, font=f_tag)
    p = int(18 * S)
    d.rounded_rectangle((x0 + p, y0 + p, x0 + p + tw + 28 * S, y0 + 56 * S), radius=int(10 * S),
                        fill=V1.TAGS.get(tag, (0, 140, 90)))
    d.text((x0 + p + 14 * S, y0 + p + 3 * S), tag, font=f_tag, fill="white")
    cw = d.textlength(label, font=f_cap)
    d.rounded_rectangle((x0 + p + tw + 36 * S, y0 + p, x0 + p + tw + 58 * S + cw, y0 + 56 * S), radius=int(10 * S), fill="white")
    d.text((x0 + p + tw + 46 * S, y0 + p + 2 * S), label, font=f_cap, fill=(90, 95, 105))


def card(key, spec):
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    top, bottom, avail = int(150 * S), H - M, W - 2 * M
    r1 = int((bottom - top - GAP) * 0.58)
    r2 = bottom - top - GAP - r1
    hero = V1.trim(load(*spec["hero"][:2]))
    hand = V1.trim(Image.open(os.path.join(V1.HAND, spec["hand"])).convert("RGB"))
    views = [(V1.trim(load(r, b)), t) for r, b, t in spec["views"]]
    hs = [1 / V1.clamp(v.width / v.height, 0.5, 3.2) for v, _ in views]
    col_nat = (r1 - GAP * (len(hs) - 1)) / sum(hs)
    wn = int(avail * 0.24)
    wc = int(V1.clamp(col_nat, avail * 0.2, avail * 0.34))
    wh = avail - wn - wc - 2 * GAP
    x = M
    tile(c, d, hero, (x, top, x + wh, top + r1), "VIEW", spec["hero"][2])
    x += wh + GAP
    yy, free = top, r1 - GAP * (len(views) - 1)
    for i, (v, t) in enumerate(views):
        hh = free - (yy - top - GAP * i) if i == len(views) - 1 else int(free * hs[i] / sum(hs))
        tile(c, d, v, (x, yy, x + wc, yy + hh), "VIEW", t)
        yy += hh + GAP
    x += wc + GAP
    tile(c, d, hand, (x, top, M + avail, top + r1), "SCALE", "hand + product (size reference)")
    y2 = top + r1 + GAP
    det = [(V1.trim(load(r, b)), t, "DETAIL") for r, b, t in spec["details"]]
    det.append((load(*LOGO_CROP[key]), "wordmark position and direction", "LOGO"))
    spec_w = int(1500 * S)
    ws = V1.row_widths([V1.clamp(i.width / i.height, 0.7, 1.6) for i, _, _ in det], r2, avail, spec_w + GAP)
    x = M
    for (im, t, tag), w in zip(det, ws):
        tile(c, d, im, (x, y2, x + w, bottom), tag, t)
        x += w + GAP
    bx = M + avail - spec_w
    d.rounded_rectangle((bx, y2, M + avail, bottom), radius=int(22 * S), outline=(225, 227, 231), width=4)
    d.text((M, int(40 * S)), spec["title"], font=F(V1.BOLD, 64), fill=(18, 20, 26))
    f_h, f_t = F(V1.BOLD, 30), F(V1.FONT, 34)
    yy = y2 + int(30 * S)
    d.text((bx + 36 * S, yy), "SIZES", font=f_h, fill=(255, 106, 0))
    yy += int(46 * S)
    for line in spec["sizes"]:
        d.text((bx + 36 * S, yy), line, font=f_t, fill=(40, 44, 52))
        yy += int(46 * S)
    yy += int(16 * S)
    d.text((bx + 36 * S, yy), "COLOUR AND MATERIAL", font=f_h, fill=(255, 106, 0))
    yy += int(46 * S)
    for name, hexv in spec["colours"]:
        d.rounded_rectangle((bx + 36 * S, yy, bx + 80 * S, yy + 44 * S), radius=int(8 * S), fill=hexv, outline=(200, 200, 200))
        d.text((bx + 96 * S, yy + 2 * S), f"{name}  {hexv}", font=F(V1.FONT, 30), fill=(40, 44, 52))
        yy += int(54 * S)
    yy += int(16 * S)
    d.text((bx + 36 * S, yy), "LOGO", font=f_h, fill=(0, 140, 90))
    yy += int(46 * S)
    words, line = LOGO[key][1].split(), ""
    f_l = F(V1.FONT, 30)
    for wd in words:  # wrap to the panel width
        t = (line + " " + wd).strip()
        if d.textlength(t, font=f_l) > spec_w - 72 * S:
            d.text((bx + 36 * S, yy), line, font=f_l, fill=(40, 44, 52))
            yy += int(40 * S)
            line = wd
        else:
            line = t
    d.text((bx + 36 * S, yy), line, font=f_l, fill=(40, 44, 52))
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, spec in V1.CARDS.items():
        card(key, spec).save(os.path.join(OUT, f"{key}_card_v2.png"))
        print("wrote", key)


if __name__ == "__main__":
    main()
