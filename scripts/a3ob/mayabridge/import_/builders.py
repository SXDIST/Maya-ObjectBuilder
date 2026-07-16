"""P3D MLOD -> Maya DAG/mesh conversion (OpenMaya 2.0).

Port of ``src/maya/MayaMeshImport.cpp``. Builds a root transform named after the file,
groups LODs by category, and for each LOD creates a mesh (shape directly under the LOD
transform), applies UVs/custom normals, materials, selection/flag sets, proxy
placeholders, Memory-LOD locators and the ``a3ob*`` round-trip metadata.

Coordinate convention: P3D (Z-up) -> Maya (Y-up) point ``(x, y, z) -> (x, z, -y)``.
"""

import os
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A

from a3ob.mayabridge.import_.convert import *  # noqa: F401,F403

def _create_set(members, name, restriction=None):
    set_fn = om.MFnSet()
    set_obj = set_fn.create(members, restriction if restriction is not None else om.MFnSet.kNone)
    set_fn.setName(name)
    return set_obj


def _create_flag_set(mesh_path, name, component_type, flag, maya_component_type, indices):
    if not indices:
        return
    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(maya_component_type)
    component_fn.addElements(om.MIntArray(indices))
    members = om.MSelectionList()
    members.add((mesh_path, component))
    set_obj = _create_set(members, name)
    attr.set_int(set_obj, A.FLAG_VALUE, flag)
    attr.set_string(set_obj, A.FLAG_COMPONENT, component_type)
    attr.mark_technical_set(set_obj)


def create_flag_sets(mesh, lod, vertex_remap):
    mesh_path = om.MFnDagNode(mesh).getPath()

    vertex_flags = {}
    for source_index, imported_index in vertex_remap.items():
        if source_index < len(lod.vertices):
            flag = lod.vertices[source_index].flag
            if flag != 0:
                vertex_flags.setdefault(flag, []).append(imported_index)
    for flag in sorted(vertex_flags):
        _create_flag_set(mesh_path, flag_set_name("VERTEX_", flag), "vertex", flag,
                         om.MFn.kMeshVertComponent, sorted(vertex_flags[flag]))

    face_flags = {}
    for face_index, face in enumerate(lod.faces):
        if face.flag != 0:
            face_flags.setdefault(face.flag, []).append(face_index)
    for flag in sorted(face_flags):
        _create_flag_set(mesh_path, flag_set_name("FACE_", flag), "face", flag,
                         om.MFn.kMeshPolygonComponent, sorted(face_flags[flag]))


def _create_selection_set(mesh_path, tagg, vertex_remap):
    if tagg.data is None or tagg.data.kind != "Selection":
        return
    selection = tagg.data
    members = om.MSelectionList()

    if selection.vertex_weights:
        component_fn = om.MFnSingleIndexedComponent()
        vertices = component_fn.create(om.MFn.kMeshVertComponent)
        added = 0
        for source_index, _weight in selection.vertex_weights:
            mapped = vertex_remap.get(source_index)
            if mapped is not None:
                component_fn.addElement(mapped)
                added += 1
        if added > 0:
            members.add((mesh_path, vertices))

    if selection.face_weights:
        component_fn = om.MFnSingleIndexedComponent()
        faces = component_fn.create(om.MFn.kMeshPolygonComponent)
        for face_index, _weight in selection.face_weights:
            component_fn.addElement(face_index)
        if component_fn.elementCount > 0:
            members.add((mesh_path, faces))

    if members.length() == 0:
        return

    set_obj = _create_set(members, selection_set_name(tagg.name))
    attr.set_string(set_obj, A.SELECTION_NAME, tagg.name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, tagg.is_proxy())
    attr.mark_technical_set(set_obj)


def create_selection_sets(mesh, lod, vertex_remap):
    mesh_path = om.MFnDagNode(mesh).getPath()
    for tagg in lod.taggs:
        if tagg.data is not None and tagg.data.kind == "Selection":
            _create_selection_set(mesh_path, tagg, vertex_remap)


def create_proxy_placeholders(parent_transform_name, transform_name, lod):
    for tagg in lod.taggs:
        if not tagg.is_proxy():
            continue
        parsed = parse_proxy_name(tagg.name)
        if parsed is None:
            continue
        proxy_path, proxy_index = parsed
        proxy_name = _create_transform(parent_transform_name, proxy_transform_name(transform_name, proxy_path, proxy_index))
        proxy_obj = _name_to_object(proxy_name)
        attr.set_bool(proxy_obj, A.IS_PROXY, True)
        attr.set_string(proxy_obj, A.PROXY_PATH, proxy_path)
        attr.set_int(proxy_obj, A.PROXY_INDEX, proxy_index)
        attr.set_string(proxy_obj, A.PROXY_SELECTION, tagg.name)


def _create_single_locator(parent_name, name, selection_name, position):
    transform_name = _create_transform(parent_name, name)
    transform_obj = _name_to_object(transform_name)
    attr.set_string(transform_obj, A.SELECTION_NAME, selection_name)
    cmds.setAttr(transform_name + ".translate", position.x, position.y, position.z, type="double3")
    # Build the shape name from the transform's leaf only: transform_name may come back as
    # a full DAG path (with "|" and a namespace prefix) during File > Import, and appending
    # "Shape" to that yields an illegal node name ("New name has no legal characters").
    shape_leaf = _leaf(transform_name).rsplit(":", 1)[-1] + "Shape"
    shape = cmds.createNode("locator", name=shape_leaf, parent=transform_name)
    cmds.setAttr(shape + ".localScale", MEMORY_LOCATOR_SCALE, MEMORY_LOCATOR_SCALE, MEMORY_LOCATOR_SCALE, type="double3")


def create_locators_for_memory_lod(parent_transform_name, lod):
    for tagg in lod.taggs:
        if tagg.data is None or tagg.data.kind != "Selection" or tagg.is_proxy():
            continue
        selection = tagg.data
        positions = [core_to_maya_point(lod.vertices[vi].position)
                     for vi, _weight in selection.vertex_weights if vi < len(lod.vertices)]
        if not positions:
            continue
        node_name = sanitized_name(tagg.name)
        if len(positions) == 1:
            _create_single_locator(parent_transform_name, node_name, tagg.name, positions[0])
        else:
            group_name = _create_transform(parent_transform_name, node_name)
            group_obj = _name_to_object(group_name)
            attr.set_string(group_obj, A.SELECTION_NAME, tagg.name)
            for pos in positions:
                _create_single_locator(group_name, "point", "", pos)


# =============================================================================
# importer
# =============================================================================


__all__ = [
    "_create_set",
    "_create_flag_set",
    "create_flag_sets",
    "_create_selection_set",
    "create_selection_sets",
    "create_proxy_placeholders",
    "_create_single_locator",
    "create_locators_for_memory_lod",
]
