# SPDX-License-Identifier: GPL-3.0-or-later
import bpy

from . import deps


class PUPPET_PT_main(bpy.types.Panel):
    bl_label = "Puppet Pose"
    bl_idname = "PUPPET_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Puppet"

    def draw(self, context):
        layout = self.layout
        layout.operator("puppet_pose.add_puppet", icon="OUTLINER_OB_ARMATURE")
        layout.operator("puppet_pose.reset_pose", icon="LOOP_BACK")


class PUPPET_PT_photo(bpy.types.Panel):
    bl_label = "Pose From Photo"
    bl_parent_id = "PUPPET_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Puppet"

    def draw(self, context):
        s = context.scene.puppet_pose
        layout = self.layout
        layout.prop(s, "image_path")
        layout.prop(s, "backend", expand=True)
        box = layout.box()
        if s.backend == "LITE":
            if not deps.mediapipe_available() or not deps.models_present():
                box.label(text="MediaPipe not installed", icon="ERROR")
                box.operator("puppet_pose.install_deps", icon="IMPORT")
            else:
                box.label(text="MediaPipe ready", icon="CHECKMARK")
            box.prop(s, "default_35mm")
            box.prop(s, "min_visibility")
        else:
            row = box.row(align=True)
            row.prop(s, "host")
            row.prop(s, "port")
            box.operator("puppet_pose.check_server", icon="URL")
            box.prop(s, "pro_method")
            box.prop(s, "use_rotations")
        cbox = layout.box()
        cbox.label(text="Measured camera (ChArUco)", icon="CAMERA_DATA")
        cbox.prop(s, "camera_profile")
        cbox.prop(s, "camera_pose")
        cbox.prop(s, "use_world")
        layout.prop(s, "focal_35mm")
        layout.prop(s, "frame_mode")
        col = layout.column(align=True)
        row = col.row(align=True)
        row.prop(s, "apply_body", toggle=True)
        row.prop(s, "apply_hands", toggle=True)
        row = col.row(align=True)
        row.prop(s, "make_camera", toggle=True)
        row.prop(s, "bg_image", toggle=True)
        row.prop(s, "refine_camera", toggle=True)
        row = col.row(align=True)
        row.prop(s, "ground", toggle=True)
        row.prop(s, "keyframe", toggle=True)
        col.prop(s, "flip_facing", toggle=True, icon="ARROW_LEFTRIGHT")
        col.prop(s, "hide_unseen", toggle=True, icon="HIDE_ON")
        layout.operator("puppet_pose.pose_from_photo", icon="ARMATURE_DATA")
        row = layout.row(align=True)
        row.operator("puppet_pose.reapply", icon="FILE_REFRESH")
        row.operator("puppet_pose.load_json", icon="FILE")
        box = layout.box()
        box.label(text="Correct keypoints (Pro server)", icon="EMPTY_DATA")
        row = box.row(align=True)
        row.operator("puppet_pose.edit_keypoints", icon="RESTRICT_SELECT_OFF")
        row.operator("puppet_pose.refit_keypoints", icon="FILE_REFRESH", text="Re-fit")
        row = box.row(align=True)
        row.operator("puppet_pose.import_openpose", icon="IMPORT", text="OpenPose In")
        row.operator("puppet_pose.export_openpose", icon="EXPORT", text="OpenPose Out")
        if s.last_notes:
            for note in s.last_notes.split(" | "):
                layout.label(text=note, icon="INFO")


class PUPPET_PT_hands(bpy.types.Panel):
    bl_label = "Hands"
    bl_parent_id = "PUPPET_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Puppet"

    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "ARMATURE"

    def draw(self, context):
        layout = self.layout
        h = context.object.puppet_hands
        for side in ("left", "right"):
            col = layout.column(align=True)
            col.label(text=side.title() + " hand")
            col.prop(h, f"{side}_curl", slider=True)
            col.prop(h, f"{side}_thumb", slider=True)
            col.prop(h, f"{side}_spread", slider=True)
        layout.label(text="Presets")
        grid = layout.grid_flow(columns=4, align=True)
        for p in ("OPEN", "RELAXED", "FIST", "POINT", "PEACE", "THUMBS_UP", "GRIP", "PINCH"):
            op = grid.operator("puppet_pose.hand_preset", text=p.replace("_", " ").title())
            op.preset = p
            op.side = "BOTH"


classes = (PUPPET_PT_main, PUPPET_PT_photo, PUPPET_PT_hands)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
