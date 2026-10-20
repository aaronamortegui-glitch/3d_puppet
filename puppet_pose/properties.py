# SPDX-License-Identifier: GPL-3.0-or-later
import bpy
from bpy.props import (BoolProperty, EnumProperty, FloatProperty,
                       IntProperty, PointerProperty, StringProperty)

from . import hand_controls


class PUPPET_PG_hands(bpy.types.PropertyGroup):
    left_curl: FloatProperty(name="Left Close", min=0.0, max=1.0, default=0.0,
                             subtype="FACTOR", update=hand_controls.update_from_props)
    left_spread: FloatProperty(name="Left Spread", min=-1.0, max=1.0, default=0.0,
                               update=hand_controls.update_from_props)
    left_thumb: FloatProperty(name="Left Thumb", min=0.0, max=1.0, default=0.0,
                              subtype="FACTOR", update=hand_controls.update_from_props)
    right_curl: FloatProperty(name="Right Close", min=0.0, max=1.0, default=0.0,
                              subtype="FACTOR", update=hand_controls.update_from_props)
    right_spread: FloatProperty(name="Right Spread", min=-1.0, max=1.0, default=0.0,
                                update=hand_controls.update_from_props)
    right_thumb: FloatProperty(name="Right Thumb", min=0.0, max=1.0, default=0.0,
                               subtype="FACTOR", update=hand_controls.update_from_props)


class PUPPET_PG_settings(bpy.types.PropertyGroup):
    image_path: StringProperty(name="Photo", subtype="FILE_PATH")
    backend: EnumProperty(
        name="Backend",
        items=[("LITE", "Lite (MediaPipe)", "Runs inside Blender, CPU, body + hands"),
               ("PRO", "Pro (local server)", "GPU server with SMPL-X class models, "
                                             "better depth, hands and camera")],
        default="LITE")
    pro_method: EnumProperty(
        name="Method",
        items=[("auto", "Auto", "Best model available on the server"),
               ("sam3d_body", "SAM 3D Body", "Meta SAM 3D Body (MHR)"),
               ("multihmr", "Multi-HMR", "NAVER Multi-HMR (SMPL-X)"),
               ("smplerx", "SMPLer-X / SMPLest-X", "SMPL-X whole body"),
               ("mediapipe", "MediaPipe", "Same as lite, but on the server")],
        default="auto")
    host: StringProperty(name="Host", default="127.0.0.1")
    port: IntProperty(name="Port", default=8765, min=1, max=65535)
    focal_35mm: FloatProperty(
        name="Focal (35mm eq.)", default=0.0, min=0.0, max=1200.0,
        description="0 = use EXIF / model estimate; otherwise force this 35mm-equivalent focal")
    default_35mm: FloatProperty(name="Fallback Focal", default=35.0, min=8.0, max=600.0,
                                description="Used when no EXIF focal is found (lite)")
    frame_mode: EnumProperty(
        name="Orientation",
        items=[("AUTO", "Auto (no roll)", "Camera keeps a level horizon; pitch and yaw come from the body"),
               ("UPRIGHT", "Subject upright", "Puppet stands vertical; camera tilt/roll copies the photo angle"),
               ("LEVEL", "Camera level", "Camera has no roll/pitch; the lean stays in the puppet"),
               ("NONE", "Raw", "Camera at world origin looking +Y")],
        default="AUTO")
    make_camera: BoolProperty(name="Create Camera", default=True)
    refine_camera: BoolProperty(
        name="Fit Camera to Photo", default=True,
        description="After posing, move the camera so the puppet's visible joints land on the "
                    "photo's keypoints (copies framing/distance even for cropped photos)")
    bg_image: BoolProperty(name="Photo as Background", default=True)
    ground: BoolProperty(name="Feet on Ground", default=True)
    apply_body: BoolProperty(name="Body", default=True)
    apply_hands: BoolProperty(name="Hands", default=True)
    use_rotations: BoolProperty(
        name="Use Model Rotations", default=False,
        description="Pro only: apply SMPL-X joint rotations directly instead of point retargeting")
    keyframe: BoolProperty(name="Insert Keyframes", default=False)
    hide_unseen: BoolProperty(
        name="Hide Unseen Limbs", default=True,
        description="Hide (mask) limbs that are out of frame / not visible in the photo")
    flip_facing: BoolProperty(
        name="Flip Front/Back", default=False,
        description="Use when the model confused the subject's front and back "
                    "(left/right swapped, depth mirrored). Then press Re-apply")
    min_visibility: FloatProperty(name="Min Visibility", default=0.5, min=0.0, max=1.0)
    last_notes: StringProperty(name="Notes", default="")


classes = (PUPPET_PG_hands, PUPPET_PG_settings)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.puppet_pose = PointerProperty(type=PUPPET_PG_settings)
    bpy.types.Object.puppet_hands = PointerProperty(type=PUPPET_PG_hands)


def unregister():
    del bpy.types.Object.puppet_hands
    del bpy.types.Scene.puppet_pose
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
