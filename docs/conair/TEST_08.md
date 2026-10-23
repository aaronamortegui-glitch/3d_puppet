# Conair POC, test 8: product images on Sunburst and the support rule (2026-10-23)

The 16 product images of test 3 (8 in hand, 8 on a soft environment) were first made with Nano Banana 2.1. Here they run again on GPT Image 2.5 Sunburst, quality high, 2K, 1:1, with the same inputs and the same prompt.

The review said the soft-environment images "should rest against something, they look like they are floating". So the 8 soft-environment images ran once more with the support rule.

- Plans and job IDs: `outputs/jobs_test8_plan.json` (Sunburst, same prompt) and `outputs/jobs_test8b_plan.json` (with the support rule).
- Images: `outputs/08_product_sunburst/`
- Cost: 24 × ~$0.12.

## Inputs

| Category | Inputs |
|---|---|
| In hand | the gray hand pose (or the product's `hand.png` reference), the packshot, and the avatar for the skin tone |
| Soft environment | only the packshot; the set is described in the prompt |

## Support rule: `tools/prompt_rules.STAGING`

> The product rests on a real support: it lies flat on the surface, or leans with its body against a prop, with a clear contact point and a soft contact shadow wherever it touches. It never stands upright balancing on its tip or its base, and it never floats. Every attachment lies flat. The cable lies on the surface.

Set descriptions that asked for "standing upright" were rewritten:

| Set | Before | After |
|---|---|---|
| Sage plinth | the body standing upright on the plinth | "lying on its side across the plinth" |
| Plaster block | the brush leaning on the block | "handle resting on the block, bristle head on the sweep" |

## Findings

1. **In hand**, Sunburst gives sharper products (a readable wordmark, true Nano Blue and Iced Blue) and more natural hands.
   - One miss: on `style_switch in_hand_01` Sunburst followed the gray proxy (a pistol-grip dryer); Nano kept the slim body.
   - Same lesson as test 4: the proxy must be the real product silhouette.
2. **On a soft environment**, Sunburst is more realistic, but without the rule it stood products up (the Style/Switch upright on the plinth, the brush on its tip), and they looked like they were floating.
3. **With the support rule**, all 8 rest on a real support with contact shadows, and they keep the same premium look.
4. **Conclusion**: Sunburst high for every category, with the rules in `tools/prompt_rules.py`.

## Figma

| File | Location | Node |
|---|---|---|
| Design file | below test 7 | 105:2 |
| FigJam CONAIR, page "study" | section | 72:202 |
| FigJam Essilor | section | 1309:401 |
