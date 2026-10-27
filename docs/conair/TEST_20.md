# Test 20: original inputs only, Nano in use, segmented product inpaint, product sheet v2 (2026-10-27)

## Why

The 2026-10-27 review raised four problems:

1. **The afters looked like edited copies of the before.** The woman was in exactly the same pose.
2. **The in-use images lost quality.** They were built on a generated image: the after was fed back as image 2, and the gray pose added its own hair.
3. **The product came out wrong.** The logo landed on the wrong side, the buttons and LEDs were in the wrong place, and the product sheet was too small to read.
4. **The product fix re-edited the whole image** (`06_product_fix_sunburst.txt`), so every pass degraded the whole picture.

## New rule

**Never chain generated images as inputs. Use only original inputs:**
- the avatar;
- the real reference photos;
- the hair cut out of the real reference;
- the real lock;
- the real packshots;
- the product sheet.

The only time a generated image goes back into a model is the product inpaint, and only as a crop around the product. Only that crop is pasted back. Everything else keeps the original pixels.

## What changed

| Step | Before (tests 13 to 19) | Now (test 20) |
|---|---|---|
| After (`02_after.txt`, Sunburst) | Same pose as the before, 2K. **v7:** the before goes in mirrored when she faces a side; new arms, a light smile; checked with `tools/facing.py` | A new photo of the same session: a small, natural change of head angle, shoulders and expression, with the hands kept low. One concrete pose line per look (`AFTER_POSES` in `fill_prompt.py`). **4K** (Sunburst returns 2496 × 3312). |
| In use (`07_in_use_nano.txt`) | Sunburst, gray pose + generated after as inputs | **Nano Banana 2.1** with original inputs only (inputs listed below), plus a free dynamic pose per product. The gray pose is the fallback; it was not needed. |
| Product sheet | `card_clean.png`, ~2K, no labels | **`card_v2.png`** (detailed below) |
| Product fix | Sunburst re-edits the whole image | **Crop → inpaint → stitch** (`tools/inpaint_product.py`, adapted from EL_Inpainting_system; detailed below) |
| Product images (`03_in_hand`, `04_soft_environment`) | Nano + full-image Sunburst fix | Nano with packshot + `card_v2`, then the same crop → inpaint → stitch |

**In-use inputs (original only):**
1. avatar `front.png`;
2. `after_hair.png`: the real reference after, cut to the hair only with MediaPipe (`tools/mask_ref_face.py`), so Nano cannot copy the other woman's face or clothes;
3. the real `lock.png`;
4. `card_v2.png`.

**`card_v2.png`:**
- 6000 × 3600 px;
- built from the real photos upscaled ×4 (Topaz High Fidelity V2);
- labelled with SIZES, COLOUR AND MATERIAL, and a LOGO line that says where the wordmark sits and which way it reads;
- includes a LOGO detail tile;
- made by `tools/product_cards_v2.py`.

**Crop → inpaint → stitch:**
1. Crop the product box, grown ×1.35, at **exactly** the shape Sunburst returns (1760×2368, 2048×2048 or 2368×1760), shrinking both sides when the box is bigger than the image.
2. Run `08_product_inpaint.txt` on Sunburst with `card_v2`.
3. Resize the edit back without stretching, **register** it on the original (ORB + RANSAC similarity on the ring around the product) and match its colour (LAB) to that ring.
4. Paste only the product box, with a feathered edge.

## Bugs found in review (2026-10-27)

**1 · The inpaint stretched the edit.**
- **Cause:** when the product box was bigger than the image, the crop was clamped on one side only and became almost square (e.g. 2048×1928). Sunburst returned 3:4 or 4:3 and the stitch stretched it back by up to 30%, leaving double edges and ghosts at the seam.
- **Effect on the in-use images:** the aspect was off ~1% and the edits shifted by up to 12 px.
- **Fix:**
  - The crop now uses the exact model shapes.
  - The stitch registers the edit before pasting and prints the aspect error, the transform and the mean difference outside the product.
- **Result:** after the fix, the difference outside the product fell from 25–35 to 2.6–5.5 (8-bit grey levels).
- **What was redone:** the 13 in-use images were re-stitched from the same edits (`*_inuse_fixed_v2.png`); 9 product images were re-run with an exact-aspect crop (`fix2_*`, `*__2_fixed_v3.png`).

**2 · The after looked like the input.** "Change the pose slightly" alone came back as a copy of the before.
- **v2:** a strong pose with raised hands. Rejected: too much.
- **v3:** a subtle change of head and shoulders, hands low, at 4K. Still looked like the input: `tools/facing.py` showed the head kept its direction.
- **v6:** a direction asked in words, a hand on the waist or the hands behind the back, and a light smile. The arms changed, but Sunburst kept the head angle of every turned before (it moved 0–9°).
- **v7 (final):** a before turned to one side goes in **mirrored**, so the after faces the other side. The arms change and she wears a light smile. Frontal befores (A02, A03) turn three-quarter (v6). All 13 move the head 17–85° (`tools/facing.py`). The mirror flips the hair parting, which is acceptable for a restyled after.

## Results

- **13 looks:** 13 afters (v3, 4K) and 13 in-use images, all with the product fix.
  - The afters now change the head angle and shoulders a little, as asked. A03 and A10 move the least.
  - The in-use images are clearly better than the chained version: sharper, more dynamic poses, the right identity, the right length, and the product touching the hair.
- **11 product images** (8 soft environment, 3 in hand). The logo and buttons are on the right side in all 11, and all 11 keep the fix. The 2 problems first seen (washed-out blue, moved brush) were the stretch bug.

**Lesson:** always compare the fix with the step 1 image. The stitch now prints its error, so a bad paste shows up as a number.

## Cost and tools

- Everything ran on Krea.
- **Krea limit:** it hit the 40,000 CU member limit halfway through. An admin raised it, and the run finished.
- **Flora:** 12 runs were rejected by its member limit (`BILLING_WORKSPACE_MEMBER_USAGE_LIMIT_EXCEEDED`), so it was not used. The runs were not retried.

Job ids:
- looks: `outputs/jobs_test20_plan.json` (`job_id`, `product_fix_job`);
- product images: `outputs/20_product/jobs_test20_product.json`.

## Files

- `outputs/20_nano_inuse/`: afters, in-use (`*_inuse_free.png`) and fixed (`*_inuse_fixed.png`), with `fix_<look>/` (crop, edit, crop.json).
- `outputs/20_product/`: `*__1_nano.png`, `*__2_fixed.png`, `fix_<name>/`.
- Final folder: `outputs/FINAL_2026-10-27/`, built by `tools/build_final.py`.

## Pending

- **In-use at 4K.** They are 2K (Nano). The options are a faithful Topaz upscale, or regenerating them on Nano 4K and redoing the fix.
- **The A10 diffuser:** it is held at the side instead of cupping the curls from below.

## QA of the in-use images (2026-10-27, `outputs/22_inuse_redo/`)

Each product was checked against its `card_v2` sheet: shape, parts, buttons, logo and how it touches the hair. 9 of the 13 passed.

| Look | Problem | Fix | Result |
|---|---|---|---|
| A03 · Auto Curler | The barrel was empty, the hair beside it. | New in use on Nano Banana 2.1, 4K. The pose line makes the curling the action: a section is held under the clamp and wound on the barrel. Then the product fix at 4K. | The hair spirals around the barrel. Hair end 2.14 against 2.15 in the after. |
| A02 · flat iron, silk press | The iron sat beside the hair, and the hair was too long (1.77 against 1.34 in the after). | Four redos. Nano was still too long (1.77, 1.66). On Sunburst the v4a fix kept the iron beside the hair, read the wordmark toward the hinge, garbled NANO TITANIUM and left an orange glow at the tip. With the iron horizontal (v5) the clamping read well, but the hair was still too long (1.58, 1.67) and the pose looked odd. | **Final: the test 17 composition (gray pose flat_iron_in_use_02, the iron diagonal on the chest), redone at 4K on Sunburst from original inputs only.** Hair is +16% over the after. The product fix took 3 passes. `card_v2`'s LOGO note ("reading toward the plates") is wrong: on the real iron the wordmark reads from the plates toward the hinge, so with the hinge at the lower left it appears upside down. The real packshot is the authority for this. |
| A01 · Style/Switch round brush | The wordmark was on the chrome panel. | Product fix v3, with a LOGO AND PANEL line: the wordmark on the blue body, the chrome panel only for the buttons. | The wordmark is on the blue body. |
| A10 · Style/Switch diffuser | Same as A01. | Same as A01. | Same as A01. |

**Lessons:**
- QA the product at full zoom against card_v2: which side the wordmark is on, its direction and its spelling, and the hair really between the plates. Never pass small-text errors as minor.
- A straightened look on Sunburst lands about +15% to +25% over the after when the iron is in the shot.
- When the use is wrong, regenerate. The product fix cannot put hair inside the product.
- A hand that pulls the section down makes straightened hair read longer. Keep the other hand away from the section.
