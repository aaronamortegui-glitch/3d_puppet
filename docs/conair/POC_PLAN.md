# Conair POC: what Nare asks, what we have, what to do

Sources:
- Nare's walkthrough video of 2026-10-23 ([transcript](TRANSCRIPT_2026-10-23_nare.md));
- the FigJam board "CONAIR Products": its sections Market References, Suggested Generation Plan and Section 1.

## 1. What Nare asks

**Client context.** Conair (Devin, Director of E-commerce Content; Christina, beauty) wants a steady partner for Amazon PDP content: images, copy, AEO. They first asked to see a "products in use" test with BaByliss Pro.

**POC scope** (FigJam, "Suggested Generation Plan"):

| Item | Amount |
|---|---|
| Products | 4 BaByliss Pro: Style/Switch, Auto Curler 1", Thermal Round Brush 1¼", Ultra-Sleek 1½" flat iron. These are the same 4 we researched. |
| Avatars | 4-6, the same ones reused in every category |
| Hair types and colours | 4-6 |
| Main categories per SKU | 4, with 3-5 images per category |
| Extra categories | 2, more generic: combo looks and videos |
| Target | Millennials, Amazon listings |

**The 6 categories and who owns them:**

| # | Category | What the listing shows | Owner |
|---|---|---|---|
| 1 | Product in use ("clients using the product") | A model styling her hair with the tool, ad framing, blue or white background | **Aaron** |
| 2 | Before / after | The same person side by side, before and after; repeated in the top 3 images of every listing ("new and repetitive, we need to handle this") | Miguel |
| 3 | Product in hand | A hand holding the product, close-up on blue, with callouts; shows scale | **Aaron** |
| 4 | Product on a soft environment | The product alone on a surface with a drop shadow, soft set | **Aaron** |
| 5 | Combo looks (no product) | Several avatars with different hair types, showing the range | Miguel |
| 6 | Videos | How-to videos with the product; lifestyle videos without it that show the end result | Miguel (Gustavo can help) |
| - | Avatars and outfits | 4-6 avatars, set up at the start, so every category uses the same people | Gustavo |

**Key point from Nare.** The same avatars must appear across every category. Random people in each image would be much weaker.

**Dates.** Internal meeting on Monday; client call on Wednesday.

## 2. What we already have and what changes

| Need | What we have | Gap |
|---|---|---|
| Product in use (1) | A pipeline that works: approved pose photo → gray render with hair (A1) + pose details (A2) → Nano Banana with packshot and person (B1). Close-ups use a masked outpaint. A reference library of 80 photos by tool (`samples/library`). | It is not organised by product × shot type, and only some poses have a gray render. It does not take Gustavo's avatars as the identity input yet. |
| Before / after (2) | A style library of 21 combinations per SKU × hair type, in two forms: swatches and back-view heads. A "what goes with what" table backed by real evidence. | The listing shows B/A on a face, front view. Our libraries are the style reference Miguel needs: they say which style each SKU gives each hair type. |
| Product in hand (3) | Generated hand references at true scale for 6 SKU/colour combinations. Product cards per colourway. | The final ad shot is not generated yet: hand + product in close-up on the brand background. |
| Product on surface (4) | Real packshots, and product cards with views and details | New category: product on a surface with a drop shadow. Nothing generated yet. |
| Avatars | None | They come from Gustavo. We must agree on a format: front, 3/4, profile and back, plus hair type and colour. |
| Hair types and colours | 4 types (1-4) with illustrative samples | Nare asks for 4-6 types **and colours**. Colour is not in our library yet. |
| Rules: which product goes with which hair type and style | `hair_evidence.json` + `STYLE_LIBRARY.md` + the READ FIRST table | Not yet one machine-readable file the generator can use. |

## 3. Proposed project structure

Today the material is spread across `samples/` (experiments) and `docs/products/`. The proposal is a `library/` folder that holds only approved, reusable inputs, plus an `outputs/` folder for each category. Experiments stay where they are, and nothing is deleted.

```
library/
  products/<sku>/            card.png, card_clean.png, packshots/, hand.png, colours/<colour>/
  poses/<category>/<sku>/<pose_id>/
                             reference.jpg  (approved photo)
                             gray.png       (A1 gray render with hair)
                             pose.txt       (A2 pose details)
                             meta.json      (hands, camera, framing, crop)
  hair_styles/<sku>/<hair_type>/<attachment>/
                             swatch_before.png, swatch_after.png, back_before.png, back_after.png
  avatars/<avatar_id>/       front.png, three_quarter.png, profile.png, back.png, meta.json (hair type, colour, outfit)
  rules/
    product_hair_rules.json  SKU × hair type × attachment → allowed?, style result, evidence, heat
outputs/
  01_in_use/<sku>/   02_before_after/<sku>/   03_in_hand/<sku>/   04_surface/<sku>/
```

- `<category>` in `poses/` is `in_use` or `in_hand`. These are the "3D poses by segment" from our method.
- Large images stay gitignored, as today. The `meta.json` and `rules/*.json` files go in git.
- A script, `tools/build_library.py`, copies the approved files from `samples/` into `library/`. Nothing moves, so the existing scripts keep working.

## 4. The test we want to run

Inputs per generation:
- **product**: the clean card, or the packshot of the right colour;
- **avatar**: Gustavo's, or a temporary one until his are ready;
- **style**: the hair style that the rules allow for that SKU and that avatar's hair type, taken from `hair_styles/`;
- **pose**: the gray render with hair from `poses/`.

Outputs:
- **in use**: the B1 prompt with the avatar as identity;
- **before / after**: the same avatar, before with her natural hair, after with the style from the rules. This is input for Miguel or a joint test.
- **in hand** and **on surface**: built from the card and the hand reference.

## 5. Next steps (Aaron)

1. Create `library/` and `rules/product_hair_rules.json` from what we already have.
2. Pose library: for each SKU, pick 3-5 `in_use` poses and 2-3 `in_hand` poses, then run the gray render with hair.
3. Agree the avatar format with Gustavo, and get 1-2 temporary avatars so we can start.
4. First test per SKU: 3 images in use + 1 before/after with the same avatar.
5. Prompts for in hand and on surface (new categories).

## Status (2026-10-23)

- `library/` is built by `tools/build_library.py`; the structure and the avatar format are in [library/README.md](../../library/README.md).
- `docs/products/product_hair_rules.json` holds 23 rules: 21 allowed, plus 2 discarded (Auto Curler and Thermal Brush on coily hair).
- The pose library has 28 poses: 5 in use and 2 in hand per SKU. Each has a reference photo, a gray render with hair and pose details.
  - 24 gray renders were new, made with Nano Banana 2.1 on Krea (job IDs in `samples/pose_library/jobs.tsv`); the other 4 come from the earlier library test.
  - In-hand poses use the new prompt `server/prompts/gray_render_prompt_in_hand.txt` (hand only; it removes callouts and text).
  - Pose details are in `tools/pose_details.json`.
  - All 24 new renders were checked against their reference: same pose and framing, product in orange, no text left.
- Next: avatars (Gustavo), then the first test per SKU (in use + before/after with the same avatar).
