# Conair POC, test 3: 3 images per SKU in all 4 categories (2026-10-23)

This test completes the POC scope with 3 images per SKU in each of Aaron's 4 categories. It adds 32 new images to the 16 from tests 1 and 2, for 48 in total. Everything is made with the same 2 temporary avatars, from `library/` inputs only.

- Plan, prompts and Krea job IDs: `outputs/jobs_test3_plan.json`. It is gitignored, as are all outputs.
- The plan was written by a small script that reads the uploads, the rules and the pose details.

## What was added per SKU

| Category | New images per SKU | How they vary |
|---|---|---|
| In use | 2 | 2 other poses from `poses/in_use/`; the other avatar; the flat iron also in Nano Blue and Iced Blue |
| Before / after | 2 | The other avatar from the front, plus the first avatar from behind (the back view links to the back-view style library). The style comes from the rule for SKU × hair type: AC_t3, AC_t2, TB_t2, TB_t3, SS_t2_aircurl, SS_t3_diffuser, FI_t3, FI_t2. |
| In hand | 2 | `in_hand_02` (or `in_hand_01`) pose plus the product's hand reference; the skin of the other avatar; the flat iron in Nano Blue and Iced Blue |
| On a soft environment | 2 | New sets: white marble with a towel, pale-blue paper sweep, travertine tray, sage plinth, icy-blue plaster |

## Review

- 31 of 32 worked on the first try.
- SS_t2_aircurl on the wavy avatar, front view, changed too little. It was regenerated with "COMPLETELY GONE" plus a description of salon blowout curls, and the change is now clear. v1 is kept in `outputs/02_before_after/v1/`.
- Known limits:
  - In hand: some hand-reference poses repeat the same vertical grip, so they give less variety.
  - The Nano Blue iron on marble came out with the plates slightly open, although the prompt asked for it closed.

## Figma

- Design file "3d-puppet", page "Product research": frame "CONAIR POC · BaByliss · 4 categories × 4 SKUs (test 3)" (node 96:2), below test 1.
- FigJam "Essilor-Luxottica": section with the same name (node 1302:233), to the right of the existing sections.
