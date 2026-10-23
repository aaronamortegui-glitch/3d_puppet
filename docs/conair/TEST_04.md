# Conair POC, test 4: Nano Banana 2.1 vs Sunburst high, 1-to-1 (2026-10-23)

This test uses Gustavo's avatars and runs each case on two models with exactly the same inputs and prompt. It asks four questions:

- which model does the job better;
- why the body changes;
- how well the product keeps its size from one scene to the next;
- what the hair length should do.

- Avatars: Gustavo's H2 (coily), H3 (black wavy), H5 (long brown straight) and H6 (blonde wavy). They are saved as `library/avatars/gustavo_*/front.png`; the source is FigJam CONAIR, node 54:34.
- Cases: 8, two in-use poses per SKU, and each case runs on both models, for 16 images.
- Plan, prompts and job IDs: `outputs/jobs_test4_plan.json`.
- Images: `outputs/05_model_compare/<sku>__<avatar>__<pose>__nano|sunburst.png`.
- All outputs are gitignored.

## Architecture (one generation)

Inputs, in this order:

1. **Pose**: the gray 3D render from `library/poses/in_use/<sku>/<pose>/gray.png`. The product is shown in orange at its true size.
2. **Avatar**: `library/avatars/<id>/front.png`, which sets the identity.
3. **Product character sheet**: `library/products/<sku>/<colour>/card_clean.png`.
4. **Hair style, close-up**: `library/hair_styles/<sku>/type<n>/<rule>/swatch_after.png`.
5. **Hair style, back view**: `back_after.png` from the same folder.

The rule (`docs/products/product_hair_rules.json`) selects inputs 4 and 5 and fills `{hair}` with the rule's `result_style`. Forbidden combinations are never generated: AC_t4 and TB_t4 (Auto Curler and Thermal Brush on coily hair).

Both models receive the same prompt:

- image roles (1 = pose and framing, orange = product at its true size; 2 = identity; 3 = exact product; 4–5 = hair texture in her own colour);
- "EXACTLY the pose … every body part stays at the same pixel position" plus the POSE DETAILS from `tools/pose_details.json`;
- replace the orange object with the product, with a PRODUCT SIZE line and "keep exactly the length and thickness of the orange object relative to her hand and head";
- `Her hair: {hair}`, the same top as in image 2, studio light and a plain light-gray background.

Models:

| Model | Resolution | Cost per image |
|---|---|---|
| `google/nano-banana-2.1` | 2K, 4:5 | ~$0.08 |
| `openai/gpt-image-2.5-sunburst` | quality high, 2K | ~$0.12 |

## QA: `tools/scene_qa.py`

Each output is measured against its gray render:

- **Pose drift**: mean distance between 13 MediaPipe Pose body keypoints, as a % of the image side.
- **Framing**: the ratio of face scale (eye distance from Face Landmarker) between the output and the render.
- **Product size**:
  - In the output, the product is found with Grounding DINO, its mask comes from SAM, and its main-axis length is divided by the eye distance.
  - This is compared with the orange proxy in the render, measured the same way. The cable is removed from the proxy first with an adaptive opening.

```
server\.venv\Scripts\python.exe tools\scene_qa.py outputs\qa_cases.json outputs\qa_results.json
```

The script needs two environment variables:

- `SCENE_QA_PYLIBS`: a folder holding transformers (installed with `pip --target`);
- `SCENE_QA_MODELS`: a folder holding `pose_landmarker_heavy.task` and `face_landmarker.task`.

It writes the masks to `outputs/qa/` so they can be checked by eye.

## Results

| Case | Nano: pose drift / framing / size | Sunburst: pose drift / framing / size |
|---|---|---|
| auto curler · in_use_05 (H5) | 30.8% / ×1.27 / +59% | 2.2% / ×1.04 / +54% |
| auto curler · in_use_02 (H5) | 11.6% / ×1.68 / −34% | 5.5% / ×1.14 / +7% |
| thermal brush · in_use_04 (H6) | 19.9% / ×0.99 / −31% | 7.2% / ×1.02 / −34% |
| thermal brush · in_use_02 (H6) | 13.1% / ×1.11 / −27% | 13.8% / ×1.12 / −17% |
| style switch · in_use_05 (H2, diffuser) | 2.1% / ×1.00 / +61% | 7.4% / ×1.05 / +77% |
| style switch · in_use_02 (H2, round brush) | 9.9% / ×1.01 / +20% | 10.0% / ×0.95 / +12% |
| flat iron · in_use_03 (H3) | n/a / ×1.04 / −24% | n/a / ×1.09 / +3% |
| flat iron · in_use_01 (H3) | 2.3% / ×0.98 / +14% | 1.6% / ×0.96 / +14% |

Averages:

| | Nano | Sunburst |
|---|---|---|
| Pose drift (7 cases with a detected body) | 12.8% | 6.8% |
| Product size error (absolute) | 34% | 27% |

## Findings

1. **The body changes because of input 1.**
   - The gray render keeps the body of the person in the original pose photo, for example the curvy body in the thermal-brush poses, and both models blend that body with the avatar.
   - Sunburst follows the render more closely.
   - Nano Banana reframed 2 shots (the face up to ×1.68 bigger) and moved the body more.
   - Fix: choose poses whose body matches the avatar, or re-render the gray pose from the avatar's body.
2. **Product shape.**
   - When the orange proxy disagreed with the product sheet, Nano Banana copied the proxy: the dryer-shaped proxy became a pistol-grip dryer.
   - Sunburst followed the sheet.
   - Both models reproduce colours, buttons and wordmarks well.
3. **Product proportion is not held reliably by either model.** The best cases are within 3–15%. The worst are +60–77%, where the proxy was a different tool. To keep the proportion:
   - (a) build the proxy from the real product silhouette at its true size;
   - (b) give sizes in body units in the prompt, for example "barrel as long as her face";
   - (c) gate on QA: regenerate when |size error| > 25% or the face scale moves more than 15%.
4. **Hair length must stay proportional.**
   - Straightening or blowing out a curl makes the hair longer in proportion to its shrinkage:

     | Hair type | Shrinkage |
     |---|---|
     | 1 | ~0% |
     | 2 | ~10% |
     | 3A–3B | 30–40% |
     | 3C | ~50% |
     | 4 | 50–75% |

   - One avatar must keep the same length across in-use and before/after shots.
   - The TB_t3 after in test 3 came out far too long.
   - Next step:
     - add a shrinkage factor per hair type to `product_hair_rules.json`;
     - write the target length in the prompt with a body landmark (for example "ends at the collarbone");
     - add a hair-length metric to `scene_qa.py`.
5. Both models keep identity, and hair-style injection (inputs 4–5) works on both.

**Current pick:**

- Sunburst high for in-use shots with a product, because it holds the pose and the product shape better.
- Nano Banana for edits on a single image (before/after, backgrounds).
- QA on every output.

## Rules for Gustavo's avatars

| Avatar (hair type) | Auto Curler | Thermal Brush | Style/Switch | Flat iron |
|---|---|---|---|---|
| H5, H8 straight (1) | OK | OK | OK (round brush, paddle, air curlers) | OK |
| H1, H3, H6, H7 wavy (2) | low evidence | OK | OK | mixed |
| H4 (3A), H9 (3C) curly | low evidence | OK | OK (diffuser, round brush) | low evidence |
| H2 coily (4) | **FORBIDDEN** | **FORBIDDEN** | mixed (diffuser, round brush) | no proof (brand claim only) |

## Figma

Each board has three parts: A, an architecture diagram linking the inputs to the prompt, the models, the outputs and QA; B, the 8 cases compared 1-to-1; C, the findings.

| File | Location | Node |
|---|---|---|
| Design file "3d-puppet" | page "Product research", frame "MODEL TEST · …", below test 3 | 98:2 |
| FigJam "CONAIR-Products" | page "study", section to the right | 64:34 |
| FigJam "Essilor-Luxottica" | section | 1305:233 |
