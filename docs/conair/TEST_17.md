# Test 17: validation of the looks workflow, new poses × other avatars (2026-10-26)

## Question

Test 13 made 7 looks on 7 poses. Does the same before → after → in use flow hold with the approved gray poses v2 that were never used, and with other avatars?

## How

The 6 approved v2 poses never used before, each with a client avatar that had not been shown with that product. The avatar is picked with `tools/pick_pose.py --finished`, with no rule changes. The flow is the same as test 13:
1. **After:** `02_after.txt`, calibrated on the real reference pair.
2. **In use:** `01_in_use.txt`, with the gray pose, the after, the product sheet and the lock.

Both steps ran on Sunburst, high, 2K, 3:4.

## Results: 5/6 pass, 1 check

| Avatar | Rule · ref | New pose | Pose verdict | Result |
|---|---|---|---|---|
| A08 shag bangs | AC_t2 · r45 | `auto_curler_in_use_04` | avoid (texture) | **Pass:** curls and length kept from the after |
| A02 coily | FI_t4_silkpress · r55 | `flat_iron_in_use_02` | ok | **Check:** silk press, skin and product good; the hair is a bit longer in use than in the after |
| A06 platinum | FI_t1 · r36 | `flat_iron_in_use_03` | avoid (texture) | **Pass:** sleek straight kept |
| A01 bob black | SS_t2_roundbrush · r39 | `style_switch_in_use_03` | ok | **Pass:** voluminous blowout kept, round brush correct |
| A07 burgundy curls | TB_t3 · r41 | `thermal_brush_in_use_04` | avoid (texture) | **Pass:** blowout kept |
| A04 wavy dark | TB_t2 · r14 | `thermal_brush_in_use_05` | check | **Pass:** blowout kept; the raised-arm pose works |

All 6 afters keep the identity and the background, and the hair change looks believable.

## Decision

1. **The looks method is confirmed on new poses and new avatars.**
2. **The pose verdict matters less now.** Since the hair comes from the after, a pose rated "avoid" only for its hair texture works. The hard rule against abundant sculpted hair still holds.
3. **Silk press (4A → straight) adds length** (r55: +43%). In the in-use step it can grow a little more. If it matters, add the measured end landmark of the after to the in-use prompt.

## Where

**Files:**
- Afters: `library/avatars/<avatar>/after/<rule>__<ref>.png` (each with its `.prompt.txt`).
- In use: `outputs/17_validation_looks/`.
- Plan, prompts and job ids: `outputs/jobs_test17_plan.json`.

**Boards:**

| Board | Node |
|---|---|
| FigJam CONAIR, "Workflow and Logic", below the final results table | 186:144 |
| Design file, page 54:2 | 206:2 |
| FigJam Essilor | 1324:461 |

The cost was 12 Sunburst high runs, about $1.50.
