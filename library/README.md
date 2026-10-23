# library/: approved generation inputs (Conair POC)

This folder holds only approved, reusable inputs. It is built from `samples/` by
`server\.venv\Scripts\python.exe tools\build_library.py`. The build copies files and never moves them, so the experiments stay in `samples/`. Images are gitignored; this README is tracked. The sources the build reads are `tools/library_manifest.json`, `tools/pose_details.json`, `tools/pose_hair.json` and `docs/products/product_hair_rules.json`.

| Folder | Content | Used for |
|---|---|---|
| `products/<sku>/<colour>/` | `card.png` (for people), `card_clean.png` (model input), `hand.png` (hand + product at true scale, generated), `packshots/` (real photos), `meta.json` | Product identity in every category |
| `poses/in_use/<sku>/<id>/` | `reference.*` (real photo), `gray.png` (gray clay render with hair, product in orange), `pose.txt` (pose details), `meta.json` (with the sculpted hair: `hair.end_landmark`, `texture`, `volume`, `body`) | Category 1, product in use |
| `poses/in_hand/<sku>/<id>/` | The same, hand only | Category 3, product in hand |
| `hair_styles/_before/type<n>/` | `swatch_before.png`, `back_before.png` | Before / after: the natural hair |
| `hair_styles/<sku>/type<n>/<key>/` | `swatch_after.png`, `back_after.png`, `rule.json` | Before / after: the style this product gives this hair type |
| `rules/product_hair_rules.json` | SKU × hair type × attachment: allowed, result style, evidence status, heat | Which style goes with which product and avatar |
| `avatars/<avatar_id>/` | See below. Filled by hand; a rebuild keeps it. | The same people in every category |

SKUs: `auto_curler` (BNTAC100), `thermal_brush` (BNTHTB125), `style_switch` (BNTSSSW / BNTSSCC) and `flat_iron` (BNT131T, in pink_rush, nano_blue and iced_blue).

Hair types: 1 straight, 2 wavy, 3 curly, 4 coily. Two combinations are discarded: auto_curler × 4 and thermal_brush × 4. See the rules file.

## Avatar format (to agree with Gustavo)

```
avatars/<avatar_id>/
  front.png          head and shoulders, neutral expression, plain light background
  three_quarter.png
  profile.png
  back.png           back of the head, natural hair, for the hair-style reference
  meta.json          {"hair_type": "3", "hair_subtype": "3B", "hair_colour": "dark brown", "skin": "...", "outfit": "...",
                      "hair_end": 1.71, "hair_end_landmark": "armpits", "hair_volume": "big", "body": "slim", "notes": "..."}
```

`hair_end` (head heights from the top of the head) is measured once on `front.png` with `tools/scene_qa.py`; `hair_volume` is flat / medium / big. Both drive the hair length in the prompt (`tools/hair_length.py`) and the pose choice (`tools/pick_pose.py`).

## One generation = one combination

product (`card_clean` or a packshot of the right colour) + avatar (identity) + pose (`gray.png` + `pose.txt`) + hair style (the rule for SKU × the avatar's hair type) → `outputs/<category>/<sku>/`

Pick the pose by the avatar's hair, as the rule picks the style: the sculpted hair of the gray render leaks into the output, so its length, texture and volume must match hers.

```
python tools/pick_pose.py <avatar_id> <rule_key>   # ranked in-use poses: ok / check / avoid, with the reason
python tools/pick_pose.py --matrix                 # best pose per avatar x rule; shows where the pose library has no match
```
