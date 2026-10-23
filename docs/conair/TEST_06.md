# Conair POC, test 6: architecture per device, coherent hair (2026-10-23)

The review of tests 4–5 raised three problems:

- some outputs had far more hair than the avatar ("where does so much hair come from");
- the product looked pasted on;
- some cases did not look like reality.

This test finds the causes, fixes them, and shows the full pipeline with one new example per device. It also shows the product images (in hand, soft environment) with their inputs and prompt.

- Plan, prompts and job IDs: `outputs/jobs_test6_plan.json`
- Images: `outputs/07_architecture/`
- QA: `outputs/qa_results_test6.json`

## Causes and fixes

1. **Extra hair comes from input 1.** The gray render has sculpted hair. `style_switch_in_use_02` has a big curly mane and `flat_iron_in_use_03` has a short wavy bob, and the models blend that hair with the avatar's. Fixes:
   - Each example now uses a pose whose sculpted hair matches the avatar's length and texture.
   - The prompt says: "take the amount, density, length and colour of her hair from image 2 … never from image 1".
2. **New HAIR AMOUNT line** in `hair_length.prompt_line()`: same amount and density as in her before photo, with no added volume or extensions. The length changes only by stretching or curling her own hair.
   - Coily blowouts keep part of their texture: `SS_t4_roundbrush` `after_shrinkage` is now 0.4.
3. **In-use shots are mid-process.** `prompt_line(t, in_progress=True)`:
   - sections that are not styled yet keep her natural texture and length;
   - styled sections have the new length.
4. **Product integration line.** The product gets the same light and contact shadows as she does, her fingers wrap around it, and strands of hair pass over and under it. It must not look pasted on.

## Examples (same prompt to both models)

| Device | Pose | Avatar | Rule |
|---|---|---|---|
| Auto Curler | in_use_04 (long straight sculpted hair) | H5, straight 1B | AC_t1 |
| Thermal Brush | in_use_02 (long hair) | H4, curly 3A | TB_t3 |
| Style/Switch + air-curl barrel | in_use_03 (medium wavy) | H6, wavy 2B | SS_t2_aircurl |
| Flat iron | in_use_04 (long hair, iron gliding down) | H3, wavy 2B | FI_t2 |

QA, Nano / Sunburst:

| Device | Pose drift | Framing | Product size |
|---|---|---|---|
| Auto Curler | 24.3 / 13.1% | ×0.94 / ×1.03 | +30 / +39% (the proxy is a thick clamp iron) |
| Thermal Brush | 14.6 / 13.9% | ×1.33 / ×1.07 | −30 / −16% |
| Style/Switch | 20.3 / 11.4% | ×1.09 / ×1.07 | −15 / −28% |
| Flat iron | 22.5 / 21.5% | ×1.00 / ×0.98 | +5 / −3% |

## Findings

- **Hair** is coherent with each avatar in all 8 outputs: the same amount, natural texture where the tool has not passed yet, and no extra hair.
- **The product** sits in the hand with matching light and shadows.
- **Sunburst** shows the styling change clearly. Nano Banana often styles too little (Thermal Brush, Style/Switch) and reframed the Thermal Brush shot.
- **Pose drift** is higher than in test 4 (11–24%). The avatar's body is kept and these are three-quarter poses. Framing stays within 10% on Sunburst.
- **Product images** use fewer inputs:
  - in hand: the gray hand pose, the packshot and the avatar for skin tone;
  - soft environment: only the packshot, with the set written in the prompt.

  The rules and hair inputs do not apply there.
- **Pick**: Sunburst high for in-use shots; Nano Banana for in-hand, soft-environment and before/after edits.
- **Next**: tag every pose in `library/poses` with its sculpted hair (length, texture, volume), and pick poses by the avatar's hair, the way the rules pick the style.

## Figma

| File | Location | Node |
|---|---|---|
| Design file | below test 5 | 101:2 |
| FigJam CONAIR, page "study" | section | 68:70 |
| FigJam Essilor | section | 1307:269 |

Each block reads from left to right: the inputs (with labels), the full prompt, the model, then the output with its QA.
