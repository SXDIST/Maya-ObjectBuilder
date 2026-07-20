"""Reading a mesh's skinCluster, and storing the baked copy of its weights.

This exists to break a real import cycle. ``weightsync`` needs to read a skinCluster (that
is what it syncs from) and ``commands.skin`` needs to store a bake (that is what
``a3obBakeSkin`` does), so each was lazily importing a function out of the other from inside
a function body — a mutual dependency held apart only by deferring both halves to call time.
Everything both of them share now lives here, below both, and both import it normally.

Deliberately a leaf: it imports the attribute schema and OpenMaya, nothing else from the
plugin. ``a3ob.mayabridge.skinweights`` was the other candidate home and is the wrong one —
it is Maya-free on purpose so the pure-Python test suite can exercise the weight math, and
every function here needs ``maya.api``.
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A


def skin_cluster_for_mesh(mesh_path):
    """The skinCluster deforming ``mesh_path`` (an MDagPath to the shape), as an MObject, or None."""
    history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    if not skins:
        return None
    selection = om.MSelectionList()
    selection.add(skins[0])
    return selection.getDependNode(0)


def complete_vertex_component(mesh_path):
    """A component covering every vertex of ``mesh_path`` — what getWeights/setWeights want.

    One home for what used to be a byte-identical private copy in ``commands.skin`` and in
    ``export.taggs.skin``, differing only in the name of a local."""
    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.setCompleteData(om.MFnMesh(mesh_path).numVertices)
    return component


def influence_leaf_names(skin_fn):
    """Bare bone name per influence, in getWeights() column order.

    DayZ selections are named after the bare bone name, so path and namespace are stripped.
    Note ``export.taggs.skin`` keeps its OWN version of this: it additionally warns when two
    influences collapse to the same leaf name, because on the export path that silently drops
    a limb's rig. That extra check is the point of it, so the two are not merged."""
    return [path.partialPathName().split("|")[-1].split(":")[-1]
            for path in skin_fn.influenceObjects()]


def vertex_neighbours(mesh_path):
    """Connected-vertex ids per vertex."""
    neighbours = [[] for _ in range(om.MFnMesh(mesh_path).numVertices)]
    vertex_it = om.MItMeshVertex(mesh_path)
    while not vertex_it.isDone():
        neighbours[vertex_it.index()] = list(vertex_it.getConnectedVertices())
        vertex_it.next()
    return neighbours


def read_skin(mesh_path):
    """``(skin_fn, weights, influence_count, neighbours)`` for a skinned mesh, or None."""
    skin_obj = skin_cluster_for_mesh(mesh_path)
    if skin_obj is None:
        return None
    skin_fn = oma.MFnSkinCluster(skin_obj)
    if not skin_fn.influenceObjects():
        return None
    weights, influence_count = skin_fn.getWeights(mesh_path, complete_vertex_component(mesh_path))
    if influence_count <= 0:
        return None
    return skin_fn, list(weights), influence_count, vertex_neighbours(mesh_path)


def store_bake(transform, text):
    """Write ``text`` as the LOD's baked weights, keeping the copy it replaces.

    Sync runs on every save from whatever skinCluster is live, which is right until the live
    one is a rig that was just re-bound: the fresh bind's defaults then overwrite a good bake
    and the only copy is gone. There is no reliable way to tell a deliberate re-bake from
    that accident — a fresh bind looks like any other rig — so instead of guessing, the
    previous value is always kept and ``a3obBakeSkin -restore -previous`` can reach it.

    Note the early return on unchanged text: it is why ``a3obBakeSkin -restore`` writes the
    previous slot directly instead of coming through here. Do not remove either behaviour."""
    if not text:
        return False
    existing = attr.get_string(transform, A.BAKED_WEIGHTS) or ""
    if existing == text:
        return False
    if existing:
        attr.set_string(transform, A.BAKED_WEIGHTS_PREVIOUS, existing)
    attr.set_string(transform, A.BAKED_WEIGHTS, text)
    return True


__all__ = [
    "skin_cluster_for_mesh",
    "complete_vertex_component",
    "influence_leaf_names",
    "vertex_neighbours",
    "read_skin",
    "store_bake",
]
