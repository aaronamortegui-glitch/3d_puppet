# SPDX-License-Identifier: GPL-3.0-or-later
"""Retarget named 3D points onto the puppet armature.

Any backend (MediaPipe, SMPL-X based models, ...) delivers named 3D
points.  For each bone we compare a *rest* vector and a *target* vector
built from the same point names, so the rest pose of the puppet and the
estimator never need to agree on bone axes.

Each bone gets a global delta rotation G (armature space, relative to
rest).  With two vectors (primary + secondary) G is fully determined
(swing + twist); with one vector we use the minimal swing applied on
top of the parent's rotation (twist inherited).
"""

from mathutils import Matrix, Quaternion, Vector

from . import skeleton as sk

EPS = 1e-6


# ---------------------------------------------------------------------------
# derived points
# ---------------------------------------------------------------------------
def _mid(p, a, b):
    if a in p and b in p:
        return (p[a] + p[b]) * 0.5
    return None


def derive_points(points):
    """Add mid points used by the specs.  Works on rest and target dicts."""
    out = dict(points)
    for name, (a, b) in {
        "hip_mid": ("left_hip", "right_hip"),
        "shoulder_mid": ("left_shoulder", "right_shoulder"),
        "ear_mid": ("left_ear", "right_ear"),
    }.items():
        if name not in out:
            m = _mid(out, a, b)
            if m is not None:
                out[name] = m
    return out


REST_POINTS = derive_points(sk.REST)


# ---------------------------------------------------------------------------
# bone specs
# ---------------------------------------------------------------------------
class Spec:
    """a: candidate point pairs for the primary vector.
    b: candidate point pairs for the secondary (twist) vector.
    b_rest: constant rest vector used instead of REST points for b.
    b_first: use b as primary axis of the frame (a only orients the twist).
    """

    def __init__(self, a, b=None, b_rest=None, b_first=False, min_angle=0.17):
        self.a = a
        self.b = b or []
        self.b_rest = b_rest
        self.b_first = b_first
        self.min_angle = min_angle


def _build_specs():
    S = {}
    S["pelvis"] = Spec([("right_hip", "left_hip")],
                       [("pelvis", "spine3"), ("hip_mid", "shoulder_mid")])
    S["spine1"] = Spec([("spine1", "spine3"), ("hip_mid", "shoulder_mid")],
                       [("right_hip", "left_hip")])
    S["spine3"] = Spec([("spine3", "neck"), ("hip_mid", "shoulder_mid")],
                       [("right_shoulder", "left_shoulder")])
    # spine2 is blended between spine1 and spine3 (see solve())
    S["neck"] = Spec([("neck", "head"), ("shoulder_mid", "ear_mid")])
    S["head"] = Spec([("right_ear", "left_ear")], [("ear_mid", "nose")])
    for s in sk.SIDES:
        fwd = Vector((0.0, -1.0, 0.0))
        back = Vector((0.0, 1.0, 0.0))
        S[f"{s}_collar"] = Spec([(f"{s}_collar", f"{s}_shoulder"),
                                 ("shoulder_mid", f"{s}_shoulder")])
        S[f"{s}_shoulder"] = Spec([(f"{s}_shoulder", f"{s}_elbow")],
                                  [(f"{s}_elbow", f"{s}_wrist")], b_rest=fwd)
        S[f"{s}_elbow"] = Spec([(f"{s}_elbow", f"{s}_wrist")],
                               [(f"{s}_pinky1", f"{s}_index1")])
        S[f"{s}_wrist"] = Spec([(f"{s}_wrist", f"{s}_middle1")],
                               [(f"{s}_pinky1", f"{s}_index1")])
        S[f"{s}_hip"] = Spec([(f"{s}_hip", f"{s}_knee")],
                             [(f"{s}_knee", f"{s}_ankle")], b_rest=back)
        S[f"{s}_knee"] = Spec([(f"{s}_knee", f"{s}_ankle")],
                              [(f"{s}_heel", f"{s}_toe")])
        S[f"{s}_ankle"] = Spec([(f"{s}_heel", f"{s}_toe"),
                                (f"{s}_ankle", f"{s}_foot")])
        S[f"{s}_foot"] = Spec([(f"{s}_foot", f"{s}_toe")])
        for f in sk.FINGERS:
            b1, b2, b3 = sk.finger_bones(s, f)
            S[b1] = Spec([(b1, b2)])
            S[b2] = Spec([(b2, b3)])
            S[b3] = Spec([(b3, f"{s}_{f}_tip")])
    return S


SPECS = _build_specs()


# ---------------------------------------------------------------------------
# math helpers
# ---------------------------------------------------------------------------
def frame(a, b):
    """Orthonormal frame (columns) with first axis a, second axis ~b."""
    x = a.normalized()
    y = b - x * b.dot(x)
    if y.length < EPS:
        return None
    y.normalize()
    z = x.cross(y)
    m = Matrix((x, y, z))  # rows
    m.transpose()          # -> columns
    return m


def align(rest_a, rest_b, tgt_a, tgt_b):
    fr, ft = frame(rest_a, rest_b), frame(tgt_a, tgt_b)
    if fr is None or ft is None:
        return None
    return ft @ fr.transposed()


def swing(u, v):
    if u.length < EPS or v.length < EPS:
        return Matrix.Identity(3)
    return u.rotation_difference(v).to_matrix()


def _pick(pairs, pts):
    for p, q in pairs:
        if p in pts and q in pts and p in REST_POINTS and q in REST_POINTS:
            return p, q
    return None


def _vec(pts, pair):
    return pts[pair[1]] - pts[pair[0]]


def _global_for(bone, pts, g_parent):
    spec = SPECS.get(bone)
    if spec is None:
        return g_parent
    pa = _pick(spec.a, pts)
    if pa is None:
        return g_parent
    rest_a, tgt_a = _vec(REST_POINTS, pa), _vec(pts, pa)
    if tgt_a.length < EPS:
        return g_parent

    pb = _pick(spec.b, pts) if spec.b else None
    if pb is not None:
        tgt_b = _vec(pts, pb)
        rest_b = spec.b_rest if spec.b_rest is not None else _vec(REST_POINTS, pb)
        ang = tgt_a.angle(tgt_b, 0.0) if tgt_b.length > EPS else 0.0
        if min(ang, 3.14159 - ang) > spec.min_angle:
            g = (align(rest_b, rest_a, tgt_b, tgt_a) if spec.b_first
                 else align(rest_a, rest_b, tgt_a, tgt_b))
            if g is not None:
                return g
    return swing(g_parent @ rest_a, tgt_a) @ g_parent


def solve(points):
    """Return {bone: G} global delta rotations (3x3, armature space)."""
    pts = derive_points(points)
    G = {}
    for bone in sk.SMPLX_JOINTS:  # SMPL-X order is parent-first
        parent = sk.PARENT[bone]
        gp = G[parent] if parent else Matrix.Identity(3)
        if bone == "spine2":
            g1 = G.get("spine1", gp)
            g3 = _global_for("spine3", pts, g1)
            G[bone] = g1.to_quaternion().slerp(g3.to_quaternion(), 0.5).to_matrix()
        else:
            G[bone] = _global_for(bone, pts, gp)
    return G


def apply_globals(arm_obj, G, bones=None):
    """Convert global deltas into pose-bone local quaternions."""
    data_bones = arm_obj.data.bones
    for pb in arm_obj.pose.bones:
        name = pb.name
        if name not in G or (bones is not None and name not in bones):
            continue
        r_rest = data_bones[name].matrix_local.to_3x3()
        parent = sk.PARENT.get(name)
        gp = G.get(parent, Matrix.Identity(3)) if parent else Matrix.Identity(3)
        basis = r_rest.inverted() @ gp.inverted() @ G[name] @ r_rest
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = basis.to_quaternion()


def apply_smplx_rotations(arm_obj, rotations, coord=None):
    """Apply SMPL-X local axis-angle rotations directly.

    rotations: {joint: (rx, ry, rz)} in SMPL-X convention (parent frame,
    y-up).  `coord` converts SMPL-X world axes into armature axes
    (default: SMPL y-up/z-front -> Blender z-up/-y-front).
    """
    if coord is None:
        coord = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))
    ci = coord.inverted()
    G = {}
    for bone in sk.SMPLX_JOINTS:
        parent = sk.PARENT[bone]
        gp = G[parent] if parent else Matrix.Identity(3)
        aa = rotations.get(bone)
        if aa is None:
            local = Matrix.Identity(3)
        else:
            v = Vector(aa)
            local = Quaternion(v.normalized(), v.length).to_matrix() if v.length > EPS \
                else Matrix.Identity(3)
        G[bone] = gp @ (coord @ local @ ci)
    apply_globals(arm_obj, G)
    return G
