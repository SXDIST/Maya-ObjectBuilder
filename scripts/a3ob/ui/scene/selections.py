"""Scene helper: selections domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
from a3ob.ui.scene.attrs import *  # noqa: F401,F403
from a3ob.ui.scene.lods import *  # noqa: F401,F403


def _is_object_builder_set(node):
    return _attr_exists(node, "a3obSelectionName") or _attr_exists(node, "a3obIsProxySelection") or _attr_exists(node, "a3obFlagComponent")


def _set_bool_attr(node, attr, value):
    if not _node_exists(node):
        return
    if not _attr_exists(node, attr):
        cmds.addAttr(node, longName=attr, attributeType="bool")
    cmds.setAttr(f"{node}.{attr}", bool(value))


def _hide_object_builder_set(node):
    if not _is_object_builder_set(node):
        return
    _set_bool_attr(node, "a3obTechnicalSet", True)
    if _attr_exists(node, "hiddenInOutliner"):
        cmds.setAttr(f"{node}.hiddenInOutliner", True)


def _object_builder_sets():
    """Every a3ob objectSet, found through Maya's own attribute filter.

    Listing all objectSets and probing each with attributeQuery cost 10-20 ms per dock
    refresh; three attribute queries answered by Maya cost well under a millisecond."""
    found = []
    seen = set()
    for attribute in ("a3obSelectionName", "a3obIsProxySelection", "a3obFlagComponent"):
        for node in cmds.ls("*." + attribute, objectsOnly=True) or []:
            if node not in seen and cmds.objectType(node, isType="objectSet"):
                seen.add(node)
                found.append(node)
    return found


def _normalize_object_builder_sets():
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        for node in _object_builder_sets():
            _hide_object_builder_set(node)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def _selection_sets():
    _normalize_object_builder_sets()
    sets = []
    for node in _object_builder_sets():
        if not _attr_exists(node, "a3obSelectionName"):
            continue
        name = _safe_get_attr(node, "a3obSelectionName", "") or ""
        is_proxy = bool(_safe_get_attr(node, "a3obIsProxySelection", False))
        flag_component = _safe_get_attr(node, "a3obFlagComponent", "") or ""
        lod = _set_lod_label(node)
        sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod})
    return sorted(sets, key=lambda item: (item["lod"].lower(), item["kind"], item["name"].lower(), item["node"].lower()))


def _live_set_members(set_node):
    if not _node_exists(set_node):
        return []
    members = cmds.sets(set_node, query=True) or []
    live_members = []
    for member in members:
        expanded = cmds.ls(member, flatten=True) or []
        live_members.extend(item for item in expanded if _node_exists(item.split(".", 1)[0]))
    return live_members


def _set_member_count(set_node):
    if not _node_exists(set_node):
        return 0
    try:
        return cmds.sets(set_node, query=True, size=True) or 0
    except RuntimeError:
        return 0


def _selection_set_details(set_node):
    count = _set_member_count(set_node)
    name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
    flag_component = _safe_get_attr(set_node, "a3obFlagComponent", "") or ""
    is_proxy = bool(_safe_get_attr(set_node, "a3obIsProxySelection", False))
    return f"LOD: {_set_lod_label(set_node)}    Type: {_set_kind(is_proxy, flag_component)}    OB name: {name}    Members: {count}\nMaya set: {set_node}"


def _canonical_selection_components(selection=None):
    selection = selection or (cmds.ls(selection=True, flatten=True, long=True) or [])
    components = []
    seen = set()
    for item in selection:
        if ".vtx[" in item:
            expanded = cmds.ls(item, flatten=True, long=True) or []
        elif ".f[" in item:
            expanded = cmds.polyListComponentConversion(item, fromFace=True, toVertex=True) or []
            expanded = cmds.ls(expanded, flatten=True, long=True) or []
        else:
            expanded = []
            for shape in _mesh_shapes_for_item(item):
                count = cmds.polyEvaluate(shape, vertex=True)
                if count:
                    expanded.extend(cmds.ls(f"{shape}.vtx[0:{count - 1}]", flatten=True, long=True) or [])
        for component in expanded:
            if component not in seen and _node_exists(component.split(".", 1)[0]):
                seen.add(component)
                components.append(component)
    return components


def _mesh_shapes_for_item(item):
    node = item.split(".", 1)[0]
    if not _node_exists(node):
        return []
    if cmds.objectType(node, isType="mesh"):
        return [node]
    return cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []


__all__ = [
    "_is_object_builder_set",
    "_set_bool_attr",
    "_hide_object_builder_set",
    "_normalize_object_builder_sets",
    "_selection_sets",
    "_live_set_members",
    "_set_member_count",
    "_selection_set_details",
    "_canonical_selection_components",
    "_mesh_shapes_for_item",
]
