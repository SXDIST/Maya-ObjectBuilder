"""commands helper: sets."""

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
from a3ob.mayabridge.commands.helpers.scene import *  # noqa: F401,F403


def proxy_placeholder(lod, selection_name):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if (child.hasFn(om.MFn.kTransform)
                and attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT)
                and attr.get_string(child, A.PROXY_SELECTION) == selection_name):
            return child
    return NULL


def proxy_selection_set_exists(selection_name):
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        node = it.thisNode()
        if attr.get_bool(node, A.IS_PROXY_SELECTION) and attr.get_string(node, A.SELECTION_NAME) == selection_name:
            return True
        it.next()
    return False


def set_contains_mesh(set_obj, mesh):
    set_fn = om.MFnSet(set_obj)
    members = set_fn.getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if dag_path.node() == mesh:
            return True
    return False


def metadata_set_has_live_members(set_obj):
    members = om.MFnSet(set_obj).getMembers(True)
    return members.length() > 0


def is_object_builder_metadata_set(set_obj):
    return (bool(attr.get_string(set_obj, A.SELECTION_NAME))
            or bool(attr.get_string(set_obj, A.FLAG_COMPONENT))
            or attr.get_bool(set_obj, A.IS_PROXY_SELECTION))


# =============================================================================
# geometry analysis
# =============================================================================


def _create_set_from_members(members, name, restriction=None):
    """Create an objectSet holding ``members`` (an MSelectionList).

    Built with cmds.sets rather than MFnSet.create: the API call never enters Maya's undo
    queue, so every set made by a3obSetFlag / a3obFindComponents / proxy selections survived
    Ctrl+Z and piled up in the scene. ``restriction`` is accepted for call-site compatibility
    — no caller has ever passed anything but the default."""
    import maya.cmds as cmds
    strings = members.getSelectionStrings()
    if not strings:
        return NULL
    created = cmds.sets(strings, name=name)
    selection = om.MSelectionList()
    selection.add(created)
    return selection.getDependNode(0)


def create_metadata_set(set_name, component, value):
    members, _lod = selected_components()
    if members.length() == 0:
        return NULL
    set_obj = _create_set_from_members(members, set_name)
    attr.set_string(set_obj, A.SELECTION_NAME, set_name)
    attr.set_string(set_obj, A.FLAG_COMPONENT, component)
    attr.set_int(set_obj, A.FLAG_VALUE, value)
    attr.mark_technical_set(set_obj)
    return set_obj


def _sanitized_set_name(selection_name):
    name = "a3ob_" + selection_name
    for ch in (":", "/", "\\", "."):
        name = name.replace(ch, "_")
    return name


def create_proxy_selection_set(selection_name):
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, component in _iter_selection(sel):
        if dag_path.node().hasFn(om.MFn.kMesh) and not component.isNull():
            members.add((dag_path, component))
    if members.length() == 0:
        return
    set_obj = _create_set_from_members(members, _sanitized_set_name(selection_name))
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)


# =============================================================================
# component (find components) sets
# =============================================================================


def selected_components():
    """Return (MSelectionList members, lod MObject) for selected mesh components."""
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    lod = NULL
    for dag_path, component in _iter_selection(sel):
        if component.isNull():
            continue
        candidate = lod_transform_for_path(dag_path)
        if candidate.isNull():
            continue
        if lod.isNull():
            lod = candidate
        members.add((dag_path, component))
    return members, lod


class MeshTarget:
    __slots__ = ("mesh_path", "lod")

    def __init__(self, mesh_path, lod):
        self.mesh_path = mesh_path
        self.lod = lod


def _add_mesh_target(mesh_path, lod, targets):
    if mesh_path.isValid() and mesh_path.node().hasFn(om.MFn.kMesh):
        for target in targets:
            if target.mesh_path.node() == mesh_path.node() and (target.lod == lod or same_node(target.lod, lod)):
                return
        targets.append(MeshTarget(mesh_path, lod))


def _add_child_mesh_targets(lod, targets):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            _add_mesh_target(om.MFnDagNode(child).getPath(), lod, targets)
        elif child.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(child)
            if not mesh.isNull():
                _add_mesh_target(om.MFnDagNode(mesh).getPath(), lod, targets)


def selected_mesh_targets():
    targets = []
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kMesh):
            _add_mesh_target(dag_path, lod_transform_for_path(dag_path), targets)
            continue
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            _add_child_mesh_targets(node, targets)
            continue
        if node.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(node)
            if not mesh.isNull():
                mesh_path = om.MFnDagNode(mesh).getPath()
                _add_mesh_target(mesh_path, lod_transform_for_path(mesh_path), targets)
    return targets


def _component_set_belongs_to_target(set_obj, lod, mesh_path):
    members = om.MFnSet(set_obj).getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if not lod.isNull() and same_node(lod_transform_for_path(dag_path), lod):
            return True
        if lod.isNull() and dag_path.node() == mesh_path.node():
            return True
    return False


def _delete_existing_component_sets(lod, mesh_path):
    to_delete = []
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        set_obj = it.thisNode()
        selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
        if is_component_selection_name(selection_name) and _component_set_belongs_to_target(set_obj, lod, mesh_path):
            to_delete.append(om.MFnDependencyNode(set_obj).name())
        it.next()
    if to_delete:
        import maya.cmds as cmds
        cmds.delete(to_delete)


# =============================================================================
# material nodes
# =============================================================================


def update_proxy_selection_set(set_obj, path, index):
    import maya.cmds as cmds
    selection_name = proxy_selection_name(path, index)
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)
    cmds.rename(om.MFnDependencyNode(set_obj).name(), _sanitized_set_name(selection_name))


def update_proxy_placeholder(proxy, path, index, modifier=None):
    selection_name = proxy_selection_name(path, index)
    attr.set_bool(proxy, A.IS_PROXY, True, modifier)
    attr.set_string(proxy, A.PROXY_PATH, path, modifier)
    attr.set_int(proxy, A.PROXY_INDEX, index, modifier)
    attr.set_string(proxy, A.PROXY_SELECTION, selection_name, modifier)


def vertex_source_index_map(transform):
    """Maya vertex index -> P3D source vertex index, or [] when the LOD carries no remap.

    Import dedupes/reorders vertices, so the Maya index space and the P3D source space are
    NOT interchangeable. Masses are stored and exported in source order, while the UI edits
    them per Maya vertex — without this map the two silently disagree."""
    raw = attr.get_string(transform, A.VERTEX_SOURCE_INDICES)
    if not raw:
        return []
    indices = []
    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            indices.append(int(token))
        except ValueError:
            return []  # malformed remap — fall back to identity rather than scramble masses
    return indices


def mass_slot_count(transform):
    """How many mass slots this LOD stores: the P3D source vertex count when the LOD came
    from an import (that is the space the mass TAGG uses), else the Maya vertex count."""
    source_count = attr.get_int(transform, A.SOURCE_VERTEX_COUNT, 0)
    if source_count > 0:
        return source_count
    return max(vertex_count_for_lod(transform), 0)


def mass_values_for_lod(transform, default_value):
    count = mass_slot_count(transform)
    values = [default_value] * count
    existing = split_semicolon(attr.get_string(transform, A.MASS_VALUES))
    for i in range(min(len(existing), len(values))):
        values[i] = float(existing[i])
    return values


def set_selected_mass_values(lod, value, modifier=None):
    members, selected_lod = selected_components()
    if members.length() == 0:
        return False
    if lod.isNull():
        lod = selected_lod

    masses = mass_values_for_lod(lod, 0.0)
    for i in range(members.length()):
        try:
            dag_path, component = members.getComponent(i)
        except Exception:
            continue
        if component.isNull() or not component.hasFn(om.MFn.kMeshVertComponent):
            continue
        elements = om.MFnSingleIndexedComponent(component).getElements()
        remap = vertex_source_index_map(lod)
        for index in elements:
            # Selected components are Maya vertices; masses live in P3D source order.
            slot = remap[index] if 0 <= index < len(remap) else index
            if 0 <= slot < len(masses):
                masses[slot] = value

    attr.set_bool(lod, A.HAS_MASS, True, modifier)
    attr.set_string(lod, A.MASS_VALUES, mass_values_string(masses), modifier)
    return True


# =============================================================================
# set creation
# =============================================================================


__all__ = [
    "proxy_placeholder",
    "proxy_selection_set_exists",
    "set_contains_mesh",
    "metadata_set_has_live_members",
    "is_object_builder_metadata_set",
    "_create_set_from_members",
    "create_metadata_set",
    "_sanitized_set_name",
    "create_proxy_selection_set",
    "selected_components",
    "MeshTarget",
    "_add_mesh_target",
    "_add_child_mesh_targets",
    "selected_mesh_targets",
    "_component_set_belongs_to_target",
    "_delete_existing_component_sets",
    "update_proxy_selection_set",
    "update_proxy_placeholder",
    "mass_values_for_lod",
    "mass_slot_count",
    "vertex_source_index_map",
    "set_selected_mass_values",
]
