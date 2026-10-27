# Test 21: hero banners in the conair.com style (2026-10-27)

## Reference

I analysed the 9 home banners of conair.com (downloaded for internal use to `samples/web_refs/conair_home/`, gitignored).

- **Format:** panoramic (about 2.7:1 on desktop). The people fill the right half; the left third is clean background for the headline.
- **Background:** one saturated seamless studio colour (sky blue, violet, hot pink to coral, orange, yellow, red), sometimes a gradient and a coloured gel rim light. The wardrobe matches or complements it.
- **Framing:** very tight, chest or shoulders up, the head often cropped. The product is big and close to the lens, held by the face or in use.
- **Mood:** real joy: open laughs, squinting eyes, head tilts, hair in motion.
- **Groups:** three women with different hair types, staggered, each with a product, each looking a different way.
- **Light:** high-key soft front light, glowing skin.

## Method

- Template: `prompts/conair/09_hero_banner.txt`.
- Model: Nano Banana 2.1, 16:9, 4K (5504 × 3072), thinking high.
- Inputs, original only:
  - **Close-up:** avatar front, the hair cut out of the real reference after, the lock, `card_v2`.
  - **Group:** three avatar fronts and three `card_v2` sheets; the hair is described in words.
- Prompts and job ids: `outputs/21_hero_banners/plan.json`.

## Run 1 rejected: it skipped the methodology

The first 6 banners (`*_pink.png` … `*_skyblue.png`, prompts in `plan.json`) left out three things:
- the calibrated HAIR LENGTH and RESULT TEXTURE lines;
- the hair cut out of the real reference, in the groups;
- the product fix.

The A06 and A01 hair came out wrong. They are kept as an experiment and not used.

## Run 2: full methodology (`plan_v2.json`)

- Every woman gets the same lines as her look in test 20, taken from `jobs_test20_plan.json`:
  - the calibrated HAIR LENGTH AND VOLUME line;
  - RESULT TEXTURE;
  - the hair cut out of her real reference (`after_hair.png`) and the lock;
  - `card_v2`.
- Groups: 3 fronts + 3 hair cutouts + 3 product sheets (9 inputs), and the lines for each woman.
- QA: `tools/measure_after.py` on each banner (or each woman, cropped). The result must stay within 15% of her test 20 after.

| Banner | Model | Hair end (after → banner) | Verdict |
|---|---|---|---|
| c1 A10 diffuser, pink | Nano 4K | bottom of bust → hair end at the crop | OK |
| c2 A01 round brush, violet | Nano 4K | chin 1.20 → chin 1.14 | OK |
| c3 A07 thermal brush, sky blue | Nano: armpits 1.77 (3 tries). **Sunburst 4K: collarbone 1.48** | collarbone 1.56 | OK on Sunburst |
| c4 A06 flat iron, orange | Nano: armpits 1.71–1.79 (3 tries). **Sunburst 4K: collarbone 1.62** | shoulders 1.46 (+11%) | OK on Sunburst |
| g1 A02 + A03 + A09, violet | Nano, then Sunburst | Nano: A02 bust (must be shoulders). Sunburst: A02 OK, A03 longer (ribs, must be bust) | NOT OK |
| g2 A08 + A04 + A01, sky blue | Nano, then Sunburst | Nano: A08 −18%. Sunburst: A04 chest (must be collarbone), A01 shoulders (must be chin) | NOT OK |

**Lessons:**
- **Nano lengthens straightened hair:** collarbone or shoulder hair comes out to the armpits, even with a hard limit and without the hair cutout. When the length matters, use Sunburst, as in the after.
- **Groups:** the models do not hold three calibrated lengths at once.

The 4 close-ups have the product fix (crop at the exact model shape → `08` → register + stitch): `*__fixed.png`, jobs in `jobs_inpaint.tsv`.

## Pending

- **Groups.** Options:
  - fix each woman's hair with a segmented inpaint on her crop;
  - or compose the group from approved single-woman frames.
