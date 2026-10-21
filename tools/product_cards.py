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

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "samples", "products", "research")
HAND = os.path.join(ROOT, "samples", "products", "sheets", "hand")
OUT = os.path.join(ROOT, "samples", "products", "cards")
W, H, M, GAP = 4000, 2400, 60, 30
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
                  ("01_curling_iron/05_packshot_blue_bg_side.jpg", (0.0, 0.3, 1.0, 1.0), "low angle")],
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
                  ("02_round_brush/callouts_side_view_cool_tip_ionic_combs_aplus.png", (0.0, 0.42, 1.0, 0.68), "side")],
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
                  ("03_style_switch/callouts_body_buttons_release_coolshot_filter_aplus.jpg", (0.3, 0.3, 1.0, 0.72), "body, side")],
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


def paste_fit(canvas, im, box):
    x0, y0, x1, y1 = box
    im = im.copy()
    im.thumbnail((x1 - x0, y1 - y0), Image.LANCZOS)
    canvas.paste(im, (x0 + (x1 - x0 - im.width) // 2, y0 + (y1 - y0 - im.height) // 2))


def column(canvas, d, items, x0, x1, top, bottom, f_small):
    n = len(items)
    hh = (bottom - top - GAP * (n - 1)) // n
    for i, (rel, crop, label) in enumerate(items):
        y = top + i * (hh + GAP)
        lab = 40 if d else 0
        paste_fit(canvas, load(rel, crop), (x0, y, x1, y + hh - lab))
        if d:
            d.text((x0, y + hh - 34), label, font=f_small, fill=(120, 124, 132))


def card(spec, labels):
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c) if labels else None
    top = 170 if labels else M
    bottom = H - (440 if labels else M)
    f_title, f_txt, f_small, f_head = (ImageFont.truetype(BOLD, 64), ImageFont.truetype(FONT, 36),
                                       ImageFont.truetype(FONT, 28), ImageFont.truetype(BOLD, 30))
    # hero | other views | hand | details
    paste_fit(c, load(*spec["hero"][:2]), (M, top, 1400, bottom - (40 if labels else 0)))
    column(c, d, spec["views"], 1440, 2100, top, bottom, f_small)
    paste_fit(c, Image.open(os.path.join(HAND, spec["hand"])).convert("RGB"), (2140, top, 3160, bottom - (40 if labels else 0)))
    column(c, d, spec["details"], 3200, W - M, top, bottom, f_small)
    if labels:
        d.text((M, 50), spec["title"], font=f_title, fill=(18, 20, 26))
        d.text((M, bottom - 34), spec["hero"][2], font=f_small, fill=(120, 124, 132))
        d.text((2140, bottom - 34), "Hand + product at true scale (generated reference, the only generated image)",
               font=f_small, fill=(255, 106, 0))
        y0 = bottom + 50
        d.text((M, y0), "SIZES", font=f_head, fill=(255, 106, 0))
        for i, line in enumerate(spec["sizes"]):
            d.text((M, y0 + 50 + i * 54), line, font=f_txt, fill=(40, 44, 52))
        x = 2140
        d.text((x, y0), "COLOUR AND MATERIAL", font=f_head, fill=(255, 106, 0))
        for i, (name, hexv) in enumerate(spec["colours"]):
            yy = y0 + 50 + i * 66
            d.rounded_rectangle((x, yy, x + 52, yy + 52), radius=10, fill=hexv, outline=(200, 200, 200))
            d.text((x + 72, yy + 4), f"{name}  {hexv}", font=f_txt, fill=(40, 44, 52))
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, spec in CARDS.items():
        card(spec, True).save(os.path.join(OUT, f"{key}_card.png"))
        card(spec, False).save(os.path.join(OUT, f"{key}_card_clean.png"))
        print("wrote", key)


if __name__ == "__main__":
    main()
