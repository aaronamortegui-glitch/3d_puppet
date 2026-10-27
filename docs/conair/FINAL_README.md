# Conair POC · final assets (2026-10-27, test 20)

This folder holds only what is used:
- every final image;
- the original inputs that made them;
- the prompts and the instructions.

Every experiment stays in `outputs/`, one folder per test. Nothing here is a rejected version. The folder is rebuilt with `python tools/build_final.py outputs/FINAL_2026-10-27`.

**Start here:**
- `WORKFLOW_test20.png`: the workflow;
- `06_instructions/TEST_20.md`: what changed and why.

## The rule

**Only original inputs go into the models:**
- the avatar;
- the real reference photos;
- the hair cut out of the real reference;
- the real lock;
- the real packshots;
- the product sheet.

**No generated image is chained as an input.** The only exception is the product fix, which edits a crop around the product and pastes back only the product.

## Folders

| Folder | What |
|---|---|
| `00_inputs/avatars/` | The 10 client avatars (`front.png` + `meta.json`). |
| `00_inputs/hair_styles/<sku_slot>/<rule>/<ref>/` | The real reference of each look: `before.png` + `after.png` (the change, for the after), `lock.png` (texture), `after_hair.png` (the hair alone, cut out of the real after, for the in use) and `ref.json`. |
| `00_inputs/products/<sku>/<colour>/` | `card_v2.png`, the product sheet: 6000 px, labelled sizes, colours and logo position. `packshots/` holds the real photo used in the product images. |
| `00_inputs/poses_3d/in_hand/` | The 3 gray hand poses used for the in-hand images. |
| `00_inputs/rules/` | Product × hair rules, hair references, the real length and width change. |
| `01_before/` | The avatar of each look (10). |
| `02_after/` | The after of each look (13): the same woman in the same session, with a slightly different pose. |
| `03_in_use/` | The product in use (13): the finished style, with the product fixed. |
| `04_product/soft_environment/` | The product in a set (8). |
| `04_product/in_hand/` | The product in hand (3). |
| `05_prompts/` | The templates. `filled/` holds the exact prompt, inputs and job id of every image, plus the crop, the edit and `crop.json` of every product fix. |
| `06_instructions/` | `CLAUDE.md` (how to run it, the rules), `TEST_20.md` (the report), `HAIR_REFS.md`, `pipeline.png`, and `jobs/` (all job ids). |

## How each image is made

**1 · After.** `02_after.txt` on Sunburst (`openai/gpt-image-2.5-sunburst`), quality high, 4K (2496 × 3312), 3:4.
- **Inputs:** the avatar, the real before and after of the reference, and the real lock.
- **Hair:** the length and width change exactly as in the real reference pair.
- **Pose:** she is photographed again a moment later, so the after never looks like the same photo:
  - she faces another direction (a before turned to one side goes in mirrored, so she faces the other way);
  - a hand rests on her waist or her hands are behind her back;
  - she wears a light happy smile.
  - Checked with `tools/facing.py`: the head turns at least 15°.

**2 · In use.** `07_in_use_nano.txt` on Nano Banana 2.1 (`google/nano-banana-2.1`), 2K, 3:4, thinking high.
- **Inputs:** the avatar, `after_hair.png`, the lock and `card_v2.png`.
- **Pose:** a dynamic beauty pose per product, with the product used correctly. The prompt gives the per-product HOW IT TOUCHES THE HAIR line and the same hair-length line as the after.
- **Not an input:** the generated after.

**3 · Product fix.** Run `tools/inpaint_product.py crop` on the product box.
- The crop has exactly the shape Sunburst returns.
1. Run `08_product_inpaint.txt` on Sunburst with the crop and `card_v2.png`.
2. Run `tools/inpaint_product.py stitch`, which registers the edit on the original and pastes back only the product with a feathered edge and matched colour.

**4 · Product images.**
- **Step 1:** `04_soft_environment.txt` or `03_in_hand.txt` on Nano Banana 2.1, with the real packshot and `card_v2.png`.
- **Step 2:** the same product fix as step 3.
- All 11 keep the fix.

## Looks

| Avatar | Rule | Reference | Product |
|---|---|---|---|
| client_a01_bob_black | SS_t2_paddle | r57 | Style/Switch, paddle |
| client_a01_bob_black | SS_t2_roundbrush | r39 | Style/Switch, round brush |
| client_a02_coily | FI_t4_silkpress | r55 | Flat iron, Nano Blue |
| client_a03_red_wavy | AC_t2 | r54 | Auto Curler |
| client_a04_wavy_dark | TB_t2 | r14 | Thermal brush |
| client_a05_long_curly | FI_t3 | r19 | Flat iron, Pink Rush |
| client_a06_platinum | FI_t1 | r36 | Flat iron, Nano Blue |
| client_a06_platinum | SS_t1_aircurl | r51 | Style/Switch, air curl |
| client_a07_burgundy_curls | TB_t3 | r41 | Thermal brush |
| client_a08_shag_bangs | AC_t2 | r45 | Auto Curler |
| client_a08_shag_bangs | SS_t2_roundbrush | r47 | Style/Switch, round brush |
| client_a09_blonde_straight | TB_t1 | r14 | Thermal brush |
| client_a10_long_curly | SS_t3_diffuser | r58 | Style/Switch, diffuser |

A05 and A08 (round brush) were the first validation runs. Their in-use images took the full real `after.png` of the reference, before `after_hair.png` existed. Every later look uses `after_hair.png`.
