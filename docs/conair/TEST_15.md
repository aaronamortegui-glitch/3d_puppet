# Test 15: product still life, Nano Banana 2.1 scene → Sunburst product fix (2026-10-26)

## Question

Test 14 showed that a Nano relight of a Sunburst still life adds nothing. The review also found that some Sunburst angles were off and that Nano lights the scene better. So the opposite order was tried: does Nano Banana 2.1 make the scene and the light, and then Sunburst correct only the product (logo, shape, buttons)?

## How

**Step 1, scene and light.** Nano Banana 2.1 at 2K, 1:1:
- the test 8 soft-environment prompt (with the support rule);
- plus a LIGHT line: a clear soft key light, realistic specular reflections that follow the product's curvature, crisp soft contact shadows, gentle fill, natural white balance;
- image 1 is the packshot.

**Step 2, product fix.** `prompts/conair/06_product_fix_sunburst.txt`, Sunburst, quality high, 2K, 1:1.
- **Inputs, in order:** the Nano scene, the packshot, the product sheet (`card_clean.png`).
- **Instruction:** keep the set, the light, the camera angle and the product's position. Correct only the product: shape, parts, buttons, LEDs, colours and the wordmark.

**Measure.** The review is by eye, with zooms on the product. The mean pixel change between steps 1 and 2 is out of 255.

## Results

| Product | Change | Verdict |
|---|---|---|
| Auto Curler | 7/255 | **Win.** Nano made the barrel gold, which is wrong. The fix restores the titanium-grey barrel and the charcoal tip, a crisp wordmark, the real LED temperatures (300–380) and the ON/OFF labels. |
| Thermal Brush | 11/255 | **Small gain.** The wordmark already read on Nano; the fix makes it sharper and the flared collar truer. |
| Style/Switch | 8/255 | **Partial.** The fix adds the wordmark on the body and cleaner buttons. Some tiny garbled text remains on the chrome panel. There are no air-curl barrels because the scene prompt only asked for the round and paddle brushes. |
| Style/Switch, retry | 7/255 | **Win.** The scene prompt now asks for all four attachments, and Nano lays out the body, both air-curl barrels, the round brush and the paddle. The fix adds the wordmark on the body and cleaner buttons. |
| Flat iron Nano Blue | 13/255 | **Win.** A crisp BaBylissPRO NANO TITANIUM wordmark with ®, readable temperatures (450°F–285°F) and real button icons. |

In all four, the fix kept Nano's set, light, reflections and shadows, and the whole product stays in frame.

## Decision

1. **New flow for category 4 (product on a soft environment):**
   - Nano Banana 2.1 makes the scene (`04_soft_environment.txt`, now with the LIGHT line);
   - then Sunburst corrects the product (`06_product_fix_sunburst.txt`).

   This replaces Sunburst alone.
2. **The Nano relight (`05_relight_nano.txt`) stays unused** (test 14).

## Open

- **Style/Switch.** Solved by the retry: name every attachment in the set description of the scene prompt (`style_switch__sage_plinth_all_attachments`).

## Where

**Files:**
- Images and prompts (`__1_nano`, `__2_nano_plus_sunburst`): `outputs/15_product_nano_then_sunburst/`.
- Comparisons (A Sunburst alone · B Nano · C Nano + fix) and zooms: `outputs/15_product_nano_then_sunburst/compare/`.
- Plan, job ids and prompts: `outputs/jobs_test15_plan.json`.

**Boards:**

| Board | Node |
|---|---|
| Design file, page 54:2 | 181:2 |
| FigJam CONAIR, page "study" | 164:228 |
| FigJam Essilor | 1319:401 |

**Connected workflow** (inputs → prompt → model → output, both lanes: the look and the product):

| Board | Node |
|---|---|
| Design file, page "workflow" | 186:2 (below 155:2) |
| FigJam CONAIR, page "Workflow and Logic" | 168:60 |
| FigJam Essilor | 1321:401 |

The total cost was 5 Nano runs plus 5 Sunburst high runs.
