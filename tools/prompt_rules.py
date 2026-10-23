"""Prompt sentences that every generation of a category must carry (Conair POC, reviews of 2026-10-23).

Import them instead of retyping them, so a fix reaches every prompt:

    from prompt_rules import STAGING, IN_HAND_REAL, HAIR_FROM_AVATAR
    prompt = f"... {set_description}. {STAGING} Calm minimal composition ..."

  HAIR_FROM_AVATAR  in use: the gray render's sculpted hair leaks into the output (test 6), so the amount, length and
                    colour of her hair come from the avatar; add hair_length.prompt_line(...) right after it
  IN_HAND_REAL      in use: the product looked pasted on (test 4); same light, contact shadows, fingers and hair around it
  STAGING           soft environment: products stood upright balancing on a tip or floated (test 8); they must rest on a
                    real support. Write set descriptions that already lie the product down ("lying on its side across
                    the plinth"), never "standing upright on".
  MODEL             GPT Image 2.5 Sunburst (quality high) is the model for the POC (review, tests 4-8)

Pose choice (not a sentence): tools/pick_pose.py, front and three-quarter views first.
"""

MODEL = "openai/gpt-image-2.5-sunburst"

HAIR_FROM_AVATAR = ("The sculpted gray hair in image 1 only shows where her hair falls and how the tool holds it: take the amount, "
                    "density, length and colour of her hair from image 2 and the HAIR LENGTH line below, never from image 1.")

IN_HAND_REAL = ("The product is really in her hand: lit by the same soft studio light as she is, with soft contact shadows on her "
                "fingers, her fingers wrapped around it, and strands of her hair passing over and under it where they touch. "
                "It must not look pasted on.")

STAGING = ("STAGING (real physics): the product rests on a real support - lying flat on the surface, or leaning with its body "
           "against a prop - with a clear contact point and a soft contact shadow wherever it touches. It never stands upright "
           "balancing on its tip or its base, never floats or hovers. Every attachment lies flat on the surface. The cable lies "
           "on the surface and leads out of the frame naturally.")
