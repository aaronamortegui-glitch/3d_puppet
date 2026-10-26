# Test 12: straightening fix (2026-10-26)

This test reruns the 5 failed or partial cases of [test 11](TEST_11.md) after four fixes.

## What changed

1. **Abundant-hair poses are rejected for good** (`tools/pose_status.json`). Three poses are out:
   - `style_switch_in_use_01` (re-tagged as big volume);
   - `flat_iron_in_use_03`;
   - `thermal_brush_in_use_04`.

   Test 11 used these poses, against the rule that abundant hair is to be avoided. It is now a hard rule: no pose with big or abundant sculpted hair, whatever the avatar's volume. 8 in-use poses remain.
2. **The pose is picked by the after.** `pick_pose.py --finished` (which `fill_prompt.py` uses for in use) scores the sculpted hair against the after:
   - the after's texture;
   - its volume;
   - its length.

   The straightening and blowout rules now carry `after_texture` and `after_volume` in `product_hair_rules.json`:

   | Rules | after_texture | after_volume |
   |---|---|---|
   | Flat iron, paddle | 1 | flat |
   | Round brush, thermal brush | 2A | medium |

   Before this fix, a flat-iron result (shrinkage 0.03) was read as texture 2A.
3. **The pose details lose their hair sentences** (`fill_prompt.pose_without_hair`). Examples: "Voluminous wavy hair." goes, and "long lock of wavy hair" becomes "lock of hair".
4. **An explicit `RESULT TEXTURE` line** is added for straight results ("completely straight … no waves, curls or bends left; ignore any waves in the sculpted hair of image 1") and for blowouts.

## Results

| Case | Test 11 | Test 12 |
|---|---|---|
| A08 · SS paddle · `style_switch_in_use_03` · r57 | partial | **good**: sleek and straight, soft bend |
| A03 · SS round brush · `style_switch_in_use_03` · r47 | partial | **good**: a real round-brush blowout |
| A05 · SS round brush on curly · `style_switch_in_use_03` · r39 | fail | **good**: curls stretched, longer as the model says |
| A07 · flat iron FI_t3 · `flat_iron_in_use_02` · r19 | fail | **good hair**: completely straight. The iron looks oversized. |
| A04 · flat iron FI_t2 · `flat_iron_in_use_02` · r21 | fail | **good hair**: straight. The iron looks oversized. |

The paddle case still had the verdict "avoid", because no Style/Switch pose has straight sculpted hair. With the prompt fixes it worked anyway.

**Where everything is:**
- Images and prompts: `outputs/12_inuse_straight_fix/`.
- Plan and job ids: `outputs/jobs_test12_plan.json`.
- Boards: design file 164:2, FigJam CONAIR 149:228, FigJam Essilor 1316:401.

## Open

- **The flat iron looks oversized** in `flat_iron_in_use_02`. The prompt only gives the plate size; add the real overall length once it is confirmed from the product sheet.
- **Pose gaps.** With 8 approved poses, many avatar × rule combinations have no "ok" pose. These are needed:
  - straight sculpted hair for the Style/Switch paddle;
  - curly and coily poses with moderate volume.
- **QA.** `scene_qa.py` was not run, because Grounding DINO and SAM are missing in the environment.
