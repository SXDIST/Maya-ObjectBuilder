"""Pose the skeleton to expose bad skin weights, then put it straight back.

Broken weights are invisible in bind pose — that is the whole reason a stray vertex survives
until the model is in game. Bending the rig makes them obvious, and what to look for is not
"does it deform nicely" but *spikes*: a vertex that travels somewhere completely different
from the vertices around it.

Every joint is restored afterwards. Exporting from a posed skeleton would bake the pose into
the .p3d, because a skinned mesh reports its deformed points — a quiet, expensive mistake.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

# Joints bent by the default test, as (name fragment, rotation axis, degrees). Fragments are
# matched against the leaf joint name, so both "LeftLeg" and "ns:Rig:LeftLeg" are found.
DEFAULT_POSE = (
    ("LeftLeg", "rotateX", 70.0),
    ("RightLeg", "rotateX", 70.0),
    ("LeftForeArm", "rotateY", 70.0),
    ("RightForeArm", "rotateY", -70.0),
    ("LeftArm", "rotateZ", 45.0),
    ("RightArm", "rotateZ", -45.0),
    ("LeftUpLeg", "rotateX", -45.0),
    ("RightUpLeg", "rotateX", -45.0),
)

# A vertex is a spike when it travels this much further than the average of its neighbours.
DEFAULT_SPIKE_TOLERANCE = 0.05


def _find_joint(fragment):
    for joint in cmds.ls(type="joint", long=True) or []:
        if joint.rsplit("|", 1)[-1].split(":")[-1] == fragment:
            return joint
    return None


def _apply_pose(pose):
    """Set the test rotations, returning what to restore afterwards."""
    restore = []
    for fragment, attribute, degrees in pose:
        joint = _find_joint(fragment)
        if joint is None:
            continue
        plug = joint + "." + attribute
        try:
            if cmds.getAttr(plug, lock=True) or cmds.connectionInfo(plug, isDestination=True):
                continue  # locked or driven — leave it alone
            original = cmds.getAttr(plug)
            cmds.setAttr(plug, original + degrees)
            restore.append((plug, original))
        except Exception:  # noqa: BLE001 - missing attribute on an odd rig
            continue
    return restore


def _restore(restore):
    for plug, original in reversed(restore):
        try:
            cmds.setAttr(plug, original)
        except Exception:  # noqa: BLE001 - never leave the rig posed because of a late error
            pass


def find_spikes(mesh_path, pose=DEFAULT_POSE, tolerance=DEFAULT_SPIKE_TOLERANCE):
    """Vertices that move unlike their neighbours when the rig is posed.

    Returns ``(spikes, joints_moved)`` where spikes is a list of
    ``(vertex, moved, neighbour_average)`` sorted worst first."""
    mesh_fn = om.MFnMesh(mesh_path)
    rest = mesh_fn.getPoints(om.MSpace.kWorld)

    restore = _apply_pose(pose)
    try:
        posed = om.MFnMesh(mesh_path).getPoints(om.MSpace.kWorld)
    finally:
        _restore(restore)

    if len(posed) != len(rest):
        return [], len(restore)

    moves = [(posed[i] - rest[i]).length() for i in range(len(rest))]
    spikes = []
    vertex_it = om.MItMeshVertex(mesh_path)
    while not vertex_it.isDone():
        index = vertex_it.index()
        neighbours = list(vertex_it.getConnectedVertices())
        if len(neighbours) >= 3:
            average = sum(moves[n] for n in neighbours) / len(neighbours)
            if moves[index] > average + tolerance:
                spikes.append((index, moves[index], average))
        vertex_it.next()

    spikes.sort(key=lambda row: row[1] - row[2], reverse=True)
    return spikes, len(restore)


def skeleton_is_posed(tolerance=1e-4):
    """Joints currently rotated away from the pose their skinCluster was bound in.

    Export reads the DEFORMED mesh, so exporting while posed bakes the pose into the .p3d as
    if it were the model's shape.

    Compared against the skinCluster's own ``bindPreMatrix`` — the inverse world matrix each
    joint had at bind time — because that is precisely what drives the deformation. A joint is
    at rest when ``worldMatrix * bindPreMatrix`` is the identity. (Comparing against the
    joint's ``.bindPose`` attribute does not work: it never reported a posed rig.)"""
    posed = []
    seen = set()
    for skin in cmds.ls(type="skinCluster") or []:
        influences = cmds.skinCluster(skin, query=True, influence=True) or []
        # bindPreMatrix is a SPARSE multi, indexed by .matrix[] LOGICAL indices — those do
        # NOT compact when an influence is removed. enumerate(influences) instead assumes a
        # dense 0..N-1 range, which is only true if nothing was ever removed, or only the
        # LAST influence was. Measured: a 4-joint rig (A,B,C,D) with A and C removed left
        # influences = ['B', 'D'], bindPreMatrix multiIndices = [0,1,2,3] (untouched), but
        # .matrix multiIndices = [1, 3] — the correct logical index for each surviving
        # influence, in the same order cmds.skinCluster(...influence=True) returns them.
        # Using enumerate() here compared B against bindPreMatrix[0] (A's old slot) and D
        # against bindPreMatrix[1] (B's old slot), so a rig that was never posed reported
        # every non-trailing-removed influence as "posed" — which fires on essentially every
        # real DayZ rig, since skintransfer.finish_for_dayz() and a3obInfluence -ri both
        # prune influences by name, not just off the end.
        matrix_indices = cmds.getAttr("%s.matrix" % skin, multiIndices=True) or []
        for index, joint in zip(matrix_indices, influences):
            if joint in seen:
                continue
            try:
                pre = cmds.getAttr("%s.bindPreMatrix[%d]" % (skin, index))
                world = cmds.xform(joint, query=True, worldSpace=True, matrix=True)
            except Exception:  # noqa: BLE001 - influence removed, or a non-DAG influence
                continue
            product = om.MMatrix(world) * om.MMatrix(pre)
            identity = all(abs(product[k] - (1.0 if k in (0, 5, 10, 15) else 0.0)) <= tolerance
                           for k in range(16))
            if not identity:
                seen.add(joint)
                posed.append(joint)
    return posed


__all__ = [
    "DEFAULT_POSE",
    "DEFAULT_SPIKE_TOLERANCE",
    "find_spikes",
    "skeleton_is_posed",
]
