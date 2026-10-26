# Real hair references and client avatars (2026-10-26)

## What this is

**Hair references.** These are the 58 real before/after hair photos from the CONAIR FigJam, page "Hair References" (node 115:115).
- Each one is classified by the SKU that gives that look.
- Each one is split into a **before** file and an **after** file.

The after is the input for the hair *style* only: curl pattern, texture and shine. Colour and length still come from the avatar.

**Avatars.** The 10 client avatars from `new_client/Avatars - After` are now in the library.

**Selection.** None of the references is picked yet: we choose which ones to use together after reviewing the board.

| | Where |
|---|---|
| Board | FigJam CONAIR-Products, page "Hair References", section "Hair references by category" (146:60), right of the original references |
| Classification | [hair_refs.json](../products/hair_refs.json), written by `tools/hair_refs_data.py` |
| Images | `outputs/10_hair_refs/refs/<id>.png` (original) and `split/<id>_before.png`, `split/<id>_after.png`, made by `tools/split_hair_refs.py` (gitignored, internal use) |
| Avatars | `library/avatars/client_a01..a10/` (`front.png` + `meta.json`), made by `tools/add_client_avatars.py` |

## How the references are graded

| Grade | Meaning | Count |
|---|---|---|
| A | Clean real photo, same person, front or back view | 24 |
| B | Usable, with a catch: AI look, text on the image, small, or a colour change | 24 |
| C | Weak: profile view, face hidden, tiny, or split down the face | 10 |

## References per category

| Category | Refs | Grade A |
|---|---|---|
| Auto Curler | 5 | r26, r43, r45, r52, r54 |
| Thermal Brush | 6 | r14, r41 |
| Style/Switch round brush | 5 | r38, r39, r47, r48, r50 |
| Style/Switch paddle | 3 | r57 |
| Style/Switch air-curl | 14 | r51 |
| Style/Switch diffuser | 4 | r17, r18, r58 |
| Flat iron | 21 | r03, r04, r19, r21, r36, r40, r55 |

## Gaps to keep in mind when choosing

- **Air-curl.** The 14 air-curl references are mostly AI-looking split-face images. Only r51 is a clean real photo.
- **Paddle brush.** It has a single grade A reference.
- **Coily hair (type 4).** Only two references: r18 (diffuser, back view) and r55 (silk press). These are the only ones for avatar A02.
- **Thermal brush on curly hair.** The only curly before is r41 (3A).
- **Split-face references** (r01, r05–r10, r12, r13, r16–r18, r32, r33) give half a head per file. They are fine for texture and weak for overall shape.
- **Text on the image.** Many references carry BEFORE/AFTER text. A model may copy it, so crop the text or tell the prompt to ignore it.

## Client avatars

The hair length is measured on `front.png` with the MediaPipe hair segmenter (`hair_length.measure`). The other tags were read by eye.

| Avatar | Hair | Colour | Ends at |
|---|---|---|---|
| A01 | 2A choppy bob | black | chin |
| A02 | 4B afro | black | jaw |
| A03 | 2B long | copper red | bottom of the ribs |
| A04 | 2C S-waves | dark brown | collarbone |
| A05 | 3A very long | black-brown | bottom of the ribs |
| A06 | 1 lob | platinum, dark roots | shoulders |
| A07 | 3B ringlets | burgundy | collarbone |
| A08 | 2A shag with bangs | warm brown | middle of the chest |
| A09 | 1 | dark blonde | collarbone |
| A10 | 3B long | black | bottom of the bust |
