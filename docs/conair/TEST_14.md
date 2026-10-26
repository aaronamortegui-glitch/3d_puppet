# Test 14: product relight, Sunburst vs Sunburst + Nano Banana 2.1 (2026-10-26)

## Question

Does a Nano Banana 2.1 relight improve the light of the Sunburst product still lifes (category 4, product on a soft environment)?

## How

**Inputs.** One test 8 still life per SKU, with the support rule:
- Auto Curler on white marble;
- Thermal Brush on a travertine tray;
- Style/Switch on a sage plinth;
- flat iron Nano Blue on white marble.

**Relight.** `prompts/conair/05_relight_nano.txt`, Nano Banana 2.1 at 2K, 1:1:
- the instruction keeps everything and improves only the light;
- image 2 is the packshot, so the product stays exact.

**Measure.** Besides the review by eye, the mean pixel change between the two images is measured (out of 255).

## Results

| Product | Mean change | Verdict |
|---|---|---|
| Auto Curler | 2/255 | no real gain: near identical, a little more neutral |
| Thermal Brush | 6/255 | no real gain: a touch brighter, cleaner white balance |
| Style/Switch, with the packshot | 80/255 | **fail**: Nano returned the packshot (all attachments) instead of the scene |
| Style/Switch, scene only (retry) | 3/255 | no real gain |
| Flat iron | 2/255 | no real gain |

## Decision

1. **Sunburst alone stays the model for this category.** The relight adds almost nothing, and with a busy packshot as image 2 it can replace the whole scene.
2. **The relight is not part of the workflow.** To change the light, ask for it directly in the Sunburst prompt (`04_soft_environment.txt`).

## Where

**Files:**
- Images and prompts: `outputs/14_product_relight/`.
- Side by sides: `outputs/14_product_relight/compare/`.
- Plan and job ids: `outputs/jobs_test14_relight_plan.json`.

**Boards:**

| Board | Node |
|---|---|
| Design file | 176:2 |
| FigJam CONAIR, page "study" | 160:229 |
| FigJam Essilor | 1317:401 |

The total cost was about $0.40.
