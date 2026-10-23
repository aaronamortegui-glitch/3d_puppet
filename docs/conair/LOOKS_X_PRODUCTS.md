# Hair looks × products: which product gives each look Nare asked for (2026-10-23)

Nare's brief asks for the before/after shot, which is in the top 3 images of every listing, and for 4–6 hair types and colours on the same avatars. Her board (CONAIR FigJam, Market References) collects 10 reference looks: the 9 BEFORE - AFTER listing images, which Gustavo rebuilt as avatars H1–H9, and the Curling Wand image of the COMBO block.

Each cell comes from `docs/products/product_hair_rules.json` for the hair type shown in the reference. The data is in `docs/products/looks_by_product.json`. ★ marks the product to feature for the look: the one in the listing image when the image names one.

| Look | Hair before → after | Avatar | Auto Curler 1" | Thermal Brush 1¼" | Style/Switch | Flat iron 1½" |
|---|---|---|---|---|---|---|
| **L1 · Glossy defined waves**<br>Before / After (auburn) | 2B wavy → glossy, defined, bouncy waves | H1 | ★ ⚪ low evidence `AC_t2`<br>uniform glossy 1" curls replacing her waves | — not this look<br>a polished blowout with bent ends, not defined waves | 🟡 mixed `SS_t2_aircurl`<br>1.5" air-curling barrels: soft bouncy waves | — not this look<br>flat-iron waves only proven on straight hair |
| **L2 · Defined coils**<br>Before / After (coily) | 4A-4B coily → defined, springy coils, less frizz | H2 | ⛔ forbidden `AC_t4`<br>does not work on coily hair | ⛔ forbidden `TB_t4`<br>does not work on coily hair | ★ 🟡 mixed `SS_t4_diffuser`<br>diffuser: defined coils with volume | — not this look<br>straightens (silk press, brand claim only) |
| **L3 · Smooth & Shiny Results**<br>flat iron listing | 2B wavy → sleek, straight, glossy | H3 | — not this look<br>curls, not straight | ✅ works `TB_t2`<br>polished smooth blowout, with more body than an iron | 🟡 mixed `SS_t2_paddle`<br>paddle brush: sleek straight blow-dry | ★ 🟡 mixed `FI_t2`<br>sleek straight (works on straight hair: FI_t1) |
| **L4 · Frizz-Free Shine**<br>flat iron listing | 2C-3A curly → sleek, straight, no frizz | H4 | — not this look<br>curls, not straight | ✅ works `TB_t3`<br>sleek almost-straight blowout | ✅ works `SS_t3_roundbrush`<br>round brush: stretched blowout, some puffiness | ★ ⚪ low evidence `FI_t3`<br>smooth shiny straight |
| **L5 · Flawless Without the Fuss**<br>Auto Curler listing | 1 straight → classic defined 1" curls | H5 | ★ ✅ works `AC_t1`<br>classic defined 1" curls | — not this look<br>blowout with root lift and bent ends | 🟡 mixed `SS_t1_aircurl`<br>air-curling barrels: soft curls that drop fast | ✅ works `FI_t1_waves`<br>loose flat-iron waves, not barrel curls |
| **L6 · The Blowout Standard**<br>Thermal Brush listing | 2A-2B wavy → volume, bounce and shine | H6 | — not this look<br>curls, not a blowout | ★ ✅ works `TB_t2`<br>polished blowout (TB_t1 on straight hair) | 🟡 mixed `SS_t2_roundbrush`<br>round brush: smooth voluminous blowout | — not this look<br>flat and straight, no volume |
| **L7 · Round Brush · smooth & shine as you dry**<br>air styler listing | 2B-2C wavy → smooth blowout with movement | H7 | — not this look<br>curls, not a blowout | ✅ works `TB_t2`<br>same look on dry hair | ★ 🟡 mixed `SS_t2_roundbrush`<br>round brush attachment (works on curly: SS_t3_roundbrush) | — not this look<br>flatter, no movement |
| **L8 · Paddle Brush · smooth & detangling blowout**<br>air styler listing | 2B wavy → sleek straight blow-dry | H8 | — not this look<br>curls, not straight | ✅ works `TB_t2`<br>polished, with more body | ★ 🟡 mixed `SS_t2_paddle`<br>paddle brush attachment | 🟡 mixed `FI_t2`<br>sleeker and flatter than a blow-dry |
| **L9 · Perfectly Polished · sleek blowout**<br>Thermal Brush listing | 3C curly → sleek polished blowout, frizz tamed | H9 | — not this look<br>smoother 1" curls, not a blowout | ★ ✅ works `TB_t3`<br>sleek almost-straight blowout | ✅ works `SS_t3_roundbrush`<br>round brush: stretched blowout, some puffiness | ⚪ low evidence `FI_t3`<br>straight, flatter than a blowout |
| **L10 · Curling Wand · long-lasting curls**<br>COMBO block (air styler) | 1-2 straight or wavy → soft curls and waves | - | ✅ works `AC_t1`<br>1" curls on straight hair (AC_t2 low evidence on wavy) | — not this look<br>blowout, not curls | ★ 🟡 mixed `SS_t1_aircurl`<br>air-curling barrels (SS_t2_aircurl on wavy) | ✅ works `FI_t1_waves`<br>loose waves on straight hair |

## How to read it

- **Straight, sleek looks** (L3, L4, L8):
  - The flat iron is the product in those listings.
  - On wavy and curly hair, the Thermal Brush has the strongest evidence.
  - The Style/Switch paddle and round brush give mixed results on wavy hair; the round brush works on curly hair.
- **Blowouts** (L6, L7, L9):
  - The Thermal Brush works on types 1–3.
  - The Style/Switch round brush works on curly hair and gives mixed results on wavy hair.
- **Curls and waves** (L1, L5, L10):
  - The Auto Curler is proven only on straight hair; on wavy hair the evidence is low.
  - The Style/Switch air-curling barrels give mixed results.
  - The flat iron makes loose waves on straight hair.
- **Coily hair** (L2):
  - Only the Style/Switch with the diffuser gives this look, with mixed results.
  - The Auto Curler and the Thermal Brush do not work on coily hair, so we never generate them on type 4.

**Rule for the POC:** each image uses the ★ product of its look, on the Gustavo avatar with that hair type. Cells marked forbidden or not this look are never generated. Cells with low evidence or a brand claim only are flagged before the client sees them.

## Figma

| File | Location | Node |
|---|---|---|
| Design file "3d-puppet" | page "Product research", below test 8 | 107:2 |
| FigJam CONAIR-Products | page "study" | 77:202 |
| FigJam Essilor | section | 1310:401 |

## Simple view: one row per SKU (Figma 110:2)

The Style/Switch is split into its 4 attachments, because each attachment is its own use case and can be shown as its own SKU. The examples are our own images on Gustavo's avatars. The new paddle-brush and curling-barrel before/afters were made on Sunburst in test 9. Test 10 completed the in-use images: the paddle brush on H3 (`style_switch_in_use_03`), and the round brush on H4 curly, where the round brush works, with `style_switch_in_use_02`; both poses were picked by `tools/pick_pose.py`. All of them are in `outputs/09_examples/`, and every SKU now has a before, an after and an in-use image.

Known limit: in the paddle in-use image the brush head reads a little rounded rather than flat.

| SKU | What it does | Straight | Wavy | Curly | Coily | Our example |
|---|---|---|---|---|---|---|
| Auto Curler 1" (BNTAC100) | 1-inch curls | ✅ works | ⚪ few reports | ⚪ few reports | ⛔ does not work | gustavo_h5_long_brown: AC_t1 |
| Thermal Round Brush 1¼" (BNTHTB125) | smooth polished blowout | ✅ works | ✅ works | ✅ works | ⛔ does not work | gustavo_h6_blonde_wavy: TB_t2 |
| Style/Switch + 1¾" round brush | blow-dry with volume | 🟡 mixed | 🟡 mixed | ✅ works | 🟡 mixed | gustavo_h4_curly: SS_t3_roundbrush (test 10, before/after + in use) |
| Style/Switch + paddle brush | straight sleek blow-dry | 🟡 mixed | 🟡 mixed | — not used | — not used | gustavo_h3_wavy_black: SS_t2_paddle (test 9 before/after, test 10 in use) |
| Style/Switch + 1½" air-curling barrels | soft curls and waves with air | 🟡 mixed | 🟡 mixed | — not used | — not used | gustavo_h6_blonde_wavy: SS_t2_aircurl (test 9) |
| Style/Switch + diffuser (Curly & Coily kit) | defines curls and coils | — not used | — not used | ✅ works | 🟡 mixed | gustavo_h2_coily: SS_t4_diffuser |
| Ultra-Sleek flat iron 1½" (BNT131T) | straightens; loose waves on straight hair | ✅ works | 🟡 mixed | ⚪ few reports | ▫️ brand claim only | gustavo_h3_wavy_black: FI_t2 |

Figma nodes for the simple view:

| File | Node |
|---|---|
| Design file | 110:2 |
| FigJam CONAIR (page "study", below the first table) | 80:202 |
| FigJam Essilor | 1311:401 |
