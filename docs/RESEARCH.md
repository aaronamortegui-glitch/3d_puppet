# Research: rigged 3D puppet + pose and camera from a single photo (Blender)

*Date: October 2026 · Target: Blender 5.0 (Python 3.11) · Reference GPU: RTX 5090 Laptop 24 GB*

Goal: a fully rigged, fully controllable 3D puppet with wrists and fingers (open/close hands). From **a single photo** it must copy:

- the **pose** of the body and hands;
- the **camera**: angle, distance and focal length.

Everything is packaged as an **installable Blender add-on**.

License decision for this project: use is **internal / research**, so non-commercial models (SMPL-X, etc.) are allowed. Each component's license is still noted.

---

## 1. Decision summary

| Component | Choice | Why |
|---|---|---|
| Default puppet | **Own procedural mannequin** generated in Python, with an **SMPL-X skeleton (55 joints, 15 finger bones per hand)** | No license risk (all our GPL code). Bone names match estimator outputs 1:1. Artist-mannequin look. |
| Hand controls | Close / thumb / spread sliders per hand, plus presets (open, fist, point, peace, thumbs up, grip, pinch) | Finger bones use local X as the flexion axis, so a positive rotation closes the finger. |
| **Lite** backend | **MediaPipe Tasks 1.1.1** (Pose Landmarker heavy + Hand Landmarker) inside Blender's Python | Apache-2.0, CPU, ~1–2 s per photo, one-click install. |
| **Pro** backend | Local server (separate venv, PyTorch cu128) with **SAM 3D Body** (Meta), NLF and MediaPipe; **auto** mode picks the best fit | SAM 3D Body is the state of the art for body + hands + feet from one photo. NLF is the easy-to-install alternative. |
| Precision stage | **RTMW** 2D keypoints + hand crops → **direct rig fit** (forward kinematics of the puppet in PyTorch) | Pixel-level overlay with zero retarget loss in Blender. |
| Focal / FOV | User > EXIF > **MoGe-2** (Microsoft, MIT) > 35 mm default | Most models assume a fixed focal length; without the right focal the camera distance is wrong. |
| Camera angle | **GeoCalib** gravity (real pitch/roll) when available, else AUTO (level horizon) | Photos rarely have roll; GeoCalib recovers it when the scene allows. |

---

## 2. Rigged 3D puppets (with fingers)

| Option | License | Fingers | Controls | Notes |
|---|---|---|---|---|
| **Procedural mannequin (this repo)** | GPL-3 (own code) | 15 per hand (3 per finger) | FK + hand sliders/presets | Default. Skeleton = SMPL-X. |
| SMPL-X Blender add-on (MPI / Meshcapade) | Model **non-commercial**; Meshcapade acquired by Epic (Feb 2026) | 15 per hand (MANO) | FK, flat/relaxed presets | Highest fidelity with SMPL-X estimators. Not redistributable: each user brings their own model. v1.0.3 supports Blender 4.5+/5.x. |
| MPFB2 (MakeHuman) | GPL code; **CC0** assets | `game_engine`: 15 per hand; `default`: 15 + metacarpals | IK helpers; Rigify option | Best CC0 base for a realistic body. UE-style naming (`index_01_l`). |
| Rigify (bundled with Blender) | GPL | 15 + palm | Full IK/FK, finger masters (curl) | Ideal for animators. Drive the FK/ORG bones and compensate the A-pose rest. |
| Blender Studio Human Base Meshes | CC0 | no rig | — | Mesh to skin onto Rigify or MPFB. |
| Blender Studio Rain / Storm | CC-BY | yes | CloudRig IK/FK | Polished animation rigs, custom naming. |
| Mixamo | Commercial use OK, but **redistribution forbidden** | 15 per hand (`LeftHandIndex1-3`) | FK | Useful as a retarget profile for users' own characters. |
| Auto-Rig Pro | Paid (~$50) | yes, finger IK | IK/FK, fist | User-side only. |
| Quaternius Universal Base Characters | CC0 | 15 per hand (reported) | FK | Low-poly, UE naming. |
| **MHR — Meta Momentum Human Rig** | **Apache-2.0** | yes | — | Native rig of SAM 3D Body; FBX with LODs and an SMPL ↔ MHR converter. |
| **Anny (NAVER)** | Apache-2.0 / CC0 | yes (104 bones) | — | Parametric body model (ages and shapes), open alternative to SMPL-X. |
| Ready Player Me | **Shut down** (Netflix, Jan 2026) | — | — | Discarded. |
| Kenney | CC0 | no fingers | — | Discarded. |

**Conclusion:** the bundled puppet is the procedural mannequin. It uses SMPL-X names, so any estimator's output applies without mapping tables. For users' own characters (Mixamo, Rigify, MPFB, UE) the next step is **bone mapping profiles**.

---

## 3. 3D pose estimation from one photo (body + fingers + camera)

| Method | License (code / weights) | Hands | Camera | Windows + 5090 install |
|---|---|---|---|---|
| **SAM 3D Body** (Meta, 2025-26) | SAM License (commercial use with restrictions); gated weights on HF | **Yes**, 21 keypoints per hand (MHR70) | Full perspective; FOV via MoGe-2; accepts `cam_int` | Medium. We avoid detectron2 and pyrender by loading the core model and passing person boxes from torchvision. |
| Fast SAM 3D Body (ECCV 26) | MIT, uses SAM 3D Body weights | yes | same | ~65 ms on a 5090; bash scripts (WSL). |
| **NLF** (Neural Localizer Fields) | MIT / **non-commercial** weights | yes (SMPL-X, weaker hands) | Perspective; accepts intrinsics | **Easy**: one TorchScript file. |
| Multi-HMR / Multi-HMR 2 (NAVER) | CC BY-NC-SA / NC | yes (moderate) | Optional intrinsics | Easy to medium. |
| SMPLer-X / SMPLest-X | S-Lab NC | yes (coarse) | Fixed focal | Hard (torch 1.12 + mmcv), not 5090-compatible without rebuilding. |
| AiOS, OSX, Hand4Whole, PIXIE | NC | yes | Fixed or weak | Legacy, hard. |
| 4D-Humans (HMR2), TokenHMR, CameraHMR | NC (SMPL) | **no** | CameraHMR estimates FOV (HumanFoV) | — |
| WiLoR / HaMeR | NC (MANO) | Hands only (best fingers) | Weak perspective | Useful to refine fingers on hand crops. |
| **MediaPipe** Pose + Hands / Holistic | Apache-2.0 | 21 per hand | None (we solve it) | Trivial. Runs in Blender's Python. |
| **RTMW** / DWPose (rtmlib, ONNX) | Apache | 133 2D keypoints | — | Easy; 2D only. Used as the 2D target of the fitting stage. |

**Camera estimation:**
- **MoGe-2**: MIT, FOV + metric depth.
- **GeoCalib**: Apache / CC-BY, focal + **gravity direction** (real pitch and roll).
- **Depth Pro**: Apple, license to be confirmed.
- **Depth Anything 3**: Apache for the small models.
- **VGGT**: has a commercial variant.

---

## 4. Blender integration

### Add-on format
- **Blender extension (4.2+)**: `blender_manifest.toml` with `files` and `network` permissions, plus `bl_info` for legacy installs.
- **Lite dependencies** are pip-installed into the extension's user directory (`extension_path_user`), **never** into Program Files.
  - numpy is pinned to Blender's version (1.26.4 in 5.0).
  - Tested: `mediapipe 1.1.1` imports fine in Blender 5.0.1's Python 3.11.
- **Note:** Blender 5.1+ uses **Python 3.13**. Compiled dependencies are reinstalled with the button; the Pro server is unaffected because it runs in its own process.
- **PyTorch never goes inside Blender** (DLL conflicts, ~3 GB). It lives in the server (`server/.venv`); Blender talks to it over local HTTP (`127.0.0.1:8765`) using only the standard library.

### Point retarget (`puppet_pose/retarget.py`, Lite path)
1. Each bone has a spec with a primary vector (e.g. shoulder → elbow) and an optional secondary vector for twist (elbow plane, index–pinky line, hip line, ears/nose).
2. The same names are evaluated on the puppet's rest pose and on the model output, so **bone axes never need to match** between rigs.
3. With two vectors an orthonormal frame gives `G = F(target) · F(rest)ᵀ`; with one, the minimal swing is applied on top of the parent rotation.
4. Global → local: `basis = R_restᵀ · G_parentᵀ · G · R_rest`.

### Camera (`puppet_pose/camera_utils.py`, `pose_apply.py`)
- **Focal:** `lens_mm = f_px · sensor_width / max(W, H)` with `sensor_fit = AUTO` and a 36 mm sensor. From EXIF 35 mm equivalent: `f_px = f35 / 43.27 · diag_px`.
- **Principal point:** `shift_x = (W/2 − cx)/max(W,H)`, `shift_y = (cy − H/2)/max(W,H)`.
- **Translation:** `f(X+tx) − (u−cx)(Z+tz) = 0` (and the same in y) is linear in `t`; solved by weighted least squares.
- **Frames:** OpenCV (x right, y down, z forward); internal W_c = `(x, z, −y)` with the camera at the origin looking +Y; a Blender camera is `Euler(90°, 0, 0)` in W_c.
- **Orientation modes:** **AUTO** (default; real gravity from GeoCalib when available, otherwise level horizon with pitch from the body), **UPRIGHT**, **LEVEL**, **NONE**.
- **Ground:** the puppet is lowered so its lowest point touches z = 0; the camera moves with it.
- **Background:** the photo is the camera background (alpha 0.6) and render resolution matches the photo. Photos with EXIF rotation get an upright copy because Blender ignores EXIF.

### Reference projects studied
- **PoseCap (Corridor, GPL-3)**: closest reference (Blender extension + separate GPU process, MediaPipe lite mode).
- **BlendArMocap** (GPL-3, discontinued): MediaPipe → Rigify math.
- **FreeMoCap add-on** (AGPL, study only), **SMPL-X add-on**, **CEB 4D Humans**, **MoPA**, **Rokoko / Expy Kit / Retarget (KBS)**.

---

## 5. Round 1 validation

| Test | Result |
|---|---|
| `tests/test_roundtrip.py`: known pose + camera → synthetic points → retarget | Bone direction error **0.25° mean** (fingers 0°). Reprojection **1.6 px** after camera fit. Focal **exact**. AUTO roll = **0.00°**. With known gravity, a 12° rolled camera is recovered **exactly** (−9.96° / 11.82°). PASS. |
| `tests/test_lite_render.py`: EEVEE render of the posed mannequin → MediaPipe → new puppet | Camera distance **3.58 m = original**, elevation 8.3° vs 7.6°, same focal. MediaPipe does **not** detect wooden hands and reads the faceless mannequin as seen from the back; real photos behave much better. |
| Extension installed from the zip (isolated profile) | Install → enable → *Install Lite Dependencies* → *Pose From Photo* → *Re-apply*: all OK in Blender 5.0.1. |

Implementation notes:
- Blender does not allow a registered operator to subclass another registered operator; a mixin is used.
- NLF's TorchScript needs `import torchvision` before `torch.jit.load` (registers `nms`).
- NLF exposes `estimate_smpl_batched(images, boxes)`: when its YOLO detector fails, external boxes are passed.
- `glob('**')` does not enter dot folders such as `extensions/.user/`.
- The **front/back** ambiguity is the most common single-photo error. *Flip Front/Back* swaps left/right and mirrors depth while keeping the 2D projection; the Pro server detects it automatically.

---

## 6. Round 2: deep research + 2D fitting

### Research findings (4 tracks)
- **Video mocap** (Move.ai, Rokoko, DeepMotion, WHAM, GVHMR, GEM-X…): **does not improve a still photo**. Duplicating the frame adds no information; temporal models only smooth. Worth trying only **Autodesk Flow Studio** (exports a Blender scene with camera) and **DeepMotion "3D Pose"** as a cheap commercial reference.
- **Community (Reddit, GitHub, Hugging Face)**: **no ready-made tool** reaches this precision with fingers and camera. *Clip Studio Pose Scanner* is rough and skips fingers; *PoseCap* does not solve the camera; *ComfyUI-SAM3DBody* exports FBX with mirrored bones. The recommended recipe everywhere: **strong regressor + fit to 2D keypoints + silhouette**.
- **State of the art**: **SAM 3D Body** is the best regressor (EMDB 61.7 mm vs NLF 68.4 mm) and accepts *keypoint prompts*; **RTMW-x** (70.2 whole-body AP) and **Sapiens2** (308 keypoints) are the best 2D detectors; **WiLoR** is best for fingers (FreiHAND 5.5 mm); **DPoser-X** is the best pose prior.
- **Avatars**: lossless transfer is **MHR + SAM 3D Body** (needs an importer; community `sam-3d-body-fbxify` as a start). Alternative: the official **SMPL-X add-on**.

### Implemented
- **SAM 3D Body** on Windows + RTX 5090 without detectron2 or pyrender.
- **RTMW** (rtmlib, ONNX): 133 whole-body 2D keypoints, 21 per hand.
- **`server/methods/fit.py`**: moves the regressor's 3D points until their projection matches RTMW, with the **puppet's** bone lengths, a per-point depth prior (single global shift, so points cannot slide along their rays), regressor directions where there is no 2D evidence, COCO hips down-weighted, border keypoints ignored, and automatic front/back detection.

### Lens (focal length)
`server/lens_report.py` compares estimators (35 mm equivalent):

| Photo | MoGe-2 | GeoCalib |
|---|---|---|
| 01 | 44.8 | 56.4 |
| 02 | 41.5 | 38.4 |
| 03 | 43.4 | 59.9 |
| 04 | 42.4 | 45.2 |

- MoGe-2 is consistent; GeoCalib varies a lot on plain studio backgrounds.
- **Lens search by fitting** (try 18–135 mm, keep the one most consistent with the puppet's proportions) was **not reliable**: at 1–2 m the perspective changes too little between lenses and the error curves are flat.
- **Pending:** validate with photos of **known focal length** (EXIF) to measure each estimator's real error.

---

## 7. Round 3: fitting the rig directly, hands, keypoint editor

**Diagnosis.** Even with fitted points at ~1 px, the posed puppet was **50–100 px** off the photo (measured with `tools/measure_overlay.py`): retargeting points onto a rigid skeleton with different proportions loses precision.

**Solution: `server/methods/fit_rig.py`.**
- Forward kinematics of the puppet skeleton (same rest pose and hierarchy) runs in PyTorch.
- One rotation per bone + the root translation are optimised against the 2D keypoints, with the regressor's depth as a prior and a pose prior.
- Blender applies the global rotations as-is: server vs Blender difference is **0.0 px**; the camera is placed from the exact pelvis position.
- **Multi-start**: the fit starts from both the point-fitted and the raw regressor skeleton and keeps the best (the same photo could land at 5 px or 25 px depending on the start).

**Hands (`server/methods/hands.py`).**
- **Chirality**: detects a mirrored hand (palm ↔ back) and fixes it by mirroring depth without changing 2D. It happened on several hands.
- **High-resolution crop re-detection** (512 px) with MediaPipe Hands.
- **Duplicate hands**: RTMW sometimes puts both hands on the same physical hand; the side is decided with the regressor's projected wrists.
- **Finger joint limits** in the rig fit: PIP/DIP joints are pure hinges toward the palm, no hyperextension, MCP with limited spread and no twist.

**Out-of-frame limbs.** Points the regressor places outside the image are kept outside during the fit, and bones without any 2D evidence (e.g. a hand out of frame) are reported as `unseen` and hidden in Blender with a Mask modifier (*Hide Unseen Limbs*).

**Head.** The eyes are used as head references, because ears are often covered by hair.

**Auto mode.** Runs SAM 3D Body, NLF and MediaPipe, fits each and keeps the lowest error.

**Keypoint editor + OpenPose.** Movable points in Blender → *Re-fit* (`/refit` endpoint). `tests/test_keypoint_editor.py`: moving the wrist by 60 px, the puppet follows within **6.9 px**; the OpenPose round trip is exact.

**Pending.**
- Validate the lens with EXIF photos.
- Learned pose prior (DPoser-X).
- Silhouette term (person mask) for an even tighter overlay.

---

## 8. Capture-side options (when we control the shoot)

Everything above works on **existing** photos. When the photos are shot by us, the most precise path is the film/VFX approach:

- **Camera:** a printed **ChArUco / ArUco board** (or a few markers) visible in a test frame gives the exact focal length, lens distortion and camera position with OpenCV calibration. This is how matchmove/VFX teams lock the "same camera shot".
- **Body:** an **inertial mocap suit** (Rokoko Smartsuit, Xsens, Noitom) with **gloves** records the exact skeleton and fingers without any camera; or **optical markers** with ≥2 synchronized cameras triangulate exact 3D. With a **single** camera, markers only make the 2D points sharper (they do not solve depth by themselves).
- **AI-painted markers** (asking an image model to add a mocap suit, skull cap and markers to an existing photo) add **no measurement**: the model guesses where markers go and can alter the pose. Tested with Nano Banana 2.1 on the 4 sample photos (`server/prompts/mocap_assist_prompt.txt`, `pose_server --assist`):
  - the head stays within 2–5 px, but shoulders and elbows move 12–55 px and one image turned the head;
  - hybrid mode (body from the AI image, hands from the original) gave 5–17 px fit error vs 3–11 px with the original only: **no clear gain**.
  Not a substitute for real markers.

---

## 9. Round 4: generative clean renders, pose variations, reference library

**Idea.** If a photo is hard to measure (hair over the face, fabric, a product that looks like a hand), ask an image model to redraw the **same shot** as a clean gray 3D render, then run the pipeline on it. Nano Banana 2.1 (Flora, 2K, ≈ $0.08 per image) with the prompts in `server/prompts/`:

- `gray_render_prompt_v1.txt` — gray clay, bald, no clothing.
- `gray_render_prompt_v2_bald.txt` / `gray_render_prompt_v2_hair.txt` — same, but the **held product is painted solid orange (#FF6A00)** so it is never confused with the hand, and the hair version keeps the hair sculpted in a darker gray. The figure keeps the person's own body shape (the product line is for women; making the body androgynous is not a goal).
- `pose_variation_prompt.txt` — the same render with a small, plausible change of pose (raise / lower / rotate the tool, tilt the head): a cheap way to grow a pose library from one photo.

**How much does the edit move the person?** `tools/compare_generated.py` runs RTMW on the original and on the edit (1500 px images) and reports per-group median shifts plus the residual after removing a global scale + shift:

| Edit | Fingertips | Wrists | Residual after align |
|---|---|---|---|
| Mocap suit | — | 12–55 px (all joints) | — |
| Gray clay v1 | 16–21 px | 6–161 px | 8–55 px |
| Gray clay v2, bald | 6–15 px | 5–33 px | 6–11 px |
| Gray clay v2, hair | 7–12 px | 9–24 px | 7–9 px |

v2 with the orange product is the cleanest edit (≈ 0.5–1 % of the image size), but no edit keeps the pose to the pixel, so the measured pose should still come from the original photo; the edit helps where the original is ambiguous (hybrid mode: body from the edit, hands from the original).

**Depth.** `tools/depth_maps.py` writes MoGe-2 depth (16-bit, near = bright, plus a colour preview and the raw metres). Relative depth of the renders is clean; the metric scale is not consistent between renders (2–4.5 m for the same framing), so do not use it as absolute distance.

**Bigger variations.** The first variation prompt asked for "small" changes and the model barely moved the pose. `pose_variation_prompt_v2.txt` asks for a clearly different pose (at least 30 degrees at the shoulder or elbow) from a menu (tool to the other side and hand, arm above the head at the crown, tool down at the hair ends, torso turned 30-45 degrees, strong head tilt). 16 generated; on review 3 were implausible (an arm crossing the chest unnaturally, a hand floating above a bald head, an odd hair lift). They were regenerated with safer poses and an explicit anatomy check appended to the prompt (each hand attached to its own arm, no arm across the chest, head tilt under ~20 degrees, no floating hands), and all 3 replacements passed. All 16 were posed on the human figure; body and arms follow the new poses, the free hand is the weakest part. Total generation cost for this round: about $1.46.

**Reference library.** 80 real photos of people using hair tools, downloaded for internal research only (`samples/library/`, git-ignored), **sorted by tool category** in `images/<tool>/` (hair dryer 28, flat iron 18, curling iron / wand 14, air styler 8, hot brush 7, round brush + dryer 5), with one contact sheet per tool and a catalog of visible hands, camera angle, framing and pose. Gaps: few air-styler / hot-brush images, few high / low camera angles.

**Study board.** All results are laid out in Figma: <https://www.figma.com/design/BIhbEhtz1sq2tjW5pzraUm/3d-puppet>.

---

## 10. Round 5: realistic human figure with a professional rig

**Why.** The wooden mannequin (chosen in round 1 only to avoid third-party assets) does not read as a human: different volumes and proportions make the overlay look wrong even when the joints match, and it has no animator controls. The use is internal, so a real body model is fine.

**Choice: MHR (Meta Momentum Human Rig, Apache-2.0)** — it was already on disk inside the SAM 3D Body weights (`assets/mhr_model.pt`):
- scan-based human mesh (18 439 vertices, UVs), 127-joint skeleton with twist, finger and face joints, linear-blend skin weights, 45 identity and 28 proportion coefficients;
- it is the body SAM 3D Body predicts, so the **body shape of the person in the photo** comes for free: `tools/build_human.py --photos ...` averages the shape of our 4 models (1.63 m, female body).

**Rig: Rigify** (bundled with Blender), generated in code by `puppet_pose/human_builder.py`:
1. the full human metarig (face removed) is moved onto the MHR joints; bone rolls are carried over from the metarig defaults (hand bones through a hand-frame change), so Rigify's IK/FK and finger conventions hold;
2. Rigify generates the rig (404 bones, 130 controls);
3. MHR skin weights are mapped onto the DEF bones (twist joints go to the nearest DEF segment).

**Pose transfer.** The pipeline poses a hidden 55-bone SMPL-X *driver* built on the human's own rest skeleton; `sync_rig()` moves the Rigify FK controls so every DEF bone follows its driver bone (max error 0.01 mm, `tests/test_human.py`). The server fits on the same skeleton (`server/methods/rest.py`, `figure` = `human` | `mannequin`, saved in the result), so the transfer stays exact.

---

## 11. Round 6: SAM 3D direct, generator choice

**SAM 3D Body straight on the photo** (`tools/sam3d_direct.py`): the regressed MHR body already fits the photo exactly, so one pass gives the person's 3D mesh (.obj), a silhouette mask and a metric depth map (e.g. 0.86-1.10 m in photo 01, near = red). Body only: hair, clothing volume and the tool are not part of the mesh.

**Nano Banana 2.1 vs GPT Image 2.5 Sunburst (high, 2K)** on the same 8 gray renders (same prompts):

| | Nano Banana 2.1 | Sunburst high |
|---|---|---|
| Fingertip shift, bald | 6-15 px | 8-161 px |
| Fingertip shift, hair | 7-12 px | 115-170 px |
| Framing | kept | re-framed in 6 of 8 |
| Moderation | none | 4 of 8 blocked by "no clothing" (passes with "fitted gray bodysuit like a store mannequin") |
| Look | clean clay mannequin | more photoreal, keeps the original model's features |
| Cost per 2K image | $0.077 | $0.122 |

**Decision: Nano Banana 2.1.** It keeps the shot and drops the original model's identity, which is what we need before prompting new people, products and hair types on top of the gray render or its depth map.

---

## 12. Round 7: Stage A - new people on top of the pose input

Goal: use the pose input to prompt different people (and later other products and hair types) while keeping the shot, the pose and the grip. Template: `server/prompts/person_from_input_prompt.txt`. Nano Banana 2.1, 2K; 4 photos x 4 inputs x 4 people = 64 images (47 in Flora, 17 in Krea with the same model after the Flora workspace ran out of credits).

Inputs:
- gray render, bald / with hair (Nano Banana edit of the photo);
- depth map of each gray render: MoGe-2, https://huggingface.co/Ruicheng/moge-2-vitl-normal (includes hair and the tool). SAM 3D Body (https://huggingface.co/facebook/sam-3d-body-dinov3) gives a body-only depth map instead.

Findings:
- every input keeps the pose, the grip and the framing, and the four women (African-American curvy, East Asian slim, Latina, blonde) read as clearly different people;
- inputs **with hair** keep the action (hair wrapped in the tool, a strand pulled into the styler) but push the original hair placement; bald inputs free the hairstyle but sometimes lose the hair-tool interaction;
- "curvy" changes the body only a little: the input silhouette dominates.

**Decision: from now on we use the inputs with hair.**

---

## 13. Round 8: library test (real photos)

One photo per tool from the reference library (#008 curling iron, #041 flat iron, #031 hair dryer, #057 air styler, #072 hot brush, #074 round brush + dryer). Step 1: gray render with hair (`gray_render_prompt_v2_hair.txt`, tool in orange). Step 2: the four people of stage A from that render. Nano Banana 2.1 through Krea (Flora workspace out of credits), 2K, 30 images.

- Works on all six tools, including two tools at once (#074); pose, grip and framing are kept and the hair-tool action carries over to every person.
- Ad text and badges of the source photo disappear.
- One gray render (#031, crop top) was blocked by the provider's moderation with "no clothing"; "replace the clothes with a smooth, fitted, seamless gray bodysuit, like a retail display mannequin" passes. Use that wording by default.
- Wide shots keep a small figure; the tool's look comes from the prompt; body type still follows the source silhouette.

Next: swap the product for one of our four tools and test hair types, then batch the library.

---

## 14. Round 9: product swap and the final pipeline

Our four products were turned into clean packshots (crop of the client photo -> Nano Banana "isolate on white"). Each of the six library cases got one packshot as a second reference image next to its gray input with hair (`server/prompts/product_swap_prompt.txt`), with one of the four people: 24 images in Krea.

- The product is reproduced faithfully (shape, colours, barrel, cable).
- Same-category swaps (curling iron reference -> our curling iron, hot brush -> our round brush) keep pose, grip and hair wrapped on the tool.
- Cross-category swaps (flat iron or two-tool references) lose the hair interaction and can move the arms.

**Pipeline adopted** (also drawn in the Figma board):
1. Approved real library, sorted by tool category; start from the category of the new product.
2. Optional: grow the library with small pose variations of approved photos (prompt v2 + anatomy check).
3. 3D gray input WITH hair: Nano Banana edit of the real photo (`gray_render_prompt_v2_hair.txt`), tool in orange, clothes as a gray bodysuit. Optional: its depth map (MoGe-2) or the SAM 3D Body mesh.
4. Inject the prompt (person, hair, wardrobe, light) and the product packshot.
5. Output: Nano Banana 2.1, 2K (Flora, Krea as fallback).

---

## 15. Round 10: hair types

Three library cases with the product of the same category (#008 -> our curling iron, #057 -> our air styler, #072 -> our round brush) x four hair types (sleek bob, 4C coily afro, box braids, 3B copper curls), same person throughout: 12 images, Nano Banana 2.1 in Krea. The prompt is the product-swap prompt with an explicit `HAIR:` line ("change the hair completely to this style, while the tool still works a section of it in the same place").

- Every hair type renders correctly; pose, grip and product stay.
- The gray input with hair fixes where the hair is and what the tool does, not the texture: the hair type is set by the prompt.
- Long hair keeps the wrap on the barrel; short or coily hair shows less wrapping (physically plausible). The brush case keeps the action with all four types.
- Small figures in the input can be re-framed bigger.

---

## 16. Round 11: SAM depth vs gray input, category batch

**SAM 3D Body depth as input (not used).** Three library cases with the SAM 3D Body depth (body only) + packshot + prompt. The map has no hair and no tool, so the model has to guess where the product goes: the tool changes hand, and pose and framing move. The main input stays the MoGe-2 depth of the gray render WITH hair, which carries body, hair and tool together. SAM 3D Body is kept in `tools/sam3d_direct.py` for reference only.

**Full pipeline on one category.** 10 of the 14 curling-iron photos (stylist and mirror shots excluded): photo -> gray render with hair -> MoGe-2 depth -> our curling iron packshot + one of the four people (`server/prompts/depth_person_product_prompt.txt`). Nano Banana 2.1 in Krea.

- 10/10 usable: our curling iron in hand with the hair wrapped on the barrel, including hand close-ups and black-and-white sources.
- Marketing text of the source photos is removed.
- Clean the reference: one output kept a dog from the source; the gray-render step should drop everything that is not the person and the tool.
- Small figures in wide shots stay small; prefer half-body references for hero shots.
- One output was blocked once by moderation and passed with a long-sleeve top.
- The real size of a new product is unknown to the model: give its dimensions in the prompt or add a photo of it in a hand.

The step-by-step build guide for ComfyUI (prompts, settings and nodes per step) is in the Figma file, in the frame next to the study board.

**Two separate workflows** (superseded in round 12: the gray render is the main input, depth is optional).
- *Workflow A - library prep, run once:* approved photo (+ optional pose variations) -> Nano Banana gray render with hair -> MoGe-2 depth map, stored in the library by tool category; packshots made once per product.
- *Workflow B - generation, one call per image:* depth map from the library (same category as the product) + packshot + prompt -> one Nano Banana 2.1 call. No 3D or depth estimation at this point.

---

## 17. Round 12: gray render vs depth map, pose details

**A/B on image 1.** Same photo, product (our curling iron), person and prompt; only image 1 changes: the gray render with hair or its MoGe-2 depth map. Three cases (#066, #001, #073).

- #066: equal.
- #001: both turn the hand close-up into a wider shot with the face.
- #073: each fails differently. From the gray render the hand is flipped (palm instead of back of the hand); from the depth map the face turns to the other side (a depth map cannot tell which way a profile looks).
- The depth map is not clearly better, so it becomes optional. The gray render is the main input (one step less).

**Pose details.** A short written description of face direction and grip ("face toward the left edge; the back of the hand faces the camera; the thumb rests on the clamp lever") fixes #073 with both inputs. Each library photo gets this description once (`server/prompts/pose_details_prompt.txt`, any vision LLM), inserted into the final prompt as `{pose_details}`.

**Suggested path.**
- *Workflow A - library prep, once per photo / per product:* approved photo -> Nano Banana gray render with hair (`gray_render_prompt_v2_hair.txt`, now also removes pets, props and text) + pose details text. Packshot once per product.
- *Workflow B - generation, one call per image:* gray render + packshot + `final_generation_prompt.txt` -> Nano Banana 2.1.
- *Optional:* pose variations to grow the library (`pose_variation_prompt_v2.txt`); MoGe-2 depth map as image 1 (`depth_person_product_prompt.txt`).

---

## 18. Round 13: final prompt on the batch failures

A closer review of the curling-iron batch showed detail failures behind the "10/10": close-up crops without a face gained an invented face and were re-framed (#001, #002), grips changed (#004, #073), and in #004 the gray render had already moved the figure.

Re-run with the final prompt (`final_generation_prompt.txt`): pose details written by a vision LLM from the original photo (prompt A2; Claude was used as the vision LLM for this test, a Gemini node in ComfyUI), a new KEEP THE CROP line and a PRODUCT SIZE line (assumed standard size, 32 mm barrel, ~35 cm, since the real size of our product is unknown). Same gray renders, packshot and people as before.

- #002: the invented face is gone; crop and grip match the photo.
- #004: gaze (up-left) and both hands on the handle match.
- #073: back of the hand toward the camera and thumb on the clamp, as in the photo.
- #001: closer crop, but part of the face still appears.

3 of 4 fixed. Remaining rules: check the gray render's framing before stage 2, and prefer references that show the face for hero shots.
