# Conair POC, test 1: same avatar, in use + before/after per SKU (2026-10-23)

Every input comes from `library/`. The images are in `outputs/` (gitignored), and the Krea job IDs are in `outputs/jobs_test1.tsv`. Model: Nano Banana 2.1, 2K.

## Avatars (temporary, until Gustavo's)

Each avatar was generated from text (front view), then the three_quarter, profile and back views were generated with the front as the identity reference. Files: `library/avatars/<id>/` (front, three_quarter, profile, back, meta.json).

| Avatar | Hair | Used for |
|---|---|---|
| `tmp_a_wavy` | Wavy, chocolate brown. Generated as 2B-2C, wavier than asked. | Auto Curler, flat iron (Pink Rush) |
| `tmp_b_curly` | Curly 3B, dark brown | Thermal Brush, Style/Switch with the diffuser |

Identity holds across the 4 views and all the outputs.

## Combinations, chosen from `product_hair_rules.json`

| SKU | Avatar | Rule | Evidence | Pose (in use) |
|---|---|---|---|---|
| auto_curler | tmp_a_wavy | AC_t2: uniform glossy 1" curls | low_evidence | in_use_05 |
| thermal_brush | tmp_b_curly | TB_t3: sleek, almost straight blowout | works | in_use_04 |
| style_switch | tmp_b_curly | SS_t3_diffuser: defined bouncy curls | works | in_use_05 (diffuser pose) |
| flat_iron (Pink Rush) | tmp_a_wavy | FI_t2: sleek straight | mixed | in_use_03 |

## How each image is made

**In use: 1 call per image.** The `final_generation_prompt.txt` (B1) gets 3 images:
1. the gray render of the pose;
2. the packshot of the right colour;
3. the avatar's front view, as identity.

The prompt also carries the pose details and the product size, plus one hair line taken from the rule (for example, "her curls have just been blown out into a smooth blowout").

**Before / after: 1 call per image.** The before is the avatar's front view as it is. The after gets 3 images:
1. the avatar;
2. `swatch_after`, the close-up of the style;
3. `back_after`, the same style on a head seen from behind.

The prompt says that only the hair changes, describes the rule's result, and says what disappears. The labelled side-by-side image is put together with PIL (`*_pair.png`).

## Review

- **In use.** All 4 keep the avatar's identity, the pose and the product (colours, buttons, proportions). Two weak points: on the Auto Curler the lock is barely wrapped around the barrel, and the Style/Switch with diffuser reads well, though the body is a little chunkier than the real one.
- **Before / after.** TB, SS and FI changed clearly on the first try. AC v1 barely changed, because the avatar is already very wavy. v2 says the waves are "COMPLETELY GONE" and describes polished barrel curls, and the change is now obvious. v1 is kept in `outputs/02_before_after/v1/`.
- **Lesson.** For before/after, the avatar's natural hair must be clearly far from the target style. When it is not, the prompt has to say what disappears.

## Next

- Replace the temporary avatars with Gustavo's (same format).
- Product in hand and product on surface (Aaron's other two categories).
- 3-5 images per SKU and category (POC scope).
