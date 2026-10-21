"""Compose one product card per product and colourway (input for image generation).

    server\\.venv\\Scripts\\python.exe tools\\product_cards.py

Successor of product_sheets.py (kept as is). Rules for the cards:
  - real product photos only (packshots, product close-ups, crops of them);
  - no people and no real hands, so a card never leaks a person into a generation;
  - the only generated image is the hand-and-product reference in samples/products/sheets/hand/.

Writes to samples/products/cards/:
  <id>_card.png         labelled card (views, details, hand, sizes, colour and material) for people
  <id>_card_clean.png   the same images without any text, to pass to an image model
"""

import os

from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "samples", "products", "research")
HAND = os.path.join(ROOT, "samples", "products", "sheets", "hand")
OUT = os.path.join(ROOT, "samples", "products", "cards")
W, H, M, GAP, PAD = 4000, 2400, 60, 28, 26
FONT = "C:/Windows/Fonts/segoeui.ttf"
BOLD = "C:/Windows/Fonts/segoeuib.ttf"

# image: (relative path, crop box as fractions x0, y0, x1, y1 or None, label)
CARDS = {
    "01_auto_curler": {
        "title": "BaBylissPRO The Auto Curler 1\"  ·  BNTAC100  ·  Nano Blue",
        "hand": "01_auto_curler_hand.png",
        "hero": ("01_curling_iron/01_packshot_white_3q.jpg", None, "3/4 view"),
        "views": [("01_curling_iron/06_packshot_left_side_silo_BNTAC100C_pearlon.jpg", (0.25, 0.0, 0.85, 1.0), "side"),
                  ("01_curling_iron/packshot_front_vertical_buttons_black_bg_ulta.jpg", (0.36, 0.04, 0.64, 0.98), "front, buttons"),
                  ],
        "details": [("01_curling_iron/closeup_handle_controls_led_heat_buttons_aplus.png", None, "heat LEDs and buttons"),
                    ("01_curling_iron/callouts_side_view_clamp_buttons_speed_aplus.png", (0.0, 0.42, 1.0, 0.66), "barrel, clamp, handle"),
                    ("01_curling_iron/01_packshot_white_3q.jpg", (0.0, 0.0, 0.5, 0.45), "titanium barrel and clamp")],
        "sizes": ["Overall 36.5 cm (14.4\")", "Barrel 2.5 cm (1\") x 14 cm, rotating", "Clamp 7.6 cm (3\")",
                  "Handle ~3.0-3.4 cm thick", "567 g  ·  cord 2.4 m, swivel"],
        "colours": [("Handle: Nano Blue, satin metallic", "#248EA6"), ("Barrel: titanium, satin grey", "#8A8580"),
                    ("Clamp and lever: gunmetal, matte", "#4A4A4E"), ("Cord: black", "#111111")],
    },
    "02_thermal_brush": {
        "title": "BaBylissPRO The Thermal Round Brush 1¼\"  ·  BNTHTB125  ·  Nano Blue",
        "hand": "02_thermal_brush_hand.png",
        "hero": ("02_round_brush/01_packshot_white_front.jpg", None, "front"),
        "views": [("02_round_brush/05_packshot_blue_bg_angled.jpg", (0.0, 0.3, 1.0, 1.0), "angled"),
                  ("02_round_brush/packshot_front_vertical_black_bg_ulta.jpg", (0.3, 0.04, 0.7, 0.98), "front, ionic side"),
                  ],
        "details": [("02_round_brush/01_packshot_white_front.jpg", (0.25, 0.0, 0.75, 0.5), "bristles, heated combs, cool tip"),
                    ("02_round_brush/closeup_cord_end_swivel_hang_loop_aplus.png", None, "swivel and hang loop"),
                    ("02_round_brush/01_packshot_white_front.jpg", (0.25, 0.45, 0.75, 0.75), "collar and handle")],
        "sizes": ["Overall 36.5 cm (14.4\")", "Barrel core 3.2 cm (1¼\"), ~6 cm across bristles",
                  "Bristle section ~16-17 cm", "Handle ~2.8-3.2 cm thick", "726 g  ·  cord 2.7 m, swivel"],
        "colours": [("Body: Nano Blue, satin metallic", "#308FBE"), ("Barrel: gunmetal Nano Titanium, perforated", "#3C3F44"),
                    ("Bristles: black nylon + heated ceramic combs", "#111111"), ("Collar ring: chrome", "#C9CED3")],
    },
    "03_style_switch": {
        "title": "BaBylissPRO The Style/Switch 5-in-1  ·  BNTSSSW / BNTSSCC  ·  Nano Blue",
        "hand": "03_style_switch_hand.png",
        "hero": ("03_style_switch/01_packshot_all_attachments.jpg", None, "body + attachments (Straight & Wavy kit)"),
        "views": [("03_style_switch/packshot_kit_curly_coily_with_diffuser_CC_amazon.jpg", None, "Curly & Coily kit, diffuser"),
                  ("03_style_switch/packshot_kit_with_case_black_bg_SW_ulta.jpg", (0.1, 0.25, 0.95, 0.95), "kit and case"),
                  ],
        "details": [("03_style_switch/closeup_air_curling_barrels_pair_bidirectional_aplus.jpg", None, "1½\" air-curling barrels"),
                    ("03_style_switch/closeup_body_top_attachment_lock_markers_aplus.jpg", None, "attachment lock, buttons"),
                    ("03_style_switch/01_packshot_all_attachments.jpg", (0.31, 0.12, 0.41, 0.98), "body, chrome panel, filter")],
        "sizes": ["Body 20.3 cm x 5.1 cm (8\" x 2\")", "With air curler ~34 cm", "Air-curling barrel 3.8 cm (1½\")",
                  "Round brush 4.4 cm (1¾\")  ·  paddle ~7.5 x 16 cm", "Body ~450-550 g (est.)"],
        "colours": [("Body: Nano Blue anodised aluminium", "#2D8AB0"), ("Front panel: mirror chrome", "#C9CED3"),
                    ("Barrels and brushes: matte black", "#212123"), ("Filter: blue perforated cover", "#2D8AB0")],
    },
    "05_flat_iron_pink": {
        "title": "BaBylissPRO Nano Titanium Ultra-Sleek 1½\" Flat Iron  ·  BNT131THP  ·  Pink Rush",
        "hand": "05_flat_iron_pink_hand.png",
        "hero": ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", None, "3/4 view"),
        # the only other Pink Rush views are ad callouts whose leader lines touch the iron, so they are left out
        "views": [("05_flat_iron/guide_heat_settings_by_hair_type_1a_to_4c_pink_rush_amazon.jpg", (0.0, 0.62, 1.0, 0.97), "side, plates open")],
        "details": [("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", (0.25, 0.25, 0.75, 0.6), "LED dots and logo"),
                    ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", (0.0, 0.1, 0.45, 0.5), "plates"),
                    ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", (0.6, 0.45, 1.0, 0.95), "hinge, swivel, cord")],
        "sizes": ["Overall 34.0 cm (13⅜\")", "6.4 cm (2½\") wide at the plates", "Plates 3.8 cm (1½\") wide, ~13-15 cm long",
                  "Arms ~3.2 cm wide below the plates", "544 g  ·  cord 2.7 m, swivel"],
        "colours": [("Body: Pink Rush, soft-touch matte", "#EB437C"), ("Plates: polished Nano Titanium", "#C8CBD0"),
                    ("Hinge ring: chrome", "#C9CED3"), ("Cord: black", "#111111")],
    },
    "05_flat_iron_blue": {
        "title": "BaBylissPRO Nano Titanium Ultra-Sleek 1½\" Flat Iron  ·  BNT131T-N  ·  Nano Blue",
        "hand": "05_flat_iron_blue_hand.png",
        "hero": ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", None, "3/4 view"),
        "views": [("05_flat_iron/06_dimensions_nano_blue.jpg", (0.45, 0.17, 0.62, 0.86), "front, closed"),
                  ("05_flat_iron/guide_heat_285_to_430_by_hair_type_nano_blue_aplus.png", (0.05, 0.10, 0.40, 0.90), "LED heat dots")],
        "details": [("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", (0.0, 0.0, 0.5, 0.45), "plates"),
                    ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", (0.3, 0.2, 0.75, 0.65), "LED dots and logo"),
                    ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", (0.55, 0.5, 1.0, 1.0), "hinge, swivel, cord")],
        "sizes": ["Overall 34.0 cm (13⅜\")", "6.4 cm (2½\") wide at the plates", "Plates 3.8 cm (1½\") wide, ~13-15 cm long",
                  "Arms ~3.2 cm wide below the plates", "522 g  ·  cord 2.7 m, swivel"],
        "colours": [("Body: Nano Blue, metallic", "#68A4CB"), ("Plates: polished Nano Titanium", "#C8CBD0"),
                    ("Hinge ring: chrome", "#C9CED3"), ("Cord: black", "#111111")],
    },
}


def load(rel, crop):
    im = Image.open(os.path.join(RES, rel)).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
    return im


def background(im):
    px = im.load()
    w, h = im.size
    corners = [px[2, 2], px[w - 3, 2], px[2, h - 3], px[w - 3, h - 3]]
    bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))
    # a crop whose corners land on the product has no real background: use white
    if sum(max(abs(a - b) for a, b in zip(c, bg)) < 24 for c in corners) < 3:
        return (255, 255, 255)
    return bg


def trim(im, pad=0.04):
    """Crop away the empty background around the product (corner colour), keeping a small margin."""
    w, h = im.size
    bg = background(im)
    if bg == (255, 255, 255) and min(im.getpixel((2, 2))) < 240:
        return im
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(lambda v: 255 if v > 22 else 0)
    box = diff.getbbox()
    if not box:
        return im
    px_, py_ = int((box[2] - box[0]) * pad), int((box[3] - box[1]) * pad)
    return im.crop((max(0, box[0] - px_), max(0, box[1] - py_), min(w, box[2] + px_), min(h, box[3] + py_)))


def clamp(a, lo, hi):
    return max(lo, min(hi, a))


TAGS = {"VIEW": (52, 96, 140), "DETAIL": (255, 106, 0), "SCALE": (124, 58, 237)}


def tile(c, d, im, box, tag, label, fonts):
    """Grey rounded tile with the image contained inside; on the labelled card a tag chip and caption on top."""
    x0, y0, x1, y1 = box
    ImageDraw.Draw(c).rounded_rectangle(box, radius=22, fill=background(im), outline=(222, 224, 228), width=3)
    top = y0 + (64 if d else 0)
    # contain, allowing up to 2.5x upscaling so small close-ups fill their tile
    k = min((x1 - x0 - 2 * PAD) / im.width, (y1 - top - 2 * PAD) / im.height, 2.5)
    im = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    c.paste(im, (x0 + (x1 - x0 - im.width) // 2, top + (y1 - top - im.height) // 2))
    if d:
        f_tag, f_cap = fonts
        tw = d.textlength(tag, font=f_tag)
        d.rounded_rectangle((x0 + 18, y0 + 16, x0 + 18 + tw + 28, y0 + 54), radius=10, fill=TAGS[tag])
        d.text((x0 + 32, y0 + 19), tag, font=f_tag, fill="white")
        cap_w = d.textlength(label, font=f_cap)
        d.rounded_rectangle((x0 + 18 + tw + 34, y0 + 16, x0 + 18 + tw + 54 + cap_w, y0 + 54), radius=10, fill="white")
        d.text((x0 + 18 + tw + 44, y0 + 18), label, font=f_cap, fill=(90, 95, 105))


def row_widths(aspects, height, avail, fixed=0):
    """Widths proportional to each image's aspect at the row height, scaled to fill the row exactly."""
    nat = [a * height for a in aspects]
    free = avail - fixed - GAP * (len(aspects) - (0 if fixed else 1))
    k = free / sum(nat)
    return [int(n * k) for n in nat]


def card(spec, labels):
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c) if labels else None
    f_title, f_txt, f_head = ImageFont.truetype(BOLD, 60), ImageFont.truetype(FONT, 34), ImageFont.truetype(BOLD, 28)
    fonts = (ImageFont.truetype(BOLD, 24), ImageFont.truetype(FONT, 26))
    top = 150 if labels else M
    bottom = H - M
    avail = W - 2 * M
    r1 = int((bottom - top - GAP) * 0.62)
    r2 = bottom - top - GAP - r1
    lab = 64 if labels else 0

    # row 1: main view | other views stacked | hand (scale)
    hero = trim(load(*spec["hero"][:2]))
    hand = trim(Image.open(os.path.join(HAND, spec["hand"])).convert("RGB"))
    views = [(trim(load(r, b)), t) for r, b, t in spec["views"]]
    # widths: hand gets a fixed share so the scale reference is always readable; the stacked views get the
    # width their images need (within limits); the main view takes the rest
    hs = [1 / clamp(v.width / v.height, 0.5, 3.2) for v, _ in views]
    col_nat = (r1 - GAP * (len(hs) - 1)) / sum(hs)
    wn = int(avail * 0.27)
    wc = int(clamp(col_nat, avail * 0.2, avail * 0.36))
    wh = avail - wn - wc - 2 * GAP
    x = M
    tile(c, d, hero, (x, top, x + wh, top + r1), "VIEW", spec["hero"][2], fonts)
    x += wh + GAP
    yy, free = top, r1 - GAP * (len(views) - 1)
    for i, (v, t) in enumerate(views):
        hh = free - (yy - top - GAP * i) if i == len(views) - 1 else int(free * hs[i] / sum(hs))
        tile(c, d, v, (x, yy, x + wc, yy + hh), "VIEW", t, fonts)
        yy += hh + GAP
    x += wc + GAP
    tile(c, d, hand, (x, top, M + avail, top + r1), "SCALE", "hand + product, generated", fonts)

    # row 2: details | sizes and colours (labelled card only)
    y2 = top + r1 + GAP
    det = [(trim(load(r, b)), t) for r, b, t in spec["details"]]
    spec_w = 1250 if labels else 0
    ws = row_widths([clamp(i.width / i.height, 0.8, 1.8) for i, _ in det], r2, avail, spec_w + GAP if labels else 0)
    x = M
    for (im, t), w in zip(det, ws):
        tile(c, d, im, (x, y2, x + w, bottom), "DETAIL", t, fonts)
        x += w + GAP
    if labels:
        bx = M + avail - spec_w
        d.rounded_rectangle((bx, y2, M + avail, bottom), radius=22, outline=(225, 227, 231), width=3)
        d.text((M, 46), spec["title"], font=f_title, fill=(18, 20, 26))
        d.text((bx + 36, y2 + 30), "SIZES", font=f_head, fill=(255, 106, 0))
        for i, line in enumerate(spec["sizes"]):
            d.text((bx + 36, y2 + 74 + i * 46), line, font=f_txt, fill=(40, 44, 52))
        cy = y2 + 74 + len(spec["sizes"]) * 46 + 24
        d.text((bx + 36, cy), "COLOUR AND MATERIAL", font=f_head, fill=(255, 106, 0))
        for i, (name, hexv) in enumerate(spec["colours"]):
            yy = cy + 44 + i * 54
            d.rounded_rectangle((bx + 36, yy, bx + 80, yy + 44), radius=8, fill=hexv, outline=(200, 200, 200))
            d.text((bx + 96, yy + 2), f"{name}  {hexv}", font=ImageFont.truetype(FONT, 28), fill=(40, 44, 52))
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, spec in CARDS.items():
        card(spec, True).save(os.path.join(OUT, f"{key}_card.png"))
        card(spec, False).save(os.path.join(OUT, f"{key}_card_clean.png"))
        print("wrote", key)


if __name__ == "__main__":
    main()
