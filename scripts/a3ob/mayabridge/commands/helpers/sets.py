"""ObjectSet creation and manipulation helpers for proxy placeholders, selection sets, and metadata sets."""

import maya.cmds as cmds
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


def lod_for_set(set_obj):
    """The LOD transform owning a set's members, or NULL when it has none left.

    A set records no LOD of its own — membership is the only link back, which is why this
    walks the members rather than reading an attribute. A set whose members have all been
    deleted therefore belongs to NO LOD, and that is the honest answer: the proxy key
    ``proxy:PATH.INDEX`` is not unique scene-wide, so an unowned set must not be used to go
    hunting for a counterpart it can no longer prove it shares a LOD with."""
    if set_obj.isNull():
        return NULL
    members = om.MFnSet(set_obj).getMembers(True)
    for dag_path, _component in _iter_selection(members):
        lod = lod_transform_for_path(dag_path)
        if not lod.isNull():
            return lod
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
        cmds.delete(to_delete)


# =============================================================================
# material nodes
# =============================================================================


def _cmds_ensure_attr(node_name, attr_pair, kind):
    """Add ``attr_pair`` to ``node_name`` via cmds.addAttr if it is not already there.

    This looks like a duplicate of ``attributes.set_bool``/``set_int``/``set_string`` and is
    NOT one: the two families differ in undo semantics, which is the whole reason both exist.

    cmds.addAttr/setAttr (unlike attr.set_* with no modifier, or an MDagModifier) enter
    Maya's own undo queue, which is what a non-undoable _Base command wrapped in
    undo_chunk() relies on to make attribute writes on a PRE-EXISTING node revertible.
    a3obProxy / a3obUpdateProxy are exactly that shape — they build objectSets, which cannot
    go through an MDagModifier, so they are non-undoable + undo_chunk(). Routing their writes
    through attr.set_* instead left the rename undone by Ctrl+Z while the metadata silently
    stayed changed. Collapsing these into the OpenMaya wrappers would reintroduce that."""
    long_name, short_name = attr_pair
    if cmds.attributeQuery(long_name, node=node_name, exists=True):
        return
    kwargs = {"attributeType": kind} if kind != "string" else {"dataType": "string"}
    cmds.addAttr(node_name, longName=long_name, shortName=short_name, keyable=True, **kwargs)


def _cmds_set_bool_attr(node_name, attr_pair, value):
    _cmds_ensure_attr(node_name, attr_pair, "bool")
    cmds.setAttr(node_name + "." + attr_pair[0], bool(value))


def _cmds_set_int_attr(node_name, attr_pair, value):
    _cmds_ensure_attr(node_name, attr_pair, "long")
    cmds.setAttr(node_name + "." + attr_pair[0], int(value))


def _cmds_set_string_attr(node_name, attr_pair, value):
    _cmds_ensure_attr(node_name, attr_pair, "string")
    cmds.setAttr(node_name + "." + attr_pair[0], value or "", type="string")


def update_proxy_selection_set(set_obj, path, index):
    """Rename an existing proxy selection set and refresh its a3ob* metadata.

    Both callers (a3obProxy, a3obUpdateProxy) are non-undoable _Base commands whose whole
    body runs inside one undo_chunk() — every write here therefore has to go through cmds
    (rename + addAttr/setAttr), never attr.set_* / MFnDependencyNode straight on the plug,
    or the rename would undo on Ctrl+Z while the metadata silently stayed changed."""
    selection_name = proxy_selection_name(path, index)
    old_name = om.MFnDependencyNode(set_obj).name()
    new_name = cmds.rename(old_name, _sanitized_set_name(selection_name))
    _cmds_set_string_attr(new_name, A.SELECTION_NAME, selection_name)
    _cmds_set_bool_attr(new_name, A.IS_PROXY_SELECTION, True)
    _cmds_set_bool_attr(new_name, A.TECHNICAL_SET, True)
    if cmds.attributeQuery("hiddenInOutliner", node=new_name, exists=True):
        cmds.setAttr(new_name + ".hiddenInOutliner", True)


def update_proxy_placeholder(proxy, path, index):
    """Point a proxy placeholder transform at a new proxy path/index.

    Same reasoning as update_proxy_selection_set: cmds.addAttr/setAttr, not attr.set_* /
    MDagModifier, because both a3obProxy and a3obUpdateProxy are non-undoable _Base
    commands that rely on undo_chunk() + cmds' own undo records for the whole body."""
    selection_name = proxy_selection_name(path, index)
    node_name = om.MFnDagNode(proxy).fullPathName()
    _cmds_set_bool_attr(node_name, A.IS_PROXY, True)
    _cmds_set_string_attr(node_name, A.PROXY_PATH, path)
    _cmds_set_int_attr(node_name, A.PROXY_INDEX, index)
    _cmds_set_string_attr(node_name, A.PROXY_SELECTION, selection_name)


def sync_proxy_pair(node, path, index):
    """Update BOTH halves of a proxy from either one of them.

    A proxy is a placeholder transform plus a selection set, keyed by the same
    ``proxy:PATH.INDEX`` string. ``a3obProxy`` writes them together; the two updaters below
    each write only one. Updating one alone leaves the pair disagreeing, which
    ``a3obValidate`` reports as "proxy placeholder has no matching selection set" — so the
    only correct edit is the pair, and this is the single place that knows that.

    Either half may legitimately be missing: ``a3obProxy -fromSelection 0`` builds a
    placeholder with no set at all. A missing counterpart is not an error.

    The counterpart is always looked up WITHIN ONE LOD. ``proxy_selection_name`` encodes no
    LOD identity, so a weapon proxy present in Resolution 1, Resolution 2 and View Pilot
    leaves several placeholders and several sets all carrying the identical
    ``proxy:PATH.INDEX`` string — the ordinary multi-LOD model, not an edge case. A
    scene-wide first match would update the selected node and then retag a stranger,
    corrupting a LOD the user never selected. That is exactly why ``proxy_placeholder``
    takes a LOD."""
    if node.hasFn(om.MFn.kSet):
        set_obj = node
        selection_name = attr.get_string(node, A.SELECTION_NAME)
        lod = lod_for_set(node)
        placeholder = proxy_placeholder(lod, selection_name) if not lod.isNull() else NULL
    else:
        placeholder = node
        selection_name = attr.get_string(node, A.PROXY_SELECTION)
        set_obj = _proxy_selection_set_in_lod(_parent_transform(node), selection_name)

    if not placeholder.isNull():
        update_proxy_placeholder(placeholder, path, index)
    if not set_obj.isNull():
        update_proxy_selection_set(set_obj, path, index)


def _parent_transform(node):
    """A placeholder's LOD: its DAG parent. NULL at the world, or for a non-DAG node."""
    if node.isNull() or not node.hasFn(om.MFn.kDagNode):
        return NULL
    dag = om.MFnDagNode(node)
    if dag.parentCount() == 0:
        return NULL
    parent = dag.parent(0)
    if parent.isNull() or parent.hasFn(om.MFn.kWorld):
        return NULL
    return parent


def _proxy_selection_set_in_lod(lod, selection_name):
    """The proxy selection set named ``selection_name`` whose members live under ``lod``.

    Scoped to one LOD for the reason spelled out in ``sync_proxy_pair``: the name alone is
    ambiguous across the LODs of one model. Iterates MItDependencyNodes rather than
    ``cmds.ls("*.attr")`` because that pattern does not recurse into namespaces — a proxy in
    a referenced file or imported under a namespace was invisible, and the failure was
    silent (no set found, pair left disagreeing, no error). ``proxy_selection_set_exists``
    above uses the same iteration for the same reason.

    The IS_PROXY_SELECTION check matters: a plain named-selection set may legitimately carry
    any a3obSelectionName, and only a proxy set is this proxy's other half."""
    if lod.isNull() or not selection_name:
        return NULL
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        node = it.thisNode()
        if (attr.get_bool(node, A.IS_PROXY_SELECTION)
                and attr.get_string(node, A.SELECTION_NAME) == selection_name
                and same_node(lod_for_set(node), lod)):
            return node
        it.next()
    return NULL


def vertex_source_index_map(transform):
    """Maya vertex index -> P3D source vertex index, or [] when the LOD carries no remap.

    Import dedupes/reorders vertices, so the Maya index space and the P3D source space are
    NOT interchangeable. Masses are stored and exported in source order, while the UI edits
    them per Maya vertex — without this map the two silently disagree."""
    raw = attr.get_string(transform, A.VERTEX_SOURCE_INDICES)
    if not raw:
        return []
    indices = []
    for token in split_semicolon(raw):
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
    # Hoisted: the remap is a property of the LOD, not of the component being visited, and
    # building it re-parses one integer per vertex — 6000 of them per iteration on a real LOD.
    remap = vertex_source_index_map(lod)
    for i in range(members.length()):
        try:
            dag_path, component = members.getComponent(i)
        except Exception:
            continue
        if component.isNull() or not component.hasFn(om.MFn.kMeshVertComponent):
            continue
        elements = om.MFnSingleIndexedComponent(component).getElements()
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
    "lod_for_set",
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
    "_cmds_ensure_attr",
    "_cmds_set_bool_attr",
    "_cmds_set_int_attr",
    "_cmds_set_string_attr",
    "update_proxy_selection_set",
    "update_proxy_placeholder",
    "sync_proxy_pair",
    "_parent_transform",
    "_proxy_selection_set_in_lod",
    "mass_values_for_lod",
    "mass_slot_count",
    "vertex_source_index_map",
    "set_selected_mass_values",
]
