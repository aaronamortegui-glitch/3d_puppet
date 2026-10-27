# CLAUDE.md: Conair / BaBylissPRO image POC

## Who and what

**The person.** Aaron (Superside). Chat in Spanish. Everything in the repo, in Figma and in FigJam is in English.

**The POC.** Generate Amazon PDP images for 4 BaBylissPRO SKUs. The same client avatars appear in every category.

**Categories and owners:**

| Category | Owner |
|---|---|
| 1 · In use | Aaron |
| 2 · Before / after | Miguel |
| 3 · In hand | Aaron |
| 4 · Product on a soft environment | Aaron |

How it works: [docs/conair/pipeline.png](docs/conair/pipeline.png). Full handoff: [docs/conair/HANDOFF.md](docs/conair/HANDOFF.md).

## Make one look: before → after → in use (test 13)

1. **After** (`prompts/conair/02_after.txt`).
   - Command: `python tools/fill_prompt.py after <avatar> <rule> - <rNN>`.
   - Inputs: the avatar front, the real reference before and after, and the lock.
   - The length and width change exactly as in that real pair (`docs/products/hair_change.json`).
   - It keeps the background.
   - Save it to `library/avatars/<avatar>/after/<rule>__<rNN>.png`, then measure where its hair ends: `SCENE_QA_MODELS=<models> server/.venv/Scripts/python.exe tools/measure_after.py <after.png>` (writes the `.json` next to it).
2. **In use** (`prompts/conair/01_in_use.txt`).
   - Command: `python tools/fill_prompt.py in_use <avatar> <rule> <pose> <rNN>`.
   - Inputs: the gray pose v2, the step 1 after, the product sheet and the lock.
   - The hair and the background come from the after. The prompt gets a hard HAIR LENGTH line: the hair ends exactly where it ends in the after (test 17).

**Final assets, clean (gitignored):** `outputs/FINAL_2026-10-26/` with `01_before/`, `02_after/`, `03_in_use/`, `04_product/` and a README.

## Make one image (details)

1. **Rule.** Pick the rule for the product × the avatar's hair type in `docs/products/product_hair_rules.json`. Never use a forbidden one: Auto Curler and Thermal Brush on coily hair.
2. **Pose.** Run `python tools/pick_pose.py <avatar> <rule>`. Use front or three-quarter poses with the verdict ok, or check at worst.
3. **Hair reference.** Pick a grade A reference of that rule from `library/hair_styles/<sku_slot>/<rule>/`. See `docs/conair/HAIR_REFS.md`.
4. **Prompt.** Run `python tools/fill_prompt.py in_use <avatar> <rule> <pose> <ref>`. It gives the inputs in order and the prompt.
5. **Generate.** Use Krea, model `openai/gpt-image-2.5-sunburst`, quality high, 2K, aspect 3:4 or 1:1 (Sunburst has no 4:5). Read the results from `get_job`.
6. **QA.** Run `tools/scene_qa.py`. Regenerate when:
   - the product size error is more than 25%;
   - the face scale moves more than 15%;
   - the hair length error is more than 15%.
7. **Save.** Write to `outputs/` (gitignored). Keep the prompt and the job id next to each image, and put the results on the boards.

## Library (`library/`, rebuilt by `tools/build_library.py`, gitignored)

| Folder | What | Name convention |
|---|---|---|
| `avatars/` | Client avatars: `front.png` + `meta.json` (hair type, subtype, colour, measured hair end). `_archive/` holds the earlier avatars. | `client_aNN_<look>` |
| `poses/in_use/<sku>/`, `poses/in_hand/<sku>/` | Approved poses only: `gray.png` (the orange proxy is the true product size), `reference.*`, `pose.txt`, `meta.json` (sculpted-hair tags). `poses/_rejected/` holds the ones that do not work, with the reason (`tools/pose_status.json`). | `<sku>_in_use_NN`, `<sku>_in_hand_NN` |
| `products/<sku>/<colour>/` | `card_clean.png` (the product sheet, model input), `card.png`, `hand.png`, `packshots/` | sku: `auto_curler`, `thermal_brush`, `style_switch`, `flat_iron`; colour: `nano_blue`, `pink_rush`, `iced_blue` |
| `hair_styles/<sku_slot>/<rule>/<ref_id>/` | The style input, from real photos (grade A): `lock.png` (texture), `after.png` (shape), `before.png`, `ref.json` | sku_slot: the 4 SKUs, with the Style/Switch split per attachment (`style_switch_round_brush`, `_paddle`, `_air_curl`, `_diffuser`); rule: `AC_t1` … `SS_t3_diffuser`; ref_id: `rNN` |
| `hair_styles_generated_v1/` | The old generated swatches and back-view heads. No longer an input. | |
| `rules/` | `product_hair_rules.json`, `hair_refs.json`, `looks_by_product.json` | |
| `prompts/` | Copy of `prompts/conair/` | `NN_<category>.txt` |

## Rules learned in reviews (do not break them)

**Hair:**
- Identity, colour and length come from the avatar. Texture comes from the real hair lock. Shape comes from the real after.
- Never use a generated wig or head as the style.
- The length follows `hair_length.py`:
  - straightening stretches the hair by the shrinkage of its curl pattern;
  - curling shortens it.
- The amount stays the same: no added volume.

**Poses:**
- The sculpted hair of the gray pose leaks into the output.
  - Never use a pose with big or abundant sculpted hair (hard rule, test 12).
  - For finished in-use shots, pick the pose by the after: `pick_pose.py <avatar> <rule> --finished`.
  - The pose details lose their hair sentences, and straight or blowout results get an explicit `RESULT TEXTURE` line (`fill_prompt.py`).
- Use front or three-quarter views. Profile and back views break identity and hair.
- The orange proxy must be the real product silhouette, because models copy a wrong proxy.

**Product:**
- In use, the product is held for real: same light, contact shadows, fingers around it (`IN_HAND_REAL`).
- On a set, the product rests on a support and never floats or stands on its tip (`STAGING`).

**In use:** show the finished style, the after, with the product in use. Never a before and after combined.

**Models:** Sunburst for the looks (after, in use). For product images, in hand and on a soft environment (tests 15, 16, validated 7/7): Nano Banana 2.1 makes the image (`03_in_hand.txt` / `04_soft_environment.txt`), then Sunburst corrects only the product (`06_product_fix_sunburst.txt`). A Nano relight of a Sunburst image adds nothing (test 14).

## Working rules

**Drives:**
- Never write to drive E:. Reading `E:\Superside\3d_puppet\...` (avatars, video) is fine.

**Experiments and images:**
- Never delete tested experiments.
- Downloaded web images are for internal use and stay gitignored.

**Boards:**
- Figma content goes in grids, never one long column.
- Every study goes on three boards:
  - the Figma design file `BIhbEhtz1sq2tjW5pzraUm` (page "Product research");
  - the FigJam CONAIR-Products `2tItrDWjhCt5uVTxcyKePK`;
  - the FigJam Essilor `zNRup5nO3L8dQqmiCqXwe2`.

**Costs:**
- Flora: quote the cost in USD before running, and do not retry billing failures.
- Krea is the approved fallback.

**Products:** no people in product cards, except a hand.
