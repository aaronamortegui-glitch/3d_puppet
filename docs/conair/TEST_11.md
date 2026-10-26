# Test 11: in use with real hair locks (2026-10-26)

## Question

With the new inputs, do in-use images of the **finished** style come out right? The inputs:
- the client avatar;
- an approved gray pose;
- the product sheet;
- a real hair lock;
- a real after.

## How

**Poses.** The poses were filtered by eye on every gray render (`tools/pose_status.json`). A pose stays when it has all of these:
- a front or three-quarter view;
- the face visible;
- a portrait crop;
- moderate sculpted hair;
- the real product silhouette as the proxy.

That leaves 11 in-use and 6 in-hand poses. 16 of the 56 avatar × rule combinations have an "ok" pose (`docs/conair/POSE_MATRIX_client_avatars.txt`).

**Setup:**

| | |
|---|---|
| Combinations | 8 "ok" ones that have a grade A reference: 7 avatars, all 4 SKUs |
| Prompt | `prompts/conair/01_in_use.txt`, filled by `tools/fill_prompt.py` (hair length from `hair_length.py`) |
| Model | Sunburst, quality high, 2K, 3:4 |
| Files | `outputs/11_inuse_real_locks/` (image + `.prompt.txt`); plan and job ids in `outputs/jobs_test11_plan.json` |

**Boards:**
- design file 159:2;
- FigJam CONAIR 148:228;
- FigJam Essilor 1315:401.

## Results

| Avatar · rule · pose · lock | Verdict | Note |
|---|---|---|
| A03 · AC_t2 · auto_curler_in_use_05 · r54 | good | Defined 1" curls, her copper colour, shorter as the length model says |
| A08 · SS_t2_aircurl · style_switch_in_use_01 · r51 | good | Soft bouncy waves, the barrel attachment right |
| A06 · TB_t1 · thermal_brush_in_use_03 · r14 | good | Smooth blowout with bent ends. The lock's dark colour was not copied. |
| A08 · SS_t2_paddle · style_switch_in_use_03 · r57 | partial | Smoother, but the waves remain; the r57 lock is low resolution |
| A03 · SS_t2_roundbrush · style_switch_in_use_01 · r47 | partial | It reads as curls more than a round-brush blowout |
| A05 · SS_t3_roundbrush · style_switch_in_use_01 · r39 | fail | The curls are not stretched |
| A07 · FI_t3 · flat_iron_in_use_03 · r19 | fail | Glossy waves, not straight |
| A04 · FI_t2 · flat_iron_in_use_03 · r21 | fail | Waves, not straight |

## Findings

1. **What worked.**
   - Identity and colour always come from the avatar, and the lock never passes its colour. The texture-only lock works as intended.
   - Curls and waves come out right.
2. **What failed: straightening and blowouts.** The gray pose's sculpted waves and the hair words in the pose details win over the lock. For example, `flat_iron_in_use_03` says "Voluminous wavy hair". The picker scores the pose texture against her hair *before*, which fits a mid-process shot. For a finished shot it should score against the *after* texture.

## Next fixes to test

1. **Pose texture.** In `pick_pose.py`, for a finished shot, compare the pose texture with the after texture (straight for flat iron, paddle and blowouts).
2. **Pose details.** Strip the hair sentences from the pose details in `fill_prompt.py`.
3. **Result line.** State the result explicitly when it is straight: "completely straight, no waves left, ignore the waves of image 1".
4. **More poses.** Render gray poses with straight sculpted hair for the flat iron and the paddle.

## Not run

**QA** (`scene_qa.py`) was not run. Its Grounding DINO and SAM packages are not in the current environment (`pylibs`). The verdicts above are by eye.
