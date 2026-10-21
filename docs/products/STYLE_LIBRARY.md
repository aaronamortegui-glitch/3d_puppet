# Hair style library (before -> after swatches)

Reference images of what each SKU does to each hair type, for later use as style input when generating hair. One lock of hair per hair type lies on a light-gray surface, shot from above; there is no person, so the reference carries only the hair style. Each AFTER is generated from the same BEFORE lock (Nano Banana 2.1, 2K, 2:3) and only the styling changes. The result described for each cell follows what real users get (see `HAIR_EVIDENCE.md`), not the brand promise; cells backed only by the brand are marked.

Images: `samples/products/style_library/swatches/<key>.png` (gitignored). Figma: page "Product research", frame "STYLE LIBRARY".

## Prompts

BEFORE (one per hair type):
> Macro reference photo of a single lock of human hair (a hair swatch about 30 cm long and 3 cm wide, bound at the top with a small black clip) lying flat on a plain light-gray matte surface, shot from directly above. Soft even studio light, sharp detail of individual strands. The hair is natural {TYPE}: {colour}, untreated and as-is, {texture}. No person, no scalp, no hands, no tools, no text.

AFTER (image 1 = the BEFORE lock):
> Image 1 is the BEFORE hair swatch. Create the AFTER photo of the SAME lock of hair: same hair colour, thickness and length, same black clip at the top, same light-gray matte surface, same top-down framing and light. Only the styling changes: it has just been styled with {tool and attachment}. Result: {result}. No person, no hands, no tools, no text.

## Index

| Key | SKU | Hair type | Attachment / technique | Result | Evidence |
|---|---|---|---|---|---|
| before_t1 | - | 1 straight | - | fine, light brown, flat | - |
| before_t2 | - | 2 wavy (2B) | - | irregular S-waves, some frizz | - |
| before_t3 | - | 3 curly (3B) | - | marker-size ringlets, frizz | - |
| before_t4 | - | 4 coily (4B-4C) | - | tight zig-zag coils, shrinkage | - |
| AC_t1 | BNTAC100 | 1 | - | classic 1" curls | real: used |
| AC_t2 | BNTAC100 | 2 | - | uniform 1" curls | real: used (1 review) |
| AC_t3 | BNTAC100 | 3 | - | smoother uniform curls | real: used (2 reviews) |
| (AC type 4) | BNTAC100 | 4 | - | does not apply | discarded |
| TB_t1 | BNTHTB125 | 1 | - | blowout, bent ends | real: used |
| TB_t2 | BNTHTB125 | 2 | - | polished blowout | real: used |
| TB_t3 | BNTHTB125 | 3 | ionic on | sleek, almost straight | real: used |
| (TB type 4) | BNTHTB125 | 4 | - | does not apply | discarded |
| SS_t1_roundbrush | BNTSSSW | 1 | round brush 1.75" | volume blowout | real: used |
| SS_t1_paddle | BNTSSSW | 1 | paddle brush | sleek | real: used |
| SS_t1_aircurl | BNTSSSW | 1 | air barrels 1.5" | soft curl that drops fast | real: mixed |
| SS_t2_aircurl | BNTSSSW | 2 | air barrels 1.5" | soft waves | real: mixed |
| SS_t2_roundbrush | BNTSSSW | 2 | round brush 1.75" | volume blowout | real: used |
| SS_t2_paddle | BNTSSSW | 2 | paddle brush | sleek | real: used |
| SS_t3_diffuser | BNTSSCC | 3 | diffuser | defined curls | real: used |
| SS_t3_roundbrush | BNTSSCC | 3 | round brush 1.75" | stretched blowout | real: mixed |
| SS_t4_diffuser | BNTSSCC | 4 | diffuser | defined coils (4A/4B) | real: mixed, weak on 4C |
| SS_t4_roundbrush | BNTSSCC | 4 | round brush 1.75" | stretched (4A/4B) | real: mixed, weak on 4C |
| FI_t1 | BNT131T(HP) | 1 | - | sleek straight | real: used (1 review) |
| FI_t1_waves | BNT131T(HP) | 1 | twist technique | loose waves | brand claim |
| FI_t2 | BNT131T(HP) | 2 | - | sleek straight | brand claim + sibling irons |
| FI_t3 | BNT131T(HP) | 3 | - | smooth straight | real: used |
| FI_t4_silkpress | BNT131T(HP) | 4 | silk press | bone straight | brand claim only |

## Audit of the internet evidence images (2026-10-21)

Every real-customer photo shown in the Figma "READ FIRST" table was reviewed by eye:
- removed: one Auto Curler before/after whose labels are reversed (the "after" is straighter), one Thermal Round Brush photo duplicated from Ulta to Sephora, and two flat-iron YouTube thumbnails that show the product but no hair result;
- flagged: Auto Curler "thick hair" photo (looks wavy, not straight), the two Auto Curler type-2 photos (wet hair: hair type only, no result), the Auto Curler type-3 photo (photo shows wavy hair), and the Style/Switch type-4 YouTube thumbnail (version unknown, no result visible).

## Back-view library: full wig heads (2026-10-21)

Same 21 combinations as the swatch library, shown on a whole head: a wig on a white mannequin with shoulders, seen from behind, on a pure white background. A swatch shows the texture up close; the back view shows the overall shape, length and volume of the style. The two libraries are complementary inputs.

- Files (gitignored): `samples/products/style_library/backview/` — `before_t1..t4.png`, one `<key>.png` per combination (same keys as the table above), `jobs.txt` (key → Krea job) and `before_urls.txt`.
- Model: Nano Banana 2.1 (Krea), 4:5, 2K. Each AFTER uses the matching BEFORE head as image 1.
- Figma: page "Product research", frame "BACK-VIEW LIBRARY · before → after wig heads" (node 76:2), to the right of the swatch library and with the same layout (products with packshots, one column per attachment, X for discarded cells).

BEFORE prompt (one per hair type):

> Back view of a full head of human hair (a wig) on a plain white mannequin head with shoulders, seen straight from behind, no face visible. Pure white seamless background, soft even studio light, sharp hair detail, the whole head and hair in frame. The hair is natural {TYPE}: {description}. No person, no hands, no tools, no text.

AFTER prompt:

> Image 1 is the BEFORE photo: a wig of human hair on a plain white mannequin head with shoulders, seen straight from behind. Create the AFTER photo of the SAME wig head: same hair colour, same density, same mannequin, same back view, same pure white background, same framing and soft studio light. Only the styling changes: the hair has just been styled with {tool / attachment}. Result: {result}. Realistic salon result, sharp hair detail. No person, no face, no hands, no tools, no text.

For straightening on curly and coily hair, the result says the hair is now longer, because the curls are stretched; without that line the model keeps the shrunken length.

Review: all 21 kept identity (colour, mannequin, framing). Three results were too weak and were regenerated with stronger prompts. The first versions are kept in `backview/v1/`, the jobs are in `v2_jobs.txt`, and the table shows v2.
- TB_t2: v1 stayed wavy. The v2 prompt says the waves are "COMPLETELY GONE", the lengths are sleek and only the ends are bent. Result: a clear polished blowout.
- SS_t1_aircurl: v1 showed full waves. The v2 prompt says the curls "have already fallen out", leaving only a weak bend in the bottom 10 cm. Result: mostly straight with a soft end bend, which matches the real-world reviews on fine hair.
- AC_t3: v1 was almost the same as the BEFORE. The v2 prompt says the small corkscrews are "REPLACED" by uniform 1-inch barrel curls. Result: bigger, glossy, regular ringlets.

Lesson: when the AFTER is close to the BEFORE, the model copies the BEFORE. Say what disappears (in capitals), not only what appears.
