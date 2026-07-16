"""commands helper: scene."""

"""The ``a3ob*`` Maya commands (OpenMaya 2.0 MPxCommand).

Port of ``src/commands/StubCommands.cpp``. Command names, flags and the resulting
``a3ob*`` attribute schema are preserved exactly — this is the contract the Python UI
and the ``tests/mayapy`` workflows depend on.

First-cut note: these commands are functional but not yet wired for undo. The C++
versions accumulated ``MDGModifier``/``MDagModifier`` operations; here operations are
applied directly. Undo support can be layered on later without changing the surface.
"""

import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.commands.helpers.primitives import *  # noqa: F401,F403


def _iter_selection(sel):
    for i in range(sel.length()):
        try:
            dag_path, component = sel.getComponent(i)
        except Exception:
            continue
        if not dag_path.isValid():
            continue
        yield dag_path, component


def first_mesh_child(transform):
    if transform.isNull():
        return NULL
    dag = om.MFnDagNode(transform)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            return child
    return NULL


def selected_transform_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kTransform):
            return node
        if node.hasFn(om.MFn.kMesh):
            return om.MFnDagNode(node).parent(0)
    return NULL


def lod_transform_for_path(dag_path):
    node = dag_path.node()
    while not node.isNull():
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            return node
        dag = om.MFnDagNode(node)
        if dag.parentCount() == 0:
            break
        node = dag.parent(0)
    return NULL


def selected_lod_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        lod = lod_transform_for_path(dag_path)
        if not lod.isNull():
            return lod
    return NULL


def lod_transforms(selection_only):
    lods = []
    if selection_only:
        sel = om.MGlobal.getActiveSelectionList()
        for dag_path, _component in _iter_selection(sel):
            node = dag_path.node()
            if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
                lods.append(node)
        return lods

    it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
    while not it.isDone():
        node = it.currentItem()
        if attr.get_bool(node, A.IS_LOD):
            lods.append(node)
        it.next()
    return lods


def node_name(node):
    if node.isNull():
        return ""
    return om.MFnDependencyNode(node).name()


def same_node(a, b):
    return not a.isNull() and not b.isNull() and a == b


# =============================================================================
# LOD metadata
# =============================================================================


def set_lod_attributes(transform, lod_type, resolution):
    from a3ob.formats.p3d import LodResolution
    signature = LodResolution.encode(lod_type, resolution)
    attr.set_bool(transform, A.IS_LOD, True)
    attr.set_int(transform, A.LOD_TYPE, lod_type)
    attr.set_int(transform, A.RESOLUTION, resolution)
    attr.set_double(transform, A.RESOLUTION_SIGNATURE, signature)
    attr.set_int(transform, A.SOURCE_VERTEX_COUNT, 0)
    attr.set_int(transform, A.SOURCE_FACE_COUNT, 0)


def vertex_count_for_lod(transform):
    mesh = first_mesh_child(transform)
    if not mesh.isNull():
        return om.MFnMesh(mesh).numVertices
    return attr.get_int(transform, A.SOURCE_VERTEX_COUNT, 0)


# =============================================================================
# proxy / set helpers
# =============================================================================


def selected_dependency_node_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        node = sel.getDependNode(i)
        if not node.isNull():
            return node
    return NULL


__all__ = [
    "_iter_selection",
    "first_mesh_child",
    "selected_transform_or_null",
    "lod_transform_for_path",
    "selected_lod_or_null",
    "lod_transforms",
    "node_name",
    "same_node",
    "set_lod_attributes",
    "vertex_count_for_lod",
    "selected_dependency_node_or_null",
]
