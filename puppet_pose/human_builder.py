# SPDX-License-Identifier: GPL-3.0-or-later
"""Realistic human figure with a professional Rigify rig.

Mesh, skin weights and skeleton come from Meta's MHR body model (Apache-2.0,
the body of SAM 3D Body), baked by tools/build_human.py into assets/human.npz.

Three objects are created:
  <name>          hidden SMPL-X "driver" armature (55 bones). The pose pipeline
                  poses this one exactly like the mannequin (same code, same
                  global-rotation transfer), using the human's own rest pose.
  <name>_rig      Rigify rig generated from the full human metarig (no face):
                  IK/FK arms and legs, spine, neck/head, finger controls.
  <name>_body     the MHR mesh, skinned to the rig's DEF bones.

sync_rig() copies the driver pose onto the Rigify FK controls, so the result
stays editable with standard animator controls.
"""

import json
import os

import bpy
import numpy as np
from mathutils import Matrix, Vector

from . import puppet_builder
from . import skeleton as sk

ASSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "human.npz")
RIG_PROP = "puppet_human_rig"
SIDE = {"left": ("L", "l"), "right": ("R", "r")}
FINGERS4 = ("index", "middle", "ring", "pinky")
_PALM = {"index": "palm.01", "middle": "palm.02", "ring": "palm.03", "pinky": "palm.04"}


def available():
    return os.path.exists(ASSET)


# ---------------------------------------------------------------------------
# metarig fitting
# ---------------------------------------------------------------------------
def _metarig_targets(J, R):
    """Metarig bone -> (head, tail) in Blender space from MHR joints J and rest R."""
    v = lambda n: Vector(J[n])  # noqa: E731
    t = {
        "spine": (v("root"), v("c_spine1")),
        "spine.001": (v("c_spine1"), v("c_spine2")),
        "spine.002": (v("c_spine2"), v("c_spine3")),
        "spine.003": (v("c_spine3"), v("c_neck")),
        "spine.004": (v("c_neck"), (v("c_neck") + v("c_head")) / 2),
        "spine.005": ((v("c_neck") + v("c_head")) / 2, v("c_head")),
        "spine.006": (v("c_head"), Vector(R["head_top"])),
    }
    for side, (S, m) in SIDE.items():
        w = v(f"{m}_wrist")
        t.update({
            f"shoulder.{S}": (v(f"{m}_clavicle"), v(f"{m}_uparm")),
            f"upper_arm.{S}": (v(f"{m}_uparm"), v(f"{m}_lowarm")),
            f"forearm.{S}": (v(f"{m}_lowarm"), w),
            f"hand.{S}": (w, v(f"{m}_middle1")),
            f"thigh.{S}": (v(f"{m}_upleg"), v(f"{m}_lowleg")),
            f"shin.{S}": (v(f"{m}_lowleg"), v(f"{m}_foot")),
            f"foot.{S}": (v(f"{m}_foot"), v(f"{m}_ball")),
            f"toe.{S}": (v(f"{m}_ball"), Vector(R[f"{side}_toe"]) * Vector((1, 1, 0))
                         + Vector((0, 0, v(f"{m}_ball").z))),
            f"pelvis.{S}": (v("root"), v(f"{m}_upleg") + Vector((0, -0.08, 0.1))),
        })
        heel = Vector(R[f"{side}_heel"])
        heel.z = 0.0
        sx = 1 if side == "left" else -1
        t[f"heel.02.{S}"] = (heel - Vector((0.035 * sx, 0, 0)), heel + Vector((0.035 * sx, 0, 0)))
        for f in FINGERS4:
            k1 = v(f"{m}_{f}1")
            t[f"{_PALM[f]}.{S}"] = (w.lerp(k1, 0.2), k1)
            t[f"f_{f}.01.{S}"] = (k1, v(f"{m}_{f}2"))
            t[f"f_{f}.02.{S}"] = (v(f"{m}_{f}2"), v(f"{m}_{f}3"))
            t[f"f_{f}.03.{S}"] = (v(f"{m}_{f}3"), v(f"{m}_{f}_null"))
        t[f"thumb.01.{S}"] = (v(f"{m}_thumb1"), v(f"{m}_thumb2"))
        t[f"thumb.02.{S}"] = (v(f"{m}_thumb2"), v(f"{m}_thumb3"))
        t[f"thumb.03.{S}"] = (v(f"{m}_thumb3"), v(f"{m}_thumb_null"))
    return t


def _hand_frame(wrist, index1, pinky1):
    a = (index1 - wrist).normalized()
    b = (pinky1 - wrist)
    n = a.cross(b).normalized()
    c = n.cross(a)
    return Matrix((a, c, n)).transposed()   # columns a, c, n


def _fit_metarig(meta, J, R):
    """Move metarig bones onto the MHR joints, keeping Rigify's roll conventions."""
    targets = _metarig_targets(J, R)
    bpy.context.view_layer.objects.active = meta
    bpy.ops.object.mode_set(mode="EDIT")
    eb = meta.data.edit_bones
    # drop the face rig and bones the figure does not need
    face = eb.get("face")
    drop = set()
    if face:
        drop |= {face.name} | {c.name for c in face.children_recursive}
    drop |= {b.name for b in eb if b.name.startswith("breast.")}
    for n in drop:
        eb.remove(eb[n])
    # remember default Z axes (and the default hand frames) before moving anything
    zdef = {b.name: b.z_axis.copy() for b in eb}
    hand_def, hand_new = {}, {}
    for side, (S, m) in SIDE.items():
        hand_def[S] = _hand_frame(eb[f"hand.{S}"].head, eb[f"f_index.01.{S}"].head,
                                  eb[f"f_pinky.01.{S}"].head)
        hand_new[S] = _hand_frame(Vector(J[f"{m}_wrist"]), Vector(J[f"{m}_index1"]),
                                  Vector(J[f"{m}_pinky1"]))
    connected = {b.name: b.use_connect for b in eb}
    for b in eb:
        b.use_connect = False
    for name, (h, tl) in targets.items():
        b = eb.get(name)
        if b is None:
            continue
        b.head, b.tail = h, tl
    for name in targets:
        b = eb.get(name)
        if b is None:
            continue
        z = zdef[name]
        S = name[-1]
        if any(name.startswith(p) for p in ("f_", "thumb", "palm")):
            z = hand_new[S] @ hand_def[S].transposed() @ z
        b.align_roll(z)
    # restore the metarig's own connections (Rigify relies on them)
    for b in eb:
        if connected.get(b.name) and b.parent:
            b.use_connect = True
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------
# skin weights: MHR joint -> Rigify DEF bone
# ---------------------------------------------------------------------------
def _def_candidates(mhr):
    n = mhr
    if n in ("body_world", "root", "c_spine0"):
        return ["DEF-spine"]
    if n == "c_spine1":
        return ["DEF-spine.001"]
    if n == "c_spine2":
        return ["DEF-spine.002"]
    if n == "c_spine3":
        return ["DEF-spine.003"]
    if n.startswith("c_neck"):
        return ["DEF-spine.004", "DEF-spine.005"]
    if n.startswith("c_"):
        return ["DEF-spine.006"]
    S = "L" if n.startswith("l_") else "R"
    b = n[2:]
    if b in ("eye", "eye_null"):
        return ["DEF-spine.006"]
    if b == "clavicle":
        return [f"DEF-shoulder.{S}"]
    if b.startswith("uparm"):
        return [f"DEF-upper_arm.{S}", f"DEF-upper_arm.{S}.001"]
    if b.startswith("lowarm") or b == "wrist_twist":
        return [f"DEF-forearm.{S}", f"DEF-forearm.{S}.001"]
    if b in ("wrist", "thumb0", "pinky0"):
        return [f"DEF-hand.{S}"]
    if b.startswith("upleg"):
        return [f"DEF-thigh.{S}", f"DEF-thigh.{S}.001"]
    if b.startswith("lowleg"):
        return [f"DEF-shin.{S}", f"DEF-shin.{S}.001"]
    if b in ("foot", "talocrural", "subtalar", "transversetarsal"):
        return [f"DEF-foot.{S}"]
    if b == "ball":
        return [f"DEF-toe.{S}"]
    for f in ("thumb",) + FINGERS4:
        if b.startswith(f):
            idx = b[len(f):]
            k = 3 if idx == "_null" else int(idx)
            pre = "DEF-thumb" if f == "thumb" else f"DEF-f_{f}"
            return [f"{pre}.0{k}.{S}"]
    return ["DEF-spine"]


def _closest_segment(p, bones):
    best, bd = None, 1e9
    for b in bones:
        a, c = b.head_local, b.tail_local
        ab = c - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-12)))
        d = (a + ab * t - p).length
        if d < bd:
            best, bd = b, d
    return best


def _bind(body, rig, d):
    names = [str(n) for n in d["joint_names"]]
    J = d["joints"]
    target = []
    for i, n in enumerate(names):
        cands = [rig.data.bones[c] for c in _def_candidates(n) if c in rig.data.bones]
        if not cands:
            cands = [rig.data.bones["DEF-spine"]]
        target.append(_closest_segment(Vector(J[i]), cands).name)
    groups = {}
    acc = {}
    for v, j, w in zip(d["w_vert"], d["w_joint"], d["w"]):
        if w > 1e-4:
            key = (int(v), target[int(j)])
            acc[key] = acc.get(key, 0.0) + float(w)
    for (v, g), w in acc.items():
        if g not in groups:
            groups[g] = body.vertex_groups.new(name=g)
        groups[g].add([v], w, "REPLACE")
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = rig
    body.parent = rig


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def _mesh(name, d):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in d["verts"]], [], d["faces"].tolist())
    uvl = me.uv_layers.new(name="UVMap")
    uv, uvf = d["uv"], d["uv_faces"]
    loop_uv = uv[uvf.reshape(-1)]
    uvl.data.foreach_set("uv", loop_uv.reshape(-1))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    mat = bpy.data.materials.get("PuppetHumanSkin") or bpy.data.materials.new("PuppetHumanSkin")
    mat.diffuse_color = (0.72, 0.72, 0.74, 1.0)
    mat.roughness = 0.6
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    return ob


def build_human(name="Human"):
    """Create driver armature + Rigify rig + skinned MHR body; returns the driver."""
    import addon_utils
    addon_utils.enable("rigify", default_set=True)
    if bpy.context.object and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    d = np.load(ASSET)
    names = [str(n) for n in d["joint_names"]]
    J = {n: d["joints"][i] for i, n in enumerate(names)}
    rest_raw = json.loads(str(d["rest_json"]))
    rest = {k: Vector(v) for k, v in rest_raw.items()}

    # 1) driver (what the pose pipeline drives)
    drv = puppet_builder._create_armature(name, rest)
    drv[puppet_builder.PUPPET_TAG] = 1
    drv[sk.REST_PROP] = json.dumps(rest_raw)
    drv.data.display_type = "STICK"

    # 2) Rigify rig
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.ops.object.armature_human_metarig_add()
    meta = bpy.context.object
    meta.name = name + "_metarig"
    _fit_metarig(meta, J, rest_raw)
    meta.data.rigify_rig_basename = name + "_rig"
    bpy.context.view_layer.objects.active = meta
    meta.select_set(True)
    bpy.ops.pose.rigify_generate()
    rig = bpy.data.objects[name + "_rig"]
    meta.hide_set(True)
    meta.hide_render = True

    # 3) body
    body = _mesh(name + "_body", d)
    _bind(body, rig, d)

    drv[RIG_PROP] = rig.name
    rig["puppet_driver"] = drv.name
    drv.hide_set(True)
    _set_fk(rig)
    return drv


# ---------------------------------------------------------------------------
# driver -> Rigify FK controls
# ---------------------------------------------------------------------------
def def_to_driver():
    m = {"DEF-spine": "pelvis", "DEF-spine.001": "spine1", "DEF-spine.002": "spine2",
         "DEF-spine.003": "spine3", "DEF-spine.004": "neck", "DEF-spine.005": "neck",
         "DEF-spine.006": "head"}
    for side, (S, _) in SIDE.items():
        m.update({
            f"DEF-shoulder.{S}": f"{side}_collar",
            f"DEF-upper_arm.{S}": f"{side}_shoulder", f"DEF-upper_arm.{S}.001": f"{side}_shoulder",
            f"DEF-forearm.{S}": f"{side}_elbow", f"DEF-forearm.{S}.001": f"{side}_elbow",
            f"DEF-hand.{S}": f"{side}_wrist",
            f"DEF-thigh.{S}": f"{side}_hip", f"DEF-thigh.{S}.001": f"{side}_hip",
            f"DEF-shin.{S}": f"{side}_knee", f"DEF-shin.{S}.001": f"{side}_knee",
            f"DEF-foot.{S}": f"{side}_ankle", f"DEF-toe.{S}": f"{side}_foot",
        })
        for f in FINGERS4:
            for k in (1, 2, 3):
                m[f"DEF-f_{f}.0{k}.{S}"] = f"{side}_{f}{k}"
        for k in (1, 2, 3):
            m[f"DEF-thumb.0{k}.{S}"] = f"{side}_thumb{k}"
    return m


def _controls():
    """(control, DEF bone it carries), parents first."""
    c = [("torso", "DEF-spine"), ("hips", "DEF-spine"),
         ("spine_fk.001", "DEF-spine.001"), ("spine_fk.002", "DEF-spine.002"),
         ("chest", "DEF-spine.003"), ("spine_fk.003", "DEF-spine.003"),
         ("neck", "DEF-spine.004"), ("head", "DEF-spine.006")]
    for side, (S, _) in SIDE.items():
        c += [(f"shoulder.{S}", f"DEF-shoulder.{S}"), (f"upper_arm_fk.{S}", f"DEF-upper_arm.{S}"),
              (f"forearm_fk.{S}", f"DEF-forearm.{S}"), (f"hand_fk.{S}", f"DEF-hand.{S}"),
              (f"thigh_fk.{S}", f"DEF-thigh.{S}"), (f"shin_fk.{S}", f"DEF-shin.{S}"),
              (f"foot_fk.{S}", f"DEF-foot.{S}"), (f"toe_fk.{S}", f"DEF-toe.{S}")]
        for f in FINGERS4:
            c += [(f"f_{f}.0{k}.{S}", f"DEF-f_{f}.0{k}.{S}") for k in (1, 2, 3)]
        c += [(f"thumb.0{k}.{S}", f"DEF-thumb.0{k}.{S}") for k in (1, 2, 3)]
    return c


def _set_fk(rig):
    for pb in rig.pose.bones:
        for prop in ("IK_FK", "ik_fk_switch"):
            if prop in pb.keys():
                pb[prop] = 1.0


def rig_of(driver):
    name = driver.get(RIG_PROP) if driver else None
    return bpy.data.objects.get(name) if name else None


def sync_rig(driver, passes=3):
    """Pose the Rigify FK controls so every DEF bone follows the driver bone."""
    rig = rig_of(driver)
    if rig is None:
        return
    rig.matrix_world = driver.matrix_world.copy()
    _set_fk(rig)
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    dmap = def_to_driver()
    targets = {}
    for dn, bn in dmap.items():
        if dn not in rig.data.bones or bn not in driver.pose.bones:
            continue
        drest = driver.data.bones[bn].matrix_local
        dpose = driver.pose.bones[bn].matrix
        targets[dn] = dpose @ drest.inverted() @ rig.data.bones[dn].matrix_local
    ctrls = [(c, dn) for c, dn in _controls() if c in rig.pose.bones and dn in targets]
    for _ in range(passes):
        for c, dn in ctrls:
            cp = rig.pose.bones[c]
            dp = rig.pose.bones[dn]
            cp.matrix = targets[dn] @ dp.matrix.inverted() @ cp.matrix
            bpy.context.view_layer.update()
    return max((targets[dn].translation - rig.pose.bones[dn].matrix.translation).length
               for _, dn in ctrls) if ctrls else 0.0
