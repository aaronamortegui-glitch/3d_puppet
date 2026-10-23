# Picking poses by the avatar's hair (2026-10-23)

Test 6 showed that the sculpted hair of the gray pose render leaks into the output. The models blend it with the avatar's hair:

- the big curly mane of `style_switch_in_use_02` gave the coily H2 "far too much hair";
- the short wavy bob of `flat_iron_in_use_03` made the H3 shot look unreal.

So a pose has to match her hair in the same way the rule has to match her hair type.

## Tags: `tools/pose_hair.json`

Each pose carries the following tags. They were set by eye from the gray renders; MediaPipe's hair segmenter cannot separate clay hair from clay skin, so it can't measure them.

| Tag | What it holds |
|---|---|
| `hair.end_landmark` / `hair.end` | Where the sculpted hair ends, in the landmarks and head heights of `tools/hair_length.py` |
| `hair.cropped` | The hair leaves the frame, so `end` is the frame bottom and a lower bound |
| `hair.texture` | Curl subtype: 1, 2A–2C, 3A–3C, 4A–4C |
| `hair.volume` | Flat, medium or big |
| `body` | The sculpted body: slim or curvy (the curvy thermal-brush poses changed the avatar's body in test 4) |
| `note` | For example: "proxy is a pistol-grip dryer, not the slim Style/Switch body" |

Poses in the `in_hand` category have `hair: null`. `tools/build_library.py` writes the tags into `library/poses/.../meta.json`.

Each avatar's `meta.json` gains `hair_volume` and `body`, next to `hair_subtype` and `hair_end` from test 5.

## Picker: `tools/pick_pose.py`

```
python tools/pick_pose.py gustavo_h2_coily SS_t4_roundbrush
python tools/pick_pose.py --matrix
```

The picker gives every in-use pose of the rule's SKU a score; lower is better.

**Score = length + 0.6 × texture + 0.5 × volume + 0.5 × body**

- **Length**: the distance in head heights to the nearer of her before length and her styled length (in-use shots are mid-process).
  - A cropped pose is penalised only if it shows more hair than she has.
- **Texture**: the curl-type distance to the nearer of her natural pattern and the rule's result style. The result style's curl type comes from its `after_shrinkage`.
- **Volume**: one step between flat, medium and big counts 1.
- **Body**: 1 when the sculpted body does not match hers.

Verdicts: ok < 0.6, check < 1.2, avoid at 1.2 and above. Notes about the proxy are shown as warnings.

The picker rejects forbidden rules (AC_t4, TB_t4) and any rule whose hair type is not hers.

**Check against the failures we saw:**

| Case | Pose | Verdict |
|---|---|---|
| H2 + round brush | `style_switch_in_use_02` (the mane) | avoid (1.23) |
| H3 + flat iron | `flat_iron_in_use_03` (the bob) | avoid (1.28) |
| H2 + Style/Switch | `style_switch_in_use_05` (afro, chin length) | ok (0.22), with the dryer-proxy warning |

## Gaps in the pose library (from `--matrix`)

| Avatar hair | Missing poses | Best today |
|---|---|---|
| Curly 3A/3C (H4, H9) | Auto Curler, Thermal Brush, flat iron | check or avoid: the poses have wavy 2B hair or are too short |
| Coily 4 (H2) | Style/Switch with the slim body as proxy; flat iron silk press | `style_switch_in_use_05` has a dryer proxy; `flat_iron_in_use_03` is a check |
| Straight 1 (H5) | Style/Switch paddle and round brush | `style_switch_in_use_01` has curly 2C hair (avoid / check) |

Wavy 2 (H1, H3, H6, H7) and straight 1 are well covered for Auto Curler, Thermal Brush and flat iron.

**Next**: render new gray poses for these gaps. The sculpted hair should be set from the avatar (curly 3B–3C, long; coily, short and big), and the proxy should be the real product silhouette (test 4 finding 3).
