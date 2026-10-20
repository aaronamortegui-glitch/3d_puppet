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

**Reference library.** Real photos of people using hair tools, downloaded for internal research only (`samples/library/`, git-ignored), catalogued by tool, visible hands and camera angle — an alternative source of poses to generated variations.

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
