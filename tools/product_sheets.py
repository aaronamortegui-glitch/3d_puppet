"""Compose one product reference sheet per product (input for image generation).

    server\\.venv\\Scripts\\python.exe tools\\product_sheets.py

Reads the product research images in samples/products/research/ and the generated
hand references in samples/products/sheets/hand/, and writes to samples/products/sheets/:
  <id>_sheet.png         labelled sheet (name, sizes, colours, grip) for people
  <id>_sheet_clean.png   the same images without any text, to pass to an image model
"""

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "samples", "products", "research")
OUT = os.path.join(ROOT, "samples", "products", "sheets")
W, H, M = 3600, 2400, 60
FONT = "C:/Windows/Fonts/segoeui.ttf"
BOLD = "C:/Windows/Fonts/segoeuib.ttf"

# image: (relative path, crop box as fractions x0, y0, x1, y1 or None)
SHEETS = {
    "01_auto_curler": {
        "title": "BaBylissPRO The Auto Curler 1\"  ·  BNTAC100",
        "colours": [("Nano Blue handle", "#248EA6"), ("Titanium barrel", "#8A8580"), ("Clamp", "#4A4A4E")],
        "hero": ("01_curling_iron/01_packshot_white_3q.jpg", None),
        "hand": "01_auto_curler_hand.png",
        "details": [("01_curling_iron/06_packshot_left_side_silo_BNTAC100C_pearlon.jpg", None),
                    ("01_curling_iron/closeup_handle_controls_led_heat_buttons_aplus.png", None),
                    ("01_curling_iron/packshot_front_vertical_buttons_black_bg_ulta.jpg", None)],
        "facts": ["Automatic ROTATING curling iron: the barrel turns and wraps the hair by itself",
                  "Overall 36.5 cm  ·  barrel 2.5 cm (1\") x 14 cm  ·  clamp 7.6 cm  ·  handle ~3 cm thick  ·  567 g",
                  "Held like a curling iron, barrel up; clamp lever and direction / Home buttons just below the clamp",
                  "Creates classic defined curls; best on straight and wavy hair (types 1-2)"],
    },
    "02_thermal_brush": {
        "title": "BaBylissPRO The Thermal Round Brush 1¼\"  ·  BNTHTB125",
        "colours": [("Nano Blue", "#308FBE"), ("Barrel", "#3C3F44"), ("Bristles", "#111111")],
        "hero": ("02_round_brush/01_packshot_white_front.jpg", None),
        "hand": "02_thermal_brush_hand.png",
        "details": [("02_round_brush/packshot_front_vertical_black_bg_ulta.jpg", None),
                    ("02_round_brush/03_closeup_ionic_button_in_hand.jpg", (0, 0.3, 1, 1)),
                    ("02_round_brush/closeup_cord_end_swivel_hang_loop_aplus.png", None)],
        "facts": ["Heated round brush for DRY hair: heated combs + nylon bristles, ionic button, cool tip",
                  "Overall 36.5 cm  ·  barrel core 3.2 cm (1¼\"), ~6 cm across the bristles  ·  handle ~3 cm  ·  726 g",
                  "Held low on the handle, brush angled up; hair wrapped ~1.5 turns around the bristles",
                  "Creates a polished blowout, volume and bent ends; smooths curly hair (types 1-3)"],
    },
    "03_style_switch": {
        "title": "BaBylissPRO The Style/Switch 5-in-1  ·  BNTSSSW (1½\" air-curling barrel)",
        "colours": [("Nano Blue body", "#2D8AB0"), ("Chrome panel", "#C9CED3"), ("Barrel", "#212123")],
        "hero": ("03_style_switch/01_packshot_all_attachments.jpg", None),
        "hand": "03_style_switch_hand.png",
        "details": [("03_style_switch/closeup_air_curling_barrels_pair_bidirectional_aplus.jpg", None),
                    ("03_style_switch/closeup_body_top_attachment_lock_markers_aplus.jpg", None),
                    ("03_style_switch/packshot_kit_curly_coily_with_diffuser_CC_amazon.jpg", None)],
        "facts": ["Air styler (110,000 RPM, max 257 °F): dries and styles with air; attachments twist-lock on the body",
                  "Body 20.3 x 5.1 cm  ·  with air curler ~34 cm  ·  air-curling barrel 3.8 cm (1½\")  ·  round brush 4.4 cm",
                  "The body is the handle, held vertically, attachment up; the Coanda airflow wraps the hair round the barrel",
                  "Air curlers: blowout curls and waves; round brush: volume; paddle: sleek; diffuser (C&C kit): defined curls"],
    },
    "05_flat_iron_pink": {
        "title": "BaBylissPRO Nano Titanium Ultra-Sleek 1½\" Flat Iron  ·  BNT131THP Pink Rush",
        "colours": [("Pink Rush", "#EB437C"), ("Plates", "#C8CBD0"), ("Cord", "#111111")],
        "hero": ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", None),
        "hand": "05_flat_iron_pink_hand.png",
        "details": [("05_flat_iron/guide_heat_settings_by_hair_type_1a_to_4c_pink_rush_amazon.jpg", (0, 0.62, 1, 0.97)),
                    ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", None)],
        "clean_details": 1,
        "facts": ["Flat iron / straightener with floating Nano Titanium plates, 5 settings up to 450 °F",
                  "Overall 34 cm  ·  6.4 cm wide at the plates  ·  plates 3.8 cm (1½\") wide  ·  544 g",
                  "Held around both arms below the plates, squeezed to close; hinge and cord at the bottom",
                  "Creates sleek straight hair on every type (1A-4C); waves or curls by twisting. Also in Nano Blue (right)"],
    },
    "05_flat_iron_blue": {
        "title": "BaBylissPRO Nano Titanium Ultra-Sleek 1½\" Flat Iron  ·  BNT131T-N Nano Blue",
        "colours": [("Nano Blue", "#68A4CB"), ("Plates", "#C8CBD0"), ("Cord", "#111111")],
        "hero": ("05_flat_iron/03_packshot_nano_blue_BNT131T-N.jpg", None),
        "hand": "05_flat_iron_blue_hand.png",
        "details": [("05_flat_iron/in_hand_adjustable_heat_led_nano_blue_amazon.jpg", (0, 0.28, 1, 1)),
                    ("05_flat_iron/01_packshot_pink_rush_BNT131THP.jpg", None)],
        "clean_details": 1,
        "facts": ["Flat iron / straightener with floating Nano Titanium plates, 5 settings up to 450 °F",
                  "Overall 34 cm  ·  6.4 cm wide at the plates  ·  plates 3.8 cm (1½\") wide  ·  522 g",
                  "Held around both arms below the plates, squeezed to close; hinge and cord at the bottom",
                  "Creates sleek straight hair on every type (1A-4C); waves or curls by twisting. Also in Pink Rush (right)"],
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


def sheet(key, spec, labels):
    c = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(c)
    top = 220 if labels else M
    bottom = H - (330 if labels else M)
    hero = (M, top, 1500, bottom)
    hand = (1560, top, 2500, bottom)
    paste_fit(c, load(*spec["hero"]), hero)
    paste_fit(c, Image.open(os.path.join(OUT, "hand", spec["hand"])).convert("RGB"), hand)
    # the other colour of the flat iron is a note for people, not model input
    details = spec["details"] if labels else spec["details"][:spec.get("clean_details", len(spec["details"]))]
    n = len(details)
    gap = 30
    hh = (bottom - top - gap * (n - 1)) // n
    for i, det in enumerate(details):
        y = top + i * (hh + gap)
        paste_fit(c, load(*det), (2560, y, W - M, y + hh))
    if labels:
        f_title, f_txt, f_small = ImageFont.truetype(BOLD, 64), ImageFont.truetype(FONT, 38), ImageFont.truetype(BOLD, 30)
        d.text((M, 50), spec["title"], font=f_title, fill=(18, 20, 26))
        x = M
        for name, hexv in spec["colours"]:
            d.ellipse((x, 150, x + 44, 194), fill=hexv, outline=(200, 200, 200))
            d.text((x + 56, 152), f"{name} {hexv}", font=f_small, fill=(90, 95, 105))
            x += 70 + d.textlength(f"{name} {hexv}", font=f_small) + 40
        d.text((hand[0], bottom + 10), "Hand + product at true scale (generated reference)", font=f_small, fill=(255, 106, 0))
        for i, line in enumerate(spec["facts"]):
            d.text((M, bottom + 70 + i * 60), "•  " + line, font=f_txt, fill=(40, 44, 52))
    return c


def main():
    os.makedirs(OUT, exist_ok=True)
    for key, spec in SHEETS.items():
        sheet(key, spec, True).save(os.path.join(OUT, f"{key}_sheet.png"))
        sheet(key, spec, False).save(os.path.join(OUT, f"{key}_sheet_clean.png"))
        print("wrote", key)


if __name__ == "__main__":
    main()
