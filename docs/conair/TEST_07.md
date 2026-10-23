# Conair POC, test 7: picking the pose by the avatar's hair (2026-10-23)

This test generates no new images. It tags the sculpted hair of every pose and adds a picker that chooses poses by the avatar's hair. Details are in [POSE_HAIR.md](POSE_HAIR.md).

## Additions from the review

- **View**:
  - every pose in `tools/pose_hair.json` now has a `view`: front, three_quarter, profile or back;
  - `tools/pick_pose.py` adds 0.6 for a profile view and 1.2 for a back view, because they break identity and hair more often;
  - front and three-quarter poses are preferred.
- **Hair volume**: the HAIR AMOUNT line in `tools/hair_length.py` now asks for realistic volume, never fuller than in her before photo unless the style adds root lift.
- **Model**: GPT Image 2.5 Sunburst high is the POC model (`tools/prompt_rules.MODEL`).

## Figma

| File | Location | Node |
|---|---|---|
| Design file | below test 6 | 104:2 |
| FigJam CONAIR, page "study" | section | 70:202 |
| FigJam Essilor | section | 1308:401 |

Each board has four parts:

- A: the 20 poses with their tags.
- B: a matrix of the best pose per avatar × device, coloured ok / check / avoid.
- C: the two test 4 failures, both flagged "avoid".
- D: conclusion and gaps.
