# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os

import bpy
from bpy.props import EnumProperty, StringProperty

from . import (deps, hand_controls, human_builder, keypoint_editor, openpose, pose_apply,
               puppet_builder)
from . import skeleton as sk


def _active_puppet(context):
    obj = context.object
    if obj and obj.type == "MESH" and obj.parent and obj.parent.type == "ARMATURE":
        obj = obj.parent
    if obj and obj.type == "ARMATURE" and "puppet_driver" in obj:   # human Rigify rig
        obj = bpy.data.objects.get(obj["puppet_driver"]) or obj
    if obj and obj.type == "ARMATURE":
        return obj
    for o in context.scene.objects:
        if puppet_builder.is_puppet(o):
            return o
    return None


def new_figure(context):
    """Build the figure chosen in the panel; returns the armature the pipeline poses."""
    s = context.scene.puppet_pose
    if s.figure == "HUMAN" and human_builder.available():
        return human_builder.build_human("Human")
    return puppet_builder.build_puppet("Puppet")


def figure_of(arm):
    return "human" if arm is not None and sk.REST_PROP in arm else "mannequin"


def sync_figure(arm):
    """Human figure: copy the driver pose onto the Rigify controls."""
    if human_builder.rig_of(arm) is not None:
        human_builder.sync_rig(arm)


class PUPPET_OT_add(bpy.types.Operator):
    bl_idname = "puppet_pose.add_puppet"
    bl_label = "Add Figure"
    bl_description = ("Add the rigged figure chosen above: realistic human with a Rigify rig, "
                      "or the wooden mannequin")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        arm = new_figure(context)
        arm.location = context.scene.cursor.location
        context.view_layer.update()
        sync_figure(arm)
        shown = human_builder.rig_of(arm) or arm
        for o in context.selected_objects:
            o.select_set(False)
        shown.select_set(True)
        context.view_layer.objects.active = shown
        return {"FINISHED"}


class PUPPET_OT_reset(bpy.types.Operator):
    bl_idname = "puppet_pose.reset_pose"
    bl_label = "Reset Pose"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        arm = _active_puppet(context)
        if not arm:
            self.report({"ERROR"}, "No puppet armature found")
            return {"CANCELLED"}
        for pb in arm.pose.bones:
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.location = (0, 0, 0)
        context.view_layer.update()
        sync_figure(arm)
        return {"FINISHED"}


class PUPPET_OT_hand_preset(bpy.types.Operator):
    bl_idname = "puppet_pose.hand_preset"
    bl_label = "Hand Preset"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(items=[(k, k.replace("_", " ").title(), "") for k in hand_controls.PRESETS])
    side: EnumProperty(items=[("BOTH", "Both", ""), ("LEFT", "Left", ""), ("RIGHT", "Right", "")])

    def execute(self, context):
        arm = _active_puppet(context)
        if not arm:
            self.report({"ERROR"}, "No puppet armature found")
            return {"CANCELLED"}
        hand_controls.apply_preset(arm, self.side, self.preset)
        context.view_layer.update()
        sync_figure(arm)
        return {"FINISHED"}


class PUPPET_OT_install_deps(bpy.types.Operator):
    bl_idname = "puppet_pose.install_deps"
    bl_label = "Install Lite Dependencies"
    bl_description = "pip-install MediaPipe into the add-on folder and download its models (internet needed)"

    def execute(self, context):
        try:
            if not deps.mediapipe_available():
                deps.install_packages(log=print)
            deps.ensure_models(log=print)
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, f"Install failed: {e}")
            return {"CANCELLED"}
        self.report({"INFO"}, "MediaPipe ready")
        return {"FINISHED"}


def run_backend(settings, image_path, figure=None):
    """Run the selected backend, returning the result dict."""
    from . import calib_local
    profile = bpy.path.abspath(settings.camera_profile) if settings.camera_profile else ""
    pose = bpy.path.abspath(settings.camera_pose) if settings.camera_pose else ""
    if settings.backend == "LITE":
        if not deps.mediapipe_available():
            raise RuntimeError("MediaPipe not installed: press 'Install Lite Dependencies'")
        from .backends import mediapipe_lite
        models = deps.ensure_models()
        f35, path, note = settings.focal_35mm, image_path, None
        if profile:
            prof = calib_local.load_json(profile)
            path, f35 = calib_local.undistort(image_path, prof)
            note = f"camera profile: {prof.get('camera', '')} {prof.get('lens', '')} (measured)"
        res = mediapipe_lite.run(path, models, focal_35mm=f35,
                                 default_35mm=settings.default_35mm,
                                 min_visibility=settings.min_visibility)
        if note:
            res["notes"].insert(0, note)
        if pose:
            res["world_from_cv"] = calib_local.load_json(pose)["world_from_cv"]
        return res
    from .backends import server_client
    return server_client.run(image_path, settings.host, settings.port,
                             focal_35mm=settings.focal_35mm, method=settings.pro_method,
                             profile=profile or None, camera_pose=pose or None,
                             figure=figure)


class _ApplyMixin:
    """Shared apply step (operators must not subclass registered operators)."""

    def _apply(self, context, arm, result, s):
        if context.object and context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        try:
            pose_apply.apply_result(
                context, arm, result, frame_mode=s.frame_mode,
                make_camera=s.make_camera, ground=s.ground,
                use_rotations=s.use_rotations, apply_body=s.apply_body,
                apply_hands=s.apply_hands, bg_image=s.bg_image,
                keyframe=s.keyframe, flip_facing=s.flip_facing,
                refine=s.refine_camera, hide_unseen=s.hide_unseen,
                use_world=s.use_world)
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, f"Apply failed: {e}")
            return {"CANCELLED"}
        context.view_layer.update()
        sync_figure(arm)
        s.last_notes = " | ".join(result.get("notes", []))
        arm["puppet_last_result"] = json.dumps(result)
        self.report({"INFO"}, f"Pose applied ({result.get('backend', '?')})")
        return {"FINISHED"}


class PUPPET_OT_pose_from_photo(_ApplyMixin, bpy.types.Operator):
    bl_idname = "puppet_pose.pose_from_photo"
    bl_label = "Pose From Photo"
    bl_description = "Estimate body, hands and camera from the photo and apply them to the puppet"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.puppet_pose
        path = bpy.path.abspath(s.image_path)
        if not os.path.isfile(path):
            self.report({"ERROR"}, "Choose a photo first")
            return {"CANCELLED"}
        arm = _active_puppet(context)
        if arm is None:
            arm = new_figure(context)
        try:
            if context.window:
                context.window.cursor_set("WAIT")
            result = run_backend(s, path, figure_of(arm))
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        finally:
            if context.window:
                context.window.cursor_set("DEFAULT")
        return self._apply(context, arm, result, s)


class PUPPET_OT_reapply(_ApplyMixin, bpy.types.Operator):
    bl_idname = "puppet_pose.reapply"
    bl_label = "Re-apply Last Result"
    bl_description = "Re-apply the last estimation with the current options (no model run)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        arm = _active_puppet(context)
        if not arm or "puppet_last_result" not in arm:
            self.report({"ERROR"}, "No previous result stored on the puppet")
            return {"CANCELLED"}
        return self._apply(context, arm, json.loads(arm["puppet_last_result"]),
                           context.scene.puppet_pose)


class PUPPET_OT_load_json(_ApplyMixin, bpy.types.Operator):
    bl_idname = "puppet_pose.load_json"
    bl_label = "Load Result JSON"
    bl_description = "Apply a result JSON saved by the pose server or another tool"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        with open(self.filepath, encoding="utf-8") as fh:
            result = json.load(fh)
        arm = _active_puppet(context) or new_figure(context)
        return self._apply(context, arm, result, context.scene.puppet_pose)


def _last(context):
    arm = _active_puppet(context)
    if not arm or "puppet_last_result" not in arm:
        raise RuntimeError("Run 'Pose From Photo' (Pro backend) first")
    cam = bpy.data.objects.get(arm.name + "_Cam")
    if cam is None:
        raise RuntimeError("Puppet camera not found")
    return arm, cam, json.loads(arm["puppet_last_result"])


class PUPPET_OT_edit_keypoints(bpy.types.Operator):
    bl_idname = "puppet_pose.edit_keypoints"
    bl_label = "Edit Keypoints"
    bl_description = ("Show one movable point per joint over the photo (camera view). "
                      "Drag the wrong ones (G), hide unwanted ones (H), then press Re-fit")
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            arm, cam, result = _last(context)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        n = keypoint_editor.create(context, arm, cam, result)
        context.scene.camera = cam
        for area in context.screen.areas if context.screen else []:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
        self.report({"INFO"}, f"{n} keypoints. Move them in camera view, then Re-fit")
        return {"FINISHED"}


class PUPPET_OT_refit_keypoints(_ApplyMixin, bpy.types.Operator):
    bl_idname = "puppet_pose.refit_keypoints"
    bl_label = "Re-fit from Keypoints"
    bl_description = "Send the edited keypoints to the pose server and re-fit the puppet"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from .backends import server_client
        s = context.scene.puppet_pose
        try:
            arm, cam, result = _last(context)
            edits = keypoint_editor.read(context, cam)
            if not edits:
                self.report({"WARNING"}, "No keypoint was moved or hidden")
                return {"CANCELLED"}
            new = server_client.refit(result, edits, s.host, s.port)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        r = self._apply(context, arm, new, s)
        keypoint_editor.create(context, arm, bpy.data.objects[arm.name + "_Cam"], new)
        return r


class PUPPET_OT_import_openpose(_ApplyMixin, bpy.types.Operator):
    bl_idname = "puppet_pose.import_openpose"
    bl_label = "Import OpenPose JSON"
    bl_description = ("Use 2D keypoints from an OpenPose JSON (BODY_25 / COCO-18 + hands, "
                      "e.g. from a ControlNet/ComfyUI pose editor) and re-fit")
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        from .backends import server_client
        s = context.scene.puppet_pose
        try:
            arm, cam, result = _last(context)
            img = result["image"]
            kp = openpose.load(self.filepath, img["width"], img["height"])
            new = server_client.refit(result, kp, s.host, s.port)
        except (RuntimeError, ValueError, OSError) as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return self._apply(context, arm, new, s)


class PUPPET_OT_export_openpose(bpy.types.Operator):
    bl_idname = "puppet_pose.export_openpose"
    bl_label = "Export OpenPose JSON"
    bl_description = "Save the current 2D keypoints (with your edits) as OpenPose BODY_25 + hands"

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        self.filepath = "keypoints_openpose.json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            arm, cam, result = _last(context)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        img = result["image"]
        openpose.save(bpy.path.ensure_ext(self.filepath, ".json"),
                      keypoint_editor.current(context, cam, result), img["width"], img["height"])
        return {"FINISHED"}


class PUPPET_OT_check_server(bpy.types.Operator):
    bl_idname = "puppet_pose.check_server"
    bl_label = "Check Server"

    def execute(self, context):
        from .backends import server_client
        s = context.scene.puppet_pose
        h = server_client.health(s.host, s.port)
        if h is None:
            self.report({"WARNING"}, f"No pose server at {s.host}:{s.port}")
        else:
            self.report({"INFO"}, "Server OK: " + ", ".join(h.get("methods", [])))
        return {"FINISHED"}


classes = (PUPPET_OT_add, PUPPET_OT_reset, PUPPET_OT_hand_preset,
           PUPPET_OT_install_deps, PUPPET_OT_pose_from_photo,
           PUPPET_OT_reapply, PUPPET_OT_load_json, PUPPET_OT_check_server,
           PUPPET_OT_edit_keypoints, PUPPET_OT_refit_keypoints,
           PUPPET_OT_import_openpose, PUPPET_OT_export_openpose)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
