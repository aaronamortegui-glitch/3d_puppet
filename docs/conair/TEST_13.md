# Test 13: final flow, before → after → in use (2026-10-26)

## Why

The review of test 12 found four problems:

1. **The background changed.** The in-use prompt asked for a plain light-gray background.
2. **There was too much hair.** The sculpted hair of the gray poses was abundant and leaked into the output.
3. **The length and volume were not grounded in anything real.** The shrinkage model gave avatar A07 +39% of length.
4. **The order was wrong.** It should be before → after first, and in use second.

## What changed

1. **Real change, measured** (`tools/measure_ref_change.py` → `docs/products/hair_change.json`).
   - **Method.** For each grade A reference, the MediaPipe hair mask gives the width and the length of the hair, before and after.
   - **Result.** Straightening keeps the length (≈1.0) and narrows the hair:

     | Rule | Width after / before |
     |---|---|
     | Flat iron | 0.86 |
     | Paddle | 0.82 |
     | Thermal brush | 0.70 |
     | Round brush | 1.07 (it adds volume) |
     | Auto Curler | 0.98 length |
2. **Step 1, the after** (`prompts/conair/02_after.txt`).
   - **Inputs:** the avatar (the before), the reference's real before and after, and its lock.
   - **`{hair_change_line}`** applies exactly the change of that real pair, never more and never less: "kept 92% of its length and 107% of its width".
   - **Background:** the same as the avatar's.
   - **Saved as:** `library/avatars/<avatar>/after/<rule>__<ref>.png`.
3. **Step 2, in use** (`prompts/conair/01_in_use.txt`). The inputs are:
   - the gray pose v2;
   - the step 1 after, so the hair is exactly the same: no longer, no fuller;
   - the product sheet;
   - the lock.

   The background is the same as in the after.
4. **Gray poses v2** (`server/prompts/gray_render_prompt_v3_moderate_hair.txt`, Nano Banana 2.1).
   - 12 in-use poses were re-rendered with neutral, moderate hair: smooth, close to the head, no big waves.
   - The renders are in `samples/pose_library/gray_v2/`, and their job ids in `samples/pose_library/jobs_gray_v2.tsv`.
   - The library uses v2 as `gray.png` and keeps the old one as `gray_v1.png`.
   - The four poses rejected only for their hair are approved again: `style_switch_in_use_01`, `style_switch_in_use_02`, `flat_iron_in_use_03` and `thermal_brush_in_use_04`.
   - 12 in-use poses are approved. The pose matrix with the client avatars has 18 ok, 20 check and 18 avoid.

## Results (one row per SKU slot)

| Row | Avatar | Rule | Reference | Pose | After | In use |
|---|---|---|---|---|---|---|
| Auto Curler | A03 | AC_t2 | r54 | `auto_curler_in_use_05` | good: curls, 9% shorter | good |
| Thermal Brush | A09 | TB_t1 | r14 | `thermal_brush_in_use_03` | good | good |
| SS round brush | A08 | SS_t2_roundbrush | r47 | `style_switch_in_use_04` | good | good |
| SS paddle | A01 | SS_t2_paddle | r57 | `style_switch_in_use_02` | good: sleek bob | good |
| SS air-curl | A06 | SS_t1_aircurl | r51 | `style_switch_in_use_01` | good: soft waves | good |
| SS diffuser | A10 | SS_t3_diffuser | r58 | `style_switch_in_use_04` | good | good (pose verdict "avoid" on texture, but the hair comes from the after) |
| Flat iron | A05 | FI_t3 | r19 | `flat_iron_in_use_01` | good: straight, same length | good: the iron size now looks right |

Every after and in-use image keeps the avatar's background, and the hair of the in-use image matches its after.

A07 (3B curls) was dropped from the round brush row. All the round-brush references are straight hair gaining volume (r39 +54% width), which would exaggerate a curly mane.

## Where

- **Afters:** `library/avatars/<avatar>/after/` (each with its `.prompt.txt`).
- **In use:** `outputs/13_final/`.
- **Plans and job ids:** `outputs/jobs_test13_after_plan.json`, `outputs/jobs_test13_in_use_plan.json`.
- **Final table:** FigJam CONAIR, page "study", section "FINAL RESULTS" (158:451), next to the earlier table (80:202, kept).
- **Workflow:** the design file, page "workflow" (155:2): the diagram, the input folders and both prompts.

## Open

- **Round brush on curly hair.** No grade A reference for it; one is needed.
- **Moderate curly or coily poses** for the diffuser.
- **Exact length of the flat iron.**
- **QA.** `scene_qa.py` was not run (Grounding DINO and SAM are missing); the checks are by eye.
