# Conair POC, test 5: hair length proportional to the style (2026-10-23)

Straightening or blowing out a curl makes the hair longer, and curling straight hair makes it shorter. This test adds that change to the rules, the prompt and the QA, then checks it on Gustavo's avatars, with and without the new prompt line.

- Plan: `outputs/jobs_test5_plan.json`
- Images: `outputs/06_hair_length/`
- QA: `outputs/qa_results_test5.json`
- All outputs are gitignored.

## The model

The model lives in `tools/hair_length.py` and `docs/products/product_hair_rules.json`.

- **Visible length** = stretched length × (1 − shrinkage). For one avatar, the after/before ratio is (1 − shrinkage of the result style) / (1 − shrinkage of her curl pattern).
- **Her curl pattern**: `hair_length.shrinkage` in the rules.

  | Type | 1 | 2A | 2B | 2C | 3A | 3B | 3C | 4A | 4B | 4C |
  |---|---|---|---|---|---|---|---|---|---|---|
  | Shrinkage | 0% | 5% | 8% | 12% | 20% | 30% | 40% | 50% | 60% | 70% |

  These are the low end of the usual ranges, because heat styling rarely releases all of the shrinkage.
- **The result style**: each rule has an `after_shrinkage`. `null` means the style keeps the curl pattern (the diffuser), so the length stays the same.
- **Units**: lengths are in head heights, measured from the top of the head. They are mapped to body landmarks: jaw, chin, shoulders, collarbone, armpits, middle of the chest, bottom of the bust, bottom of the ribs, waist, hips.
- **Calibration**: the model was checked against Gustavo's own before/after pairs.

  | Case | Gustavo's images | Model |
  |---|---|---|
  | Curling iron on straight hair | ×0.83 | ×0.80 |
  | Sleek blowout on 3C hair | ×1.42 | ×1.53 |

- **Avatars**: each avatar's before length is measured once on her front photo and stored in `library/avatars/<id>/meta.json` (`hair_subtype`, `hair_end`). Gustavo's H4 and H9 were added from FigJam node 56:34.
- **Prompt line**: `prompt_line()` writes "HAIR LENGTH: her hair now ends at the &lt;landmark&gt; (before: at the &lt;landmark&gt;); it is about N% longer/shorter … Keep exactly this length."
- **QA**: `tools/scene_qa.py` gained a hair metric.
  - The hair mask comes from MediaPipe's `selfie_multiclass.tflite`, which goes in `SCENE_QA_MODELS`.
  - `hair_end` is the lowest hair point, in head heights (face-mesh forehead-to-chin × 1.3).
  - `hair_error` is the hanging length divided by the target, minus 1.
  - `hair_cropped` flags hair that leaves the frame. In that case `hair_end` is a lower bound.
  - Cases without a gray render now measure the hair only.

## Results

The test covers 6 cases. Before/after images were made on Nano Banana 2.1 (old prompt and prompt with the length line). In-use images were made on Sunburst high, with test 4 as the "old" version.

| Mean \|hair_error\| | Old prompt | With the length line |
|---|---|---|
| Before/after | 10% | 6% |
| In use | 11% | 5% |

- The mean gap between an avatar's length in the before/after image and in the in-use image dropped from 0.23 to 0.12 head heights.
- The biggest gains came from the largest changes:

  | Case | Old prompt | With the length line |
  |---|---|---|
  | Coily round-brush blowout | −29% | −11% |
  | 3C sleek blowout, in use | −23% | 0% |
  | Auto Curler, before/after | +12% | 0% |

## Review

- The review found that coily hair still looked like it gained too much hair: the model had pushed it to the bottom of the ribs.
- Fix, applied in test 6:
  - `SS_t4_roundbrush` `after_shrinkage` went from 0.25 to 0.4.
  - A HAIR AMOUNT line was added to `prompt_line()`.

## Figma

| File | Location | Node |
|---|---|---|
| Design file | below test 4 | 100:2 |
| FigJam CONAIR, page "study" | section | 66:70 |
| FigJam Essilor | section | 1306:269 |
