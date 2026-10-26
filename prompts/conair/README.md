# Conair prompt templates

There is one template per category. Each file has two parts:
- a header, which lists the inputs **in the order the model receives them**, as library paths;
- the prompt, after `---`, with `{placeholders}`.

## Fill a template

Never fill a template by hand. Use the script:

```
python tools/fill_prompt.py in_use  client_a07_burgundy_curls SS_t3_diffuser style_switch_in_use_02 r58
python tools/fill_prompt.py after   client_a09_blonde_straight AC_t1 - r43
python tools/fill_prompt.py in_hand client_a02_coily - flat_iron_in_hand_01 - pink_rush
python tools/fill_prompt.py soft_env - - - - --sku flat_iron --set "lying on its side across a pale travertine plinth ..."
```

The script prints the resolved input paths and the full prompt. It **refuses** five things:
- a forbidden product × hair combination;
- a rule for another hair type;
- a rejected pose;
- a reference that is not grade A.

For an in-use image it also prints the pose verdict (ok, check or avoid).

## The templates

| File | Category | Model | Inputs |
|---|---|---|---|
| `01_in_use.txt` | 1 · Product in use: the finished style, product in her hand | Sunburst, 3:4 | gray pose, avatar, product sheet, hair lock, real after |
| `02_after.txt` | 2 · The after of a before / after | Sunburst, 3:4 | avatar (the before), hair lock, real after |
| `03_in_hand.txt` | 3 · Product in hand | Sunburst, 1:1 | gray hand pose, packshot, avatar (skin tone) |
| `04_soft_environment.txt` | 4 · Product on a soft environment | Sunburst, 1:1 | packshot |
| `05_relight_nano.txt` | 4 · Step 2 (test): relight with Nano Banana 2.1 | Nano Banana 2.1 | Sunburst output, packshot |

## Where the fixed sentences come from

The fixed sentences live in `tools/prompt_rules.py`:
- `HAIR_FROM_AVATAR`;
- `IN_HAND_REAL`;
- `STAGING`.

The `HAIR LENGTH` and `HAIR AMOUNT` lines come from `tools/hair_length.py`. To change a rule, change it there, so it reaches every prompt.
