# SPDX-License-Identifier: GPL-3.0-or-later
import json
import os

import bpy
from bpy.props import EnumProperty, StringProperty

from . import deps, hand_controls, pose_apply, puppet_builder


def _active_puppet(context):
    obj = context.object
    if obj and obj.type == "MESH" and obj.parent and obj.parent.type == "ARMATURE":
        obj = obj.parent
    if obj and obj.type == "ARMATURE":
        return obj
    for o in context.scene.objects:
        if puppet_builder.is_puppet(o):
            return o
    return None


class PUPPET_OT_add(bpy.types.Operator):
    bl_idname = "puppet_pose.add_puppet"
    bl_label = "Add Puppet"
    bl_description = "Add a rigged mannequin (SMPL-X skeleton, full fingers)"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        arm = puppet_builder.build_puppet("Puppet")
        arm.location = context.scene.cursor.location
        for o in context.selected_objects:
            o.select_set(False)
        arm.select_set(True)
        context.view_layer.objects.active = arm
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


def run_backend(settings, image_path):
    """Run the selected backend, returning the result dict."""
    if settings.backend == "LITE":
        if not deps.mediapipe_available():
            raise RuntimeError("MediaPipe not installed: press 'Install Lite Dependencies'")
        from .backends import mediapipe_lite
        models = deps.ensure_models()
        return mediapipe_lite.run(image_path, models, focal_35mm=settings.focal_35mm,
                                  default_35mm=settings.default_35mm,
                                  min_visibility=settings.min_visibility)
    from .backends import server_client
    return server_client.run(image_path, settings.host, settings.port,
                             focal_35mm=settings.focal_35mm, method=settings.pro_method)


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
                keyframe=s.keyframe, flip_facing=s.flip_facing)
        except Exception as e:  # noqa: BLE001
            self.report({"ERROR"}, f"Apply failed: {e}")
            return {"CANCELLED"}
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
            arm = puppet_builder.build_puppet("Puppet")
        try:
            if context.window:
                context.window.cursor_set("WAIT")
            result = run_backend(s, path)
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
        arm = _active_puppet(context) or puppet_builder.build_puppet("Puppet")
        return self._apply(context, arm, result, context.scene.puppet_pose)


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
           PUPPET_OT_reapply, PUPPET_OT_load_json, PUPPET_OT_check_server)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
