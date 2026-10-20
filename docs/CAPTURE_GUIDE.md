# Capture guide: exact camera with a ChArUco board

Use this when **we** shoot the photos. A printed ChArUco board turns the camera from an *estimate* into a *measurement*: exact focal length, lens distortion and camera position/angle. The pose pipeline then only has to solve the body.

## 0. Make the board (once)

```bat
cd server
.venv\Scripts\python calibrate.py board --out calibration\boards
```

This writes `charuco_7x5_40mm.png/.pdf/.json`: 7×5 squares of 40 mm with 30 mm ArUco markers (DICT_5X5_250), 300 × 220 mm in total.

- Print at **100% scale** (no "fit to page").
- **Measure one square with a ruler**: it must be exactly 40.0 mm. If not, regenerate with the measured size (`--square-mm 39.6 --marker-mm 29.7`) or reprint.
- Mount it **perfectly flat** on foam board, aluminium composite or glass. A curved board ruins calibration.
- For full-body shots at 3–5 m, print a bigger board (e.g. `--squares 9x6 --square-mm 80 --marker-mm 60` on A1/A0).

## 1. Calibrate the lens (once per camera + lens + zoom + focus distance)

1. Fix the camera settings you will use for the shoot: lens, **zoom position**, focus distance (manual focus), and image size/aspect. Turn off in-camera digital crop and lens-correction profiles.
2. Take **15–30 photos of the board** from different angles and distances:
   - fill different parts of the frame (center, corners, edges);
   - tilt the board up to about 45° in various directions;
   - keep it sharp: no motion blur, good light.
3. Calibrate:
   ```bat
   .venv\Scripts\python calibrate.py intrinsics D:\shoot\calib_50mm --out profiles\a7iv_50mm.json --camera "Sony A7 IV" --lens "50mm f/1.8"
   ```
   It prints the reprojection error (`rms`). **Below 0.5 px is excellent, below 1 px is acceptable.** Above that: re-shoot blurry views, check board flatness, and make sure zoom/focus did not change.

The profile JSON stores `fx, fy, cx, cy`, distortion, the 35 mm-equivalent focal length and the horizontal FOV. **Reuse it for every shoot with the same camera, lens and zoom.** If you zoom or change lenses, make a new profile.

## 2. Camera position for each setup (board in the shot)

For every camera position:

1. With the camera locked off (tripod), take a **"plate" photo with the board in the scene**:
   - **Floor** (default): lay the board flat on the floor where the talent will stand (world origin = board corner, Z up).
   - **Wall / stand**: board vertical (`--mount wall`).
2. Take the actual talent photos **without moving the camera**.
3. Solve the camera pose from the plate:
   ```bat
   .venv\Scripts\python calibrate.py pose D:\shoot\setup01\plate.jpg --profile profiles\a7iv_50mm.json --mount floor
   ```
   This writes `plate_camera_pose.json` with the camera position in meters and `world_from_cv` (a 4×4 matrix).

## 3. Use it in the pose pipeline

- **Server CLI:**
  ```bat
  run_server.bat --once D:\shoot\setup01\take_03.jpg --method auto --profile profiles\a7iv_50mm.json --camera-pose D:\shoot\setup01\plate_camera_pose.json --out take_03.json
  ```
- **Batch:**
  ```bat
  run_server.bat --batch D:\shoot\setup01 --out D:\shoot\setup01\results --profile profiles\a7iv_50mm.json --camera-pose D:\shoot\setup01\plate_camera_pose.json
  ```
- **Board in every photo:** use `--camera-pose auto` and the board is found in each photo itself (no separate plate needed).
- **Blender:** in the *Puppet* panel, box *Measured camera (ChArUco)*: set **Camera Profile** and (optionally) **Camera Pose**, keep **Use Measured Camera** on, then *Pose From Photo*. Works with both backends (Lite undistorts locally with OpenCV).

With a profile the image is undistorted and the measured focal length is used, so no estimation is needed. With a camera pose, the Blender camera gets the **measured** position and angle, and the puppet is placed in the same world (standing on the board's floor).

## Validation (synthetic ground truth)

`tests/render_charuco.py` renders the board in Blender with a known 50 mm camera (24 views + one plate at 1.8 m) and `tests/test_calibration.py` adds a known lens distortion (k1 = −0.08, k2 = 0.02), calibrates and solves the plate pose:

| Quantity | Error |
|---|---|
| Focal length | 0.18 % (2218.3 vs 2222.2 px) |
| Principal point | 1.6 px |
| Pixel ray direction (whole camera model) | 0.06° (95th pct, central 80 %), 0.13° max in the corners |
| Straightness after undistortion | 0.10 px |
| Plate camera position (1.8 m away) | 3.0 mm |
| Plate camera rotation | 0.07° |

`tests/test_world_placement.py` checks the Blender side: with a measured camera pose the camera is restored exactly (0.00 mm, 0.0000°) and, on the Pro (rig) path, every joint lands exactly where it was in the world (0.0 mm); the Lite (points) path is within 14 mm on average.

## Tips

- Shoot **RAW + JPEG** and keep the original files (EXIF intact). Do not crop photos you want to match; if you must, crop *after* processing.
- Same camera + same zoom + same focus = same profile. Changing focus distance a lot slightly changes the focal length; re-calibrate for very different distances.
- For the best **body** precision, add a second synchronized camera or an inertial mocap suit with gloves; see `docs/RESEARCH.md` §8.
