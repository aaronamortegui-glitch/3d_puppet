# Test 16: validation of the product workflow, Nano Banana 2.1 → Sunburst product fix (2026-10-26)

## Question

Test 15 showed that Nano Banana 2.1 makes the better scene and light and that a Sunburst pass fixes the product. Does that hold beyond test 15? This test checks it on:
- new sets and camera angles;
- a colour never tested before;
- the product in a hand, with client avatars on other library poses.

## How

**Step 1, on Nano Banana 2.1** (2K, 1:1):
- **Soft environment:** `04_soft_environment.txt` with new set descriptions.
- **In hand:** `03_in_hand.txt`, run on Nano instead of Sunburst. The inputs are the gray hand pose, the packshot and the avatar (for the skin tone).

**Step 2, on Sunburst** (high, 2K, 1:1): `06_product_fix_sunburst.txt`. Its inputs are the Nano image, the packshot and `card_clean.png`. The template now also keeps any hand holding the product (skin, nails, grip, fingers).

## Results: 7/7 pass

| Case | Change | Verdict |
|---|---|---|
| Auto Curler · terrazzo shelf, higher angle | 10/255 | **Pass.** Nano made the barrel gold again; the fix restores the titanium-grey barrel, the charcoal tip, a crisp wordmark and the coloured LEDs. |
| Thermal Brush · oak tray, handle to camera | 9/255 | **Pass.** The fix shows the real perforated gunmetal barrel between the bristles, and the wordmark is crisp. |
| Style/Switch · all 4 attachments in a row | 17/255 | **Pass.** All the attachments are kept, and the wordmark and buttons are sharper. The light came out slightly warmer. |
| Flat iron **Pink Rush** (new colour) · blush velvet | 8/255 | **Pass.** A crisp wordmark, real LED heat dots and buttons, and the true plates. |
| In hand · Auto Curler · `auto_curler_in_hand_02` · A03 | 5/255 | **Pass.** The hand, grip and skin are kept; the wordmark, LEDs and buttons are crisp. |
| In hand · Flat iron Pink Rush · `flat_iron_in_hand_02` · A02 | 4/255 | **Pass.** Nano hid the wordmark; the fix brings it back. The dark skin tone is kept. |
| In hand · Thermal Brush · `thermal_brush_in_hand_01` · A09 | 8/255 | **Pass.** The wordmark and barrel are true; the hand, nails and grip are kept. |

## Decision

The method is confirmed for:
- **category 4**, product on a soft environment;
- **category 3**, product in hand.

In both, Nano Banana 2.1 makes the image (scene, light, hand) and Sunburst corrects only the product. The recurring Nano errors are a gold Auto Curler barrel, a soft or missing wordmark and simplified LEDs and buttons. The fix corrects them every time.

## Where

**Files:**
- Images, prompts and comparisons: `outputs/16_validation_nano_then_sunburst/` (with `compare/`).
- Plan with job ids and prompts: `outputs/jobs_test16_plan.json`.

**Boards:**

| Board | Node |
|---|---|
| FigJam CONAIR, "Workflow and Logic", product column, below Test 15 | 178:144 |
| Design file, page 54:2, below Test 15 | 197:2 |
| FigJam Essilor, below the connected workflow | 1322:461 |

The cost was 7 Nano runs plus 7 Sunburst high runs, about $1.40.
