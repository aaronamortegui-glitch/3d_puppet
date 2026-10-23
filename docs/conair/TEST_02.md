# Conair POC, test 2: product in hand + product on a soft environment (2026-10-23)

These are Aaron's other two categories in Nare's plan. There is 1 image per SKU per category. Every input comes from `library/`. The images are in `outputs/03_in_hand/` and `outputs/04_surface/` (gitignored), and the Krea job IDs are in `outputs/jobs_test2.tsv`. Model: Nano Banana 2.1, 2K, 1:1 (Amazon square).

## Product in hand

Each image is 1 call with 3 input images:
1. the pose: the gray in-hand render `poses/in_hand/<sku>/<sku>_in_hand_01/gray.png` (for the Style/Switch, its hand reference `products/style_switch/nano_blue/hand.png`);
2. the packshot of the right colour;
3. the front view of the same avatar as in test 1, so the skin tone matches across categories.

The prompt names the product's details and size, and asks for the hand and forearm only, on a soft brand-coloured backdrop: light blue for the Nano Blue tools, blush pink for Pink Rush.

| SKU | Avatar (skin) | Pose |
|---|---|---|
| auto_curler | tmp_a_wavy | in_hand_01 |
| thermal_brush | tmp_b_curly | in_hand_01 |
| style_switch (air curler) | tmp_b_curly | product hand reference |
| flat_iron Pink Rush | tmp_a_wavy | in_hand_01 |

## Product on a soft environment

Each image is 1 call, packshot only (plus the clean card for the flat iron). The product lies alone on a soft set with a drop shadow:
- Auto Curler: cream plaster with linen;
- Thermal Brush: beige stone on oatmeal fabric;
- Style/Switch: the body plus 4 attachments on cream plaster;
- flat iron: blush plaster with pink satin.

## Review

All 8 images worked on the first try: the products are faithful (colours, buttons, proportions), the hands look natural with the right skin tone, and the sets are clean. One minor point: the Pink Rush iron on the surface is slightly open although the prompt asked for it closed.

Figma: page "Product research", frame "CONAIR POC · TEST 2" (node 95:2), next to TEST 1 (94:2).
