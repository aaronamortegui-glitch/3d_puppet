# SPDX-License-Identifier: GPL-3.0-or-later
"""Procedural wooden-mannequin puppet.

Builds an armature with the SMPL-X joint layout (incl. 3 bones per
finger) and a segmented mesh rigidly bound to it (one vertex group per
bone, weight 1.0), like an artist's wooden mannequin.  Everything is
generated in code, so the add-on ships without third-party assets.
"""

import bmesh
import bpy
from mathutils import Matrix, Vector

from . import skeleton as sk

PUPPET_TAG = "puppet_pose_rig"

# (bone, radius_x, radius_z, overlap) for limb segments; ellipsoid along bone
_SEGMENTS = {
    "spine1": (0.125, 0.095, 0.03),
    "spine2": (0.145, 0.105, 0.03),
    "neck": (0.048, 0.048, 0.03),
    "collar": (0.035, 0.035, 0.0),
    "shoulder": (0.046, 0.046, 0.0),
    "elbow": (0.038, 0.036, 0.0),
    "hip": (0.074, 0.074, 0.0),
    "knee": (0.052, 0.052, 0.0),
    "foot": (0.03, 0.018, 0.0),
}
_FINGER_RADIUS = {"thumb": 0.0105, "index": 0.009, "middle": 0.0092,
                  "ring": 0.0088, "pinky": 0.0078}
_JOINT_BALLS = {  # joint -> radius ; the sphere follows the bone at that joint
    "shoulder": 0.05, "elbow": 0.042, "wrist": 0.033, "hip": 0.078,
    "knee": 0.056, "ankle": 0.042,
}


def _aligned_matrix(center, direction, sx, sy, sz):
    """Matrix placing a unit sphere as an ellipsoid whose local Y is `direction`."""
    rot = direction.to_track_quat("Y", "Z").to_matrix().to_4x4()
    scale = Matrix.Diagonal((sx, sy, sz, 1.0))
    return Matrix.Translation(center) @ rot @ scale


class _MeshBuilder:
    def __init__(self, bone_names):
        self.bm = bmesh.new()
        self.deform = self.bm.verts.layers.deform.verify()
        self.group_index = {n: i for i, n in enumerate(bone_names)}

    def ellipsoid(self, group, matrix, segments=16, rings=10):
        res = bmesh.ops.create_uvsphere(
            self.bm, u_segments=segments, v_segments=rings, radius=1.0,
            matrix=matrix)
        gi = self.group_index[group]
        for v in res["verts"]:
            v[self.deform][gi] = 1.0

    def segment(self, bone, rx, rz, overlap=0.0, segments=16):
        head, tail = sk.REST[bone], sk.bone_tail(bone)
        d = tail - head
        length = d.length
        center = (head + tail) * 0.5
        self.ellipsoid(bone, _aligned_matrix(center, d.normalized(), rx,
                                             length * 0.5 + overlap, rz),
                       segments=segments)

    def ball(self, group, center, r, segments=12):
        self.ellipsoid(group, Matrix.Translation(center) @ Matrix.Scale(r, 4),
                       segments=segments, rings=8)

    def finish(self, name):
        me = bpy.data.meshes.new(name)
        self.bm.normal_update()
        self.bm.to_mesh(me)
        self.bm.free()
        for p in me.polygons:
            p.use_smooth = True
        return me


def _create_armature(name):
    arm_data = bpy.data.armatures.new(name)
    arm_data.display_type = "OCTAHEDRAL"
    arm_obj = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(arm_obj)
    arm_obj.show_in_front = True

    prev_active = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    ebones = arm_data.edit_bones
    for joint in sk.SMPLX_JOINTS:
        eb = ebones.new(joint)
        eb.head = sk.REST[joint]
        eb.tail = sk.bone_tail(joint)
        # Roll: finger bones get local Z pointing to the palm side so that a
        # positive local-X rotation curls the finger (see hand_controls.py).
        if "_thumb" in joint:  # thumb flexes across the palm
            eb.align_roll(Vector((0.0, 0.7, -0.7)))
        elif any(f"_{f}" in joint for f in sk.FINGERS):
            eb.align_roll(Vector((0.0, 0.0, -1.0)))
        elif "wrist" in joint or "elbow" in joint or "shoulder" in joint or "collar" in joint:
            eb.align_roll(Vector((0.0, -1.0, 0.0)))
        else:
            eb.align_roll(Vector((0.0, -1.0, 0.0)) if abs(eb.vector.z) > 0.5
                          else Vector((0.0, 0.0, 1.0)))
    for joint in sk.SMPLX_JOINTS:
        parent = sk.PARENT[joint]
        if parent:
            eb = ebones[joint]
            eb.parent = ebones[parent]
            eb.use_connect = (eb.head - ebones[parent].tail).length < 1e-4
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = prev_active

    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return arm_obj


def _create_mesh(name, arm_obj):
    mb = _MeshBuilder(sk.SMPLX_JOINTS)
    R = sk.REST

    # torso / head blocks
    mb.ellipsoid("pelvis", _aligned_matrix(Vector((0, 0.0, 0.905)),
                                           Vector((0, 0, 1)), 0.165, 0.10, 0.115))
    mb.segment("spine1", *_SEGMENTS["spine1"])
    mb.segment("spine2", *_SEGMENTS["spine2"])
    mb.ellipsoid("spine3", _aligned_matrix(Vector((0, 0.0, 1.33)),
                                           Vector((0, 0, 1)), 0.175, 0.13, 0.115))
    mb.segment("neck", *_SEGMENTS["neck"])
    mb.ellipsoid("head", _aligned_matrix(Vector((0, -0.012, 1.625)),
                                         Vector((0, 0, 1)), 0.085, 0.118, 0.10),
                 segments=24, rings=16)
    # nose hint so the facing direction is readable
    mb.ellipsoid("head", _aligned_matrix(R["nose"] + Vector((0, 0.012, 0)),
                                         Vector((0, -1, 0)), 0.012, 0.018, 0.012))

    for s in sk.SIDES:
        mb.segment(f"{s}_collar", *_SEGMENTS["collar"])
        mb.segment(f"{s}_shoulder", *_SEGMENTS["shoulder"])
        mb.segment(f"{s}_elbow", *_SEGMENTS["elbow"])
        mb.segment(f"{s}_hip", *_SEGMENTS["hip"])
        mb.segment(f"{s}_knee", *_SEGMENTS["knee"])
        for j, r in _JOINT_BALLS.items():
            mb.ball(f"{s}_{j}", R[f"{s}_{j}"], r)
        # foot block from heel to ball
        heel, ball = R[f"{s}_heel"], R[f"{s}_foot"]
        c = (heel + ball) * 0.5 + Vector((0, 0, 0.015))
        mb.ellipsoid(f"{s}_ankle", _aligned_matrix(c, (ball - heel).normalized(),
                                                   0.045, (ball - heel).length * 0.62, 0.035))
        mb.segment(f"{s}_foot", *_SEGMENTS["foot"])
        # palm
        w, m1 = R[f"{s}_wrist"], R[f"{s}_middle1"]
        palm_dir = (m1 - w).normalized()
        mb.ellipsoid(f"{s}_wrist", Matrix.Translation((w + m1) * 0.5 + Vector((0, 0, 0.002)))
                     @ palm_dir.to_track_quat("Y", "Z").to_matrix().to_4x4()
                     @ Matrix.Diagonal((0.047, (m1 - w).length * 0.55, 0.016, 1.0)))
        # fingers: a segment + a knuckle ball per phalanx
        for f in sk.FINGERS:
            r = _FINGER_RADIUS[f]
            for b in sk.finger_bones(s, f):
                mb.segment(b, r, r * 0.85, overlap=0.002, segments=10)
                mb.ball(b, R[b], r * 1.05, segments=8)

    me = mb.finish(name + "_mesh")
    obj = bpy.data.objects.new(name + "_mesh", me)
    bpy.context.collection.objects.link(obj)
    for joint in sk.SMPLX_JOINTS:
        obj.vertex_groups.new(name=joint)
    obj.parent = arm_obj
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm_obj
    obj.data.materials.append(_wood_material())
    return obj


def _wood_material():
    mat = bpy.data.materials.get("PuppetWood")
    if mat:
        return mat
    mat = bpy.data.materials.new("PuppetWood")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.80, 0.58, 0.36, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.45
    mat.diffuse_color = (0.80, 0.58, 0.36, 1.0)
    return mat


def build_puppet(name="Puppet"):
    """Create the puppet; returns the armature object."""
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    arm = _create_armature(name)
    arm[PUPPET_TAG] = 1
    _create_mesh(name, arm)
    return arm


def is_puppet(obj):
    return obj is not None and obj.type == "ARMATURE" and PUPPET_TAG in obj
