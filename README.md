# 3D Puppet — Pose and camera from a single photo (Blender add-on)

A **Blender 4.2+ / 5.0** add-on with a **fully rigged 3D mannequin**: wrists and 15 finger bones per hand, so hands can open and close. From **a single photo** it copies:

- the **pose** of the body and hands;
- the **camera**: angle, distance and focal length, with the photo as background.

The full research (rigged puppets, pose models, camera, licenses) is in **[docs/RESEARCH.md](docs/RESEARCH.md)**.

## What's included

- **Procedural puppet** with an SMPL-X skeleton (55 joints) and a wooden-mannequin look. It is 100% code, with no third-party assets.
- **Hand controls**: close, thumb and spread sliders per hand. Presets: *Open, Relaxed, Fist, Point, Peace, Thumbs up, Grip, Pinch*.
- **Pose From Photo** with two backends:
  - **Lite**: MediaPipe inside Blender. Runs on CPU and installs with one click.
  - **Pro**: local GPU server with SAM 3D Body (Meta), NLF and MediaPipe, plus RTMW 2D keypoints, a direct rig fit, MoGe-2 (focal) and GeoCalib (gravity).
- **Camera**: a camera whose focal length and position reproduce the photo, with the photo as background. **AUTO** mode keeps the horizon level unless real gravity is known.
- **Keypoint editor + OpenPose**: correct any joint by hand and re-fit.

## Installation

1. Build the add-on. On Windows you can also zip the `puppet_pose/` folder by hand.
   ```bash
   blender --command extension build --source-dir puppet_pose --output-dir dist
   ```
2. In Blender go to *Edit → Preferences → Get Extensions → ⌄ → Install from Disk…* and pick `dist/puppet_pose-0.1.0.zip`.
3. Open the panel in *3D Viewport → Sidebar (N) → **Puppet** tab*.

### Lite backend (MediaPipe)
In the panel, choose **Lite** and press **Install Lite Dependencies**. This installs MediaPipe into the add-on's user folder and downloads its models (about 30 MB). Internet is needed once.

### Pro backend (local GPU server)
```bat
cd server
install_server.bat         :: venv + PyTorch CUDA 12.8 + MediaPipe + MoGe-2 + GeoCalib + RTMW
install_sam3d.bat          :: optional: SAM 3D Body (request access on HF + "hf auth login")
run_server.bat             :: http://127.0.0.1:8765
```
In Blender choose **Pro**, press *Check Server*, then *Pose From Photo*. The server also works from the command line:
```bat
run_server.bat --once photo.jpg --method auto --out result.json
```
Apply that JSON with **Load Result JSON**.

## Runs on its own (no Claude, no cloud)

Everything runs **locally**: the add-on inside Blender and the server on your GPU. Internet is only needed once, to download the models.

- **From Blender:** *Puppet* panel → *Pose From Photo*.
- **Batch:** process a whole folder of photos:
  ```bat
  samples\run_samples.bat                       :: samples\photos with the best available method
  samples\run_samples.bat D:\my_photos nlf      :: another folder, fixed method (auto | nlf | mediapipe | sam3d_body)
  ```
  For each photo it writes to `samples/results/`:
  - `<photo>_<method>.json`: pose and camera.
  - `<photo>_<method>.blend`: the posed puppet, with the camera copying angle, distance and focal, and the photo as background.
  - `<photo>_<method>_overlay.png`: the puppet over the photo, for review.

## Matching the photo's camera

The camera is rebuilt in three steps:

1. **Focal length:** your manual value, else EXIF, else the MoGe-2 estimate (`server/lens_report.py` compares estimators).
2. **Angle:** from the gravity direction estimated by GeoCalib (real pitch and roll); if unavailable, from the body posture with a level horizon.
3. **Distance and framing:** the Pro backend fits the rig itself to the 2D keypoints, so the camera is placed from the exact pelvis position. The Lite backend uses *Fit Camera to Photo*, which moves the camera until the puppet's visible joints match the photo. Both work with cropped (half-body) photos.

### Exact camera from our own shoots (ChArUco)

For photos we shoot ourselves, a printed ChArUco board turns the camera into a measurement (focal, distortion, position): see **[docs/CAPTURE_GUIDE.md](docs/CAPTURE_GUIDE.md)** and `server/calibrate.py`. Validated on synthetic renders: focal within 0.2 %, camera position within 3 mm at 1.8 m.

## Correcting keypoints by hand (and OpenPose)

If a wrist, elbow or finger is wrong:

1. In the *Puppet* panel, press **Edit Keypoints**. One point (empty) per joint appears over the photo in camera view.
2. Move the wrong points (`G`) into place. Hide unusable ones with `H`.
3. Press **Re-fit**. The server re-fits the whole rig to your points in a few seconds.

**OpenPose In / Out** imports and exports the points as OpenPose JSON (BODY_25 or COCO-18, plus 21 points per hand). You can correct them in any OpenPose editor (ComfyUI/ControlNet, etc.) and bring them back.

## Usage

1. **Add Puppet**, or let *Pose From Photo* create it.
2. Choose the photo and the backend. Optionally force the focal length (35 mm equivalent; 0 = automatic).
3. **Pose From Photo**. The body and fingers are posed, `Puppet_Cam` becomes the active camera and the photo becomes its background. Look through the camera with `Numpad 0`.
4. Adjust by hand in Pose Mode, with the hand sliders, or with **Re-apply Last Result** after changing options (orientation, body or hands only, keyframes, hide unseen limbs).

## Layout

```
puppet_pose/            add-on / extension (GPL-3.0-or-later)
  skeleton.py           SMPL-X skeleton, rest pose and landmarks
  puppet_builder.py     armature + segmented mannequin
  hand_controls.py      curl / spread / presets
  retarget.py           named 3D points -> bone rotations (swing + twist)
  camera_utils.py       OpenCV <-> Blender, focal, camera + background
  pose_apply.py         applies a result (pose + camera + ground)
  keypoint_editor.py    movable keypoints over the photo
  openpose.py           OpenPose JSON import/export
  backends/             mediapipe_lite (in Blender), server_client (HTTP)
server/                 Pro server (own venv, PyTorch)
  pose_server.py        /health, /estimate, /refit, --once, --batch, --profile, --camera-pose
  calibrate.py          ChArUco board / lens calibration / camera pose
  lens_report.py        compares focal-length estimators
  methods/              sam3d_method, nlf_method, mediapipe_method, keypoints2d (RTMW),
                        fit (points), fit_rig (rig), hands, focal (MoGe-2), gravity (GeoCalib), detect
tools/                  blender_batch.py (scenes + overlays), measure_overlay.py
tests/                  tests that run in Blender background mode
docs/RESEARCH.md        full research
```

## Tests
```bash
blender -b --factory-startup --python tests/test_roundtrip.py
blender -b --factory-startup --python tests/test_lite_render.py -- <site-packages-dir-with-mediapipe>
blender -b --factory-startup --python tests/test_keypoint_editor.py -- <result.json>   # needs the server
blender -b --factory-startup --python tests/test_world_placement.py
blender -b --factory-startup --python tests/render_charuco.py -- <board.png> <render_dir>
python tests/test_calibration.py <render_dir> <board.json>                              # server venv
```

## Licenses
The add-on code is GPL-3.0-or-later. Models have their own licenses; **several are research / non-commercial only**:

| Model | License |
|---|---|
| MediaPipe | Apache-2.0 |
| RTMW (rtmlib) | Apache-2.0 |
| SAM 3D Body | SAM License, gated weights |
| NLF | non-commercial weights |
| SMPL-X | non-commercial |
| MoGe-2 | MIT |
| GeoCalib | Apache-2.0 code, CC-BY-4.0 weights |

Details in [docs/RESEARCH.md](docs/RESEARCH.md).
