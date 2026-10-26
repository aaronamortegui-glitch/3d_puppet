# Conair POC: handoff (2026-10-23)

This package lets someone continue the BaBylissPRO / Conair image POC. It contains every input, every generated image with the exact prompt that made it, the rules, the tools and the findings. The code lives in the repo `aaronamortegui-glitch/3d_puppet` (branch `main`). This folder is a copy made with `tools/export_handoff.py`.

## What the POC does

It generates product images for 4 SKUs, in 4 categories, from fixed inputs, so the same people and products stay consistent across shots.

**SKUs:**
- Auto Curler BNTAC100
- Thermal Brush BNTHTB125
- Style/Switch air styler
- Nano Titanium flat iron, in Pink Rush, Nano Blue and Iced Blue

**Categories and inputs:**

| Category | Inputs |
|---|---|
| **In use** | gray 3D pose render (the product in orange at its true size), avatar (identity), product character sheet, hair-style references (close-up and back view) |
| **Before / after** | avatar before photo and hair-style references; Miguel owns this one in the POC plan |
| **In hand** | gray hand pose (or the product's hand reference), packshot, avatar for the skin tone |
| **On a soft environment** | packshot; the set is described in the prompt |

**The steps for one image:**

1. Pick the rule (product × hair type).
2. Pick the pose (`pick_pose.py`).
3. Fill the prompt (the template plus `prompt_rules`).
4. Generate.
5. Run QA (`scene_qa.py`).

## Folder map

**`01_library/`** holds the approved inputs. In the repo it is built by `tools/build_library.py` from `samples/`.

| Path | Content |
|---|---|
| `products/<sku>/<colour>/` | `card_clean.png` (model input), `card.png`, `hand.png`, `packshots/` |
| `poses/in_use/<sku>/<pose>/` | `gray.png` (clay render, product in orange), `reference.*` (real photo), `pose.txt` (pose details for the prompt), `meta.json` (sculpted-hair tags: length, texture, volume, body, view, notes) |
| `poses/in_hand/<sku>/<pose>/` | the same, hand only |
| `hair_styles/<sku>/type<n>/<rule>/` | `swatch_after.png`, `back_after.png`, `rule.json`; `_before/` holds the natural references |
| `avatars/<id>/` | `front.png` plus `meta.json` (hair type and subtype, length in head heights, volume, body). Gustavo's avatars come from FigJam CONAIR node 56:34 (H1–H9); H2, H3, H4, H5, H6 and H9 are here. `gustavo_after.png` is his own after image. `tmp_*` are the early temporary avatars. |
| `rules/product_hair_rules.json` | |

**`02_rules_and_tools/`:**

| File | What it is |
|---|---|
| `docs/products/product_hair_rules.json` | 23 rules (SKU × hair type × attachment): allowed or forbidden, evidence (works, mixed, low evidence, no proof), result style, and `after_shrinkage`, plus the `hair_length` model (shrinkage per curl type, body landmarks). Forbidden: Auto Curler and Thermal Brush on coily (type 4) hair. |
| `tools/pose_hair.json` | Sculpted hair of every pose, tagged by eye, plus the view (front, three_quarter, profile, back) |
| `tools/hair_length.py` | Target hair length after styling, and the HAIR LENGTH / HAIR AMOUNT prompt lines |
| `tools/pick_pose.py` | Ranks the poses for an avatar and a rule (ok / check / avoid). `--matrix` gives the best pose per avatar × rule. |
| `tools/prompt_rules.py` | The sentences every prompt must carry: hair taken from the avatar, product really held in the hand, support rule for sets, and the model |
| `tools/scene_qa.py` | Measures an output against its gray render: pose drift, framing, product size (Grounding DINO + SAM) and hair end (MediaPipe hair segmenter) |
| `docs/conair/LOOKS_X_PRODUCTS.md` + `docs/products/looks_by_product.json` | Which product gives each of Nare's 10 reference looks, per hair type and with evidence (Figma node 107:2) |
| `docs/conair/HAIR_REFS.md` + `docs/products/hair_refs.json` | The 58 real before/after hair references, split and classified by SKU and graded, plus the 10 client avatars (`library/avatars/client_a01..a10`) |
| `docs/conair/` | Every test write-up (TEST_01 to TEST_08), POSE_HAIR, POC_PLAN and the transcript of Nare's brief |
| `docs/products/` | Product sheets, hair evidence audit, style library notes |

**`03_tests/test_NN_*/`** contains, per test:

- `images/`;
- `prompts/<image>.txt` with the model, the settings, the input images in order (as library paths) and the full prompt;
- `jobs.json`;
- the `TEST_NN.md` write-up.

In the prompt files, `library/...` means `01_library/...` in this package.

Tests 1–2 kept only job IDs: their prompts follow the template of test 3.

## Model and settings

| Use | Model |
|---|---|
| Everything | GPT Image 2.5 Sunburst (`openai/gpt-image-2.5-sunburst`, quality high, 2K) |
| Fallback | Nano Banana 2.1 (`google/nano-banana-2.1`, 2K) |

- Both run through Krea. The cost is about $0.12 (Sunburst) and $0.08 (Nano) per image, and each takes about 45 s.
- Sunburst has no 4:5 or 5:4 aspect ratio; use 3:4 or 1:1.
- Sunburst results are not at Krea's public URL; read them from the job (`get_job`).

## Rules learned (apply them to every new image)

1. **Product × hair rule first.** Never generate a forbidden combination. Prefer the works and mixed evidence levels for client-facing images.
2. **Pick the pose by her hair** (`pick_pose.py`). The sculpted hair of the gray render leaks into the output:
   - a curly mane gave a coily avatar "too much hair";
   - a short bob on a long-haired avatar looked unreal.

   Front and three-quarter views come first; profile and back views break identity and hair more often.
3. **The hair comes from the avatar.** The prompt says so (`HAIR_FROM_AVATAR`) and adds the length and amount lines (`hair_length.prompt_line`):
   - straightening or blowing out curls makes the hair longer, and curling straight hair makes it shorter, by the shrinkage of each curl pattern;
   - the amount and density stay the same, and the volume stays realistic;
   - in-use shots are mid-process: the styled sections have the new length and the rest keep her natural texture.
4. **The product must be held, not pasted on** (`IN_HAND_REAL`): same light, contact shadows, fingers around it, hair passing over and under it.
5. **On a set, the product rests on a real support** (`STAGING`). It lies flat or leans against a prop with a contact shadow, and never stands on its tip or floats. Write the set description lying down from the start.
6. **The orange proxy in the gray render must be the real product silhouette.** Both models copy a wrong proxy:
   - Nano turned the Style/Switch into a pistol-grip dryer in test 4;
   - Sunburst did the same in hand in test 8.

   The proxy also sets the product size, and the size error was 3–77% when the proxy was a different tool.
7. **QA on every output** (`scene_qa.py`). Regenerate when:
   - |product size error| > 25%;
   - the face scale moves more than 15%;
   - |hair error| > 15%.

## Tests

The Figma file "3d-puppet" (BIhbEhtz1sq2tjW5pzraUm), page "Product research", has one frame per test. The same boards are in FigJam CONAIR-Products (2tItrDWjhCt5uVTxcyKePK), page "study", and in FigJam Essilor-Luxottica (zNRup5nO3L8dQqmiCqXwe2).

| Test | What it covers | Design-file node |
|---|---|---|
| 1 | First in-use and before/after shots, temporary avatars | 94:2 |
| 2 | In hand and on a soft environment, 1 per SKU | 95:2 |
| 3 | 3 images per SKU in all 4 categories (Nano Banana) | 96:2 |
| 4 | Nano Banana vs Sunburst 1-to-1, architecture, QA metrics | 98:2 |
| 5 | Hair length kept proportional (shrinkage model, prompt line, QA metric) | 100:2 |
| 6 | Architecture per device, hair amount and pasted-product fixes | 101:2 |
| 7 | Sculpted-hair tags and the pose picker; conclusion: Sunburst | 104:2 |
| 8 | Product images on Sunburst plus the support rule | 105:2 |

## Open next steps

1. **Fill the gaps in the pose library** (`POSE_HAIR.md`). Render new gray poses for:
   - curly 3A–3C hair (Auto Curler, Thermal Brush, flat iron);
   - coily hair with the real Style/Switch silhouette as the proxy;
   - straight hair with the Style/Switch paddle or round brush.

   Use front or three-quarter views, sculpt the hair from the avatar, and build the proxy from the real product silhouette.
2. **Tag every new pose** in `tools/pose_hair.json`, and measure `hair_end` for every new avatar (`scene_qa.py` on `front.png`).
3. **Before / after** (Miguel): use the HAIR LENGTH and HAIR AMOUNT lines, and the same avatar and length across shots.
4. **Turn the plan scripts into one generator** that reads the rules, the picker and `prompt_rules`, writes the prompt, generates on Sunburst and runs the QA gate.
