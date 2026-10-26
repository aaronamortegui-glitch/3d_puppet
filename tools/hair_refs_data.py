"""Writes docs/products/hair_refs.json: the 58 real before/after hair references (FigJam CONAIR 115:115), classified by SKU and rule."""
import json
from collections import Counter

# id, figjam node, sku, rule, before type, after look, view, layout, photo, grade, note
ROWS = [
    ("r01", "115:116", "style_switch_air_curl", "SS_t2_aircurl", "2B", "defined loose waves", "back", "split", "real", "C", "colour gets darker in the after"),
    ("r02", "115:120", "flat_iron", "FI_t2", "2A", "glass-straight", "back", "pair", "real", "B", "stylist hands in frame"),
    ("r03", "115:124", "flat_iron", "FI_t2", "2A", "glass-straight", "back", "pair", "real", "A", ""),
    ("r04", "115:128", "flat_iron", "FI_t2", "2A", "glossy straight", "back", "pair", "real", "A", "BEFORE/AFTER text"),
    ("r05", "115:132", "style_switch_air_curl", "SS_t2_aircurl", "2C-3A", "big smooth waves", "profile", "split", "ai_look", "C", "curly before; profile view"),
    ("r06", "115:136", "flat_iron", "FI_t2", "2A", "glass-straight", "front", "split", "ai_look", "C", "face covered by hair"),
    ("r07", "115:140", "style_switch_air_curl", "SS_t2_aircurl", "2B", "smooth waves", "profile", "split", "ai_look", "C", "profile view"),
    ("r08", "115:144", "style_switch_air_curl", "SS_t2_aircurl", "3A", "smooth waves", "profile", "split", "ai_look", "C", "profile view; curly before"),
    ("r09", "115:148", "style_switch_air_curl", "SS_t2_aircurl", "2B", "glossy waves", "front", "split", "ai_look", "C", "face covered by hair"),
    ("r10", "115:152", "style_switch_air_curl", "SS_t2_aircurl", "2B", "glossy waves", "front", "split", "ai_look", "B", ""),
    ("r11", "115:156", "flat_iron", "FI_t1", "1-2A", "glass-straight", "profile", "pair", "ai_look", "C", "profile view"),
    ("r12", "115:160", "style_switch_air_curl", "SS_t2_aircurl", "2B", "glossy defined waves", "front", "split", "ai_look", "B", "text callouts"),
    ("r13", "115:164", "style_switch_air_curl", "SS_t2_aircurl", "2A", "soft waves", "front", "split", "ai_look", "B", "AFTER text"),
    ("r14", "115:171", "thermal_brush", "TB_t2", "2C", "smooth blowout, bent ends", "front", "pair", "real", "A", "BEFORE/AFTER text"),
    ("r15", "115:175", "thermal_brush", "TB_t2", "2A", "polished blowout, soft bend", "three_quarter_back", "pair", "ai_look", "B", ""),
    ("r16", "115:179", "flat_iron", "FI_t1_waves", "2A", "loose S-waves", "back", "split", "real", "B", ""),
    ("r17", "115:186", "style_switch_diffuser", "SS_t3_diffuser", "3B", "defined curls, less frizz", "back", "split", "real", "A", ""),
    ("r18", "115:190", "style_switch_diffuser", "SS_t4_diffuser", "3C-4A", "defined coils", "back", "split", "real", "A", ""),
    ("r19", "115:194", "flat_iron", "FI_t3", "2C-3A", "glass-straight", "back", "pair", "real", "A", ""),
    ("r20", "115:198", "flat_iron", "FI_t2", "2B", "straight", "back", "pair", "real", "B", "colour toned in the after"),
    ("r21", "115:211", "flat_iron", "FI_t2", "2B", "smooth straight", "back", "pair", "real", "A", ""),
    ("r22", "115:215", "flat_iron", "FI_t2", "2C", "glass-straight", "back", "pair", "real", "B", "colour toned in the after"),
    ("r23", "115:219", "flat_iron", "FI_t3", "3A", "glass-straight", "back", "pair", "ai_look", "B", ""),
    ("r24", "115:223", "flat_iron", "FI_t2", "2C", "glass-straight", "back", "pair", "ai_look", "B", ""),
    ("r25", "115:227", "thermal_brush", "TB_t2", "2A", "smooth glossy blowout with movement", "back", "pair", "ai_look", "B", ""),
    ("r26", "115:231", "auto_curler", "AC_t1", "1", "glossy defined curls", "back", "pair", "real", "A", "AFTER text"),
    ("r27", "115:235", "flat_iron", "FI_t2", "2A", "straight", "back", "pair", "real", "C", "small, far, salon mirror"),
    ("r28", "115:245", "style_switch_air_curl", "SS_t1_aircurl", "1", "glossy loose waves", "back", "pair", "ai_look", "B", ""),
    ("r29", "115:249", "flat_iron", "FI_t1", "1-2A", "glass-straight", "profile", "pair", "ai_look", "C", "profile view"),
    ("r30", "115:253", "style_switch_paddle", "SS_t2_paddle", "2A", "smooth straight blow-dry", "front", "pair", "real", "B", "Cyrillic text"),
    ("r31", "115:257", "flat_iron", "FI_t2", "2B", "glass-straight", "front", "pair", "ai_look", "B", ""),
    ("r32", "115:261", "flat_iron", "FI_t2", "2B", "glossy straight", "front", "split", "ai_look", "B", "salon background"),
    ("r33", "115:265", "flat_iron", "FI_t2", "2A", "glossy straight", "front", "split", "ai_look", "C", "HD badge"),
    ("r34", "115:269", "style_switch_paddle", "SS_t2_paddle", "2A", "smooth straight blow-dry", "front", "pair", "ai_look", "B", "BEFORE/AFTER text"),
    ("r35", "115:273", "style_switch_air_curl", "SS_t2_aircurl", "2A", "glossy curled ends", "front", "pair", "ai_look", "B", "BEFORE/AFTER text"),
    ("r36", "115:277", "flat_iron", "FI_t1", "1-2A", "sleek straight", "front", "pair", "real", "A", "Before/After text"),
    ("r37", "115:281", "style_switch_diffuser", "SS_t3_diffuser", "3A", "looser curls, less frizz", "front", "pair", "real", "B", "Before/After text"),
    ("r38", "115:285", "style_switch_round_brush", "SS_t1_roundbrush", "1", "voluminous blowout, flipped ends", "front", "pair", "real", "A", "Before/After text"),
    ("r39", "115:292", "style_switch_round_brush", "SS_t2_roundbrush", "2A", "voluminous bouncy blowout", "front", "pair", "real", "A", "AFTER text"),
    ("r40", "115:296", "flat_iron", "FI_t1", "1", "sleek straight", "front", "pair", "real", "A", "Before/After UI labels"),
    ("r41", "115:300", "thermal_brush", "TB_t3", "3A", "smooth blowout with bend", "front", "pair", "real", "A", "text labels"),
    ("r42", "119:304", "thermal_brush", "TB_t2", "2A", "smooth blowout with bend", "front", "pair", "real", "B", "small (500 px)"),
    ("r43", "119:308", "auto_curler", "AC_t1", "1", "big defined curls", "three_quarter", "pair", "real", "A", "AFTER text"),
    ("r44", "119:312", "style_switch_air_curl", "SS_t2_aircurl", "2C", "defined smooth waves", "front", "pair", "real", "B", ""),
    ("r45", "119:316", "auto_curler", "AC_t2", "2B", "glossy defined curls", "back+front", "grid_2x2", "real", "A", "back and front view in one image"),
    ("r46", "119:323", "thermal_brush", "TB_t1", "1-2A", "smooth blowout", "front", "pair", "real", "B", "BEFORE/AFTER text"),
    ("r47", "119:327", "style_switch_round_brush", "SS_t2_roundbrush", "2A", "bouncy blowout, curled ends", "front", "pair", "real", "A", "BEFORE/AFTER text"),
    ("r48", "119:331", "style_switch_round_brush", "SS_t1_roundbrush", "1", "voluminous blowout", "front", "pair", "real", "A", ""),
    ("r49", "119:335", "style_switch_air_curl", "SS_t2_aircurl", "2A", "beachy waves", "front", "pair", "real", "B", "make-up changes; BEFORE/AFTER band"),
    ("r50", "119:342", "style_switch_round_brush", "SS_t1_roundbrush", "1", "blowout with curled ends", "front", "pair", "real", "A", "BEFORE/AFTER text"),
    ("r51", "119:346", "style_switch_air_curl", "SS_t2_aircurl", "2A", "soft waves", "three_quarter", "pair", "real", "A", "text"),
    ("r52", "119:359", "auto_curler", "AC_t1", "1-2A", "bouncy curls", "front", "pair", "real", "A", ""),
    ("r53", "119:363", "style_switch_air_curl", "SS_t2_aircurl", "2B", "smoother big waves", "front", "pair", "real", "B", "subtle change"),
    ("r54", "119:367", "auto_curler", "AC_t2", "2B", "defined curls", "front", "pair", "real", "A", ""),
    ("r55", "119:371", "flat_iron", "FI_t4_silkpress", "4A", "sleek straight (silk press)", "three_quarter", "pair", "real", "A", "Prima/Dopo text"),
    ("r56", "119:375", "flat_iron", "FI_t3", "3B", "sleek straight bob", "front", "pair", "real", "B", "pose changes in the after"),
    ("r57", "119:379", "style_switch_paddle", "SS_t2_paddle", "2A", "smooth straight blow-dry", "front", "pair", "real", "A", ""),
    ("r58", "119:383", "style_switch_diffuser", "SS_t3_diffuser", "3A", "defined curls", "front", "pair", "real", "A", "AFTER text"),
]

KEYS = ("id", "node", "sku", "rule", "before", "after", "view", "layout", "photo", "grade", "note")
DOC = {
    "version": "2026-10-26",
    "source": "FigJam CONAIR-Products (2tItrDWjhCt5uVTxcyKePK) node 115:115 'Hair References': 58 images",
    "purpose": "Real before/after references of the finished hair. The after (and its before) go in as inputs for the hair style only: curl pattern, texture, shine. Colour and length come from the avatar.",
    "grades": {"A": "clean, same person, front or back view, real photo",
               "B": "usable, with a catch: AI look, text, small, or a colour change",
               "C": "weak: profile view, face hidden, tiny, or split down the face"},
    "layouts": {"pair": "two photos side by side", "split": "one photo split down the middle",
                "grid_2x2": "top row before, bottom row after"},
    "files": "outputs/10_hair_refs/refs/<id>.png (original) and split/<id>_before.png, split/<id>_after.png (gitignored, internal use)",
    "refs": [dict(zip(KEYS, r)) for r in ROWS],
}

if __name__ == "__main__":
    with open("docs/products/hair_refs.json", "w", encoding="utf-8") as f:
        json.dump(DOC, f, indent=1, ensure_ascii=False)
    print(Counter(r[2] for r in ROWS))
    print(Counter(r[9] for r in ROWS))
