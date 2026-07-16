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
    set_fn = om.MFnSet()
    if restriction is None:
        restriction = om.MFnSet.kNone
    set_obj = set_fn.create(members, restriction)
    set_fn.setName(name)
    return set_obj


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


def update_proxy_placeholder(proxy, path, index):
    selection_name = proxy_selection_name(path, index)
    attr.set_bool(proxy, A.IS_PROXY, True)
    attr.set_string(proxy, A.PROXY_PATH, path)
    attr.set_int(proxy, A.PROXY_INDEX, index)
    attr.set_string(proxy, A.PROXY_SELECTION, selection_name)


def mass_values_for_lod(transform, default_value):
    count = max(vertex_count_for_lod(transform), 0)
    values = [default_value] * count
    existing = split_semicolon(attr.get_string(transform, A.MASS_VALUES))
    for i in range(min(len(existing), len(values))):
        values[i] = float(existing[i])
    return values


def set_selected_mass_values(lod, value):
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
        for index in elements:
            if 0 <= index < len(masses):
                masses[index] = value

    attr.set_bool(lod, A.HAS_MASS, True)
    attr.set_string(lod, A.MASS_VALUES, mass_values_string(masses))
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
    "set_selected_mass_values",
]
