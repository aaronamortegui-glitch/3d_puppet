# Conair POC · cost and time per workflow (2026-10-27)

## Sources

- **Krea cost per model:** a `preflight` quote on each model (no spend).
- **Flora cost per model:** the USD it quoted and charged in test 23.
- **Model times:** the start and end times of the real jobs from tests 20 to 23.
- **What is not in the data:** Krea does not give a USD price per compute unit (CU) through the API, so Krea costs stay in CU. The USD figures come from Flora for the same models.

## 1 · Cost and time per model

| Model | Use | Resolution | Krea (CU) | Flora (USD) | Time per run (min · avg · max) |
|---|---|---|---|---|---|
| GPT Image 2.5 **Sunburst** (`openai/gpt-image-2.5-sunburst`), quality high | after; in use for straightened hair; product fix | 2K or 4K (same price on Krea) | 127 | 0.20 at 4K | 4K in use: 46 · 47 · 49 s<br>4K fix: 38 · 44 · 51 s<br>2K fix: 42 · 43 · 45 s |
| **Nano Banana 2.1** (`google/nano-banana-2.1`), thinking high | in use; product scenes; banners | 2K | 37 | — | — |
| **Nano Banana 2.1** | (same) | 4K | 56 | 0.15 | 3:4: 58 · 64 · 68 s<br>16:9: 58 · 75 · 92 s |
| **Seedance 2.5** (`bytedance/seedance-2-5`) | 5-second clip | 720p | 856 | ~2.48 (estimate) | 148 · 201 · 282 s |

**Local tools (no model cost):**

| Tool | What it does | Time per image |
|---|---|---|
| `tools/inpaint_product.py crop` / `stitch` | Crops at the model's exact shape; registers the edit and pastes back only the product | < 10 s |
| `tools/measure_after.py` | Where the hair ends, in head heights | ~5 s |
| `tools/facing.py` | Head yaw; the after must turn ≥ 15° | ~3 s |

## 2 · Cost and time per workflow (one final image)

Runs are the usual number to reach a pass in tests 20 to 23. The range covers the first try passing up to the worst case seen.

| Workflow | Process (models and steps) | Runs to a pass | Krea (CU) | Flora (USD) | Model time | + QA and stitch |
|---|---|---|---|---|---|---|
| **After** (before / after) | `02_after.txt` on **Sunburst 4K** 3:4. Inputs: the avatar (mirrored if she faces a side) and the real reference pair plus the lock. QA: `facing.py` (≥ 15°), `measure_after.py`. | 1–2 | 127–254 | 0.20–0.40 | ~1–2 min | ~2 min |
| **In use** (look) | **Nano Banana 4K** (or **Sunburst 4K** for straightened hair, which holds the length). Inputs: original only, i.e. avatar, `after_hair`, lock, `card_v2`, optional gray pose. Then the product fix: crop, then **Sunburst 4K** with `08_product_inpaint.txt`, then stitch. QA: hair length ≤ 15%, product at full zoom against `card_v2` and the real packshot. | 2 variants + 1–3 fixes | 239–635 | 0.55–1.00 | ~3–5 min | ~5 min |
| **Product on a soft environment** (Amazon) | `04_soft_environment.txt` on **Nano 4K** 1:1, with the real packshot and `card_v2`. Then the **Sunburst 4K** product fix. | 1 + 1 | 183 | 0.36 | ~2 min | ~3 min |
| **Product in hand** | `03_in_hand.txt` on **Nano 4K** 3:4, with the gray hand pose, packshot, avatar (skin) and `card_v2`. Then the **Sunburst** product fix. | 1 + 1 | 183 | 0.36 | ~2 min | ~3 min |
| **Hero banner with an avatar** (16:9, conair.com style) | `09_hero_banner.txt` on **Nano 4K** 16:9 (Sunburst 4K when Nano makes the hair too long), then the **Sunburst** product fix. | 1–3 + 1 | 183–508 | 0.36–0.80 | ~2–5 min | ~5 min |
| **Product-only banner** (16:9) | `10_product_banner.txt` on **Nano 4K** 16:9, then the **Sunburst 4K** product fix on a 16:9 crop. Plan for a second fix (the wordmark is often mirrored). | 1 + 1–2 | 183–310 | 0.36–0.56 | ~2–3 min | ~3 min |
| **5 s clip** | **Seedance 2.5** 720p from a final 16:9 image that already passed QA. Only the camera and the light move on products. | 1 | 856 | ~2.48 | ~2.5–5 min | ~2 min (frames) |

## 3 · What this POC used

| Item | Count | Cost |
|---|---|---|
| Looks: before, after, in use | 13 | Krea; history in `outputs/jobs_test20_plan.json` |
| Product images (soft environment + in hand) | 15 | Krea, plus 4 on Flora (USD 1.42) |
| Hero banners with avatars | 4 | Krea |
| Product banners | 5 | Krea |
| Clips | 5 | Krea, 856 CU each |
| Krea monthly limit per member | 60,000 CU | Reached on 2026-10-27; resets 2026-11-01 |

## Notes

- **The product fix is the step that makes it our product.** Budget 1 to 3 passes. QA at full zoom against the real packshot, not only `card_v2`.
- **`card_v2` has a wrong LOGO note on the flat iron.** It says "reading toward the plates". On the real iron the wordmark reads from the plates toward the hinge.
- **4K costs the same as 2K on Sunburst (127 CU)**, so always run 4K. On Nano, 4K is 56 CU against 37 at 2K.
