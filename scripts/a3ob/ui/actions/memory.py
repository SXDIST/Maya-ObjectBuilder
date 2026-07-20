"""memory action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _find_memory_lod_from_selection():
    for node in cmds.ls(selection=True, long=True) or []:
        current = node
        while current:
            if _is_lod_transform(current) and _safe_get_attr(current, "a3obLodType", -1) == MEMORY_LOD_TYPE:
                return current
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            current = parents[0] if parents else ""
    return None


def _resolve_memory_lod():
    lod = _find_memory_lod_from_selection()
    if lod:
        return lod
    scene_lods = _scene_memory_lods()
    if len(scene_lods) == 0:
        cmds.select(clear=True)
        node = cmds.a3obCreateLOD(lodType=9, resolution=0, name="Memory")
        created = node[0] if isinstance(node, (list, tuple)) else node
        if not created:
            cmds.warning("MayaObjectBuilder: Failed to create Memory LOD.")
            return None
        cmds.inViewMessage(amg="Memory LOD created automatically", pos="midCenter", fade=True)
        return created
    if len(scene_lods) == 1:
        return scene_lods[0]
    if QT_AVAILABLE and qt_widgets:
        labels = [_lod_label(n) for n in scene_lods]
        chosen, ok = qt_widgets.QInputDialog.getItem(
            None,
            "Select Memory LOD",
            "Multiple Memory LODs found. Choose one:",
            labels,
            0,
            False
        )
        if ok:
            chosen_idx = labels.index(chosen)
            return scene_lods[chosen_idx]
    cmds.warning(
        "MayaObjectBuilder: Multiple Memory LODs found in the scene. "
        "Select one in the Outliner first, then click Add Memory Point."
    )
    return None


MEMORY_LOCATOR_SCALE = 0.05  # keep UI-created points as tidy dots, matching importer


def _shrink_locator(transform):
    for shape in (cmds.listRelatives(transform, shapes=True, type="locator", fullPath=True) or []):
        cmds.setAttr(shape + ".localScale", MEMORY_LOCATOR_SCALE, MEMORY_LOCATOR_SCALE, MEMORY_LOCATOR_SCALE, type="double3")


def _create_memory_locator(parent_lod, selection_name):
    cmds.select(clear=True)
    locator = cmds.spaceLocator(name=selection_name)[0]
    _ensure_string_attr(locator, "a3obSelectionName", "a3sn")
    cmds.setAttr(f"{locator}.a3obSelectionName", selection_name, type="string")
    cmds.parent(locator, parent_lod, relative=False)
    _shrink_locator(locator)
    cmds.select(locator)
    return locator


def add_memory_point():
    load_plugin()
    parent_lod = _resolve_memory_lod()
    if not parent_lod:
        return
    name = _prompt("Add Memory Point", "Memory point name:")
    if not name:
        return
    try:
        _create_memory_locator(parent_lod, name)
    except RuntimeError as exc:
        cmds.warning(f"MayaObjectBuilder: Could not create memory point: {exc}")


def _add_point_to_group(group_node):
    """Create a new anonymous locator inside a group container and select it."""
    cmds.select(clear=True)
    locator = cmds.spaceLocator(name="point")[0]
    cmds.parent(locator, group_node, relative=False)
    _shrink_locator(locator)
    cmds.select(locator)
    return locator


def _promote_locator_to_group(locator_node, memory_lod):
    """Convert a direct Memory LOD locator to a group container with two point locators."""
    sel_name = _safe_get_attr(locator_node, "a3obSelectionName") or locator_node.split("|")[-1]
    # Rename the existing locator to free up the selection name for the group
    renamed_short = cmds.rename(locator_node, "point")
    # Locate the renamed node among Memory LOD's direct children
    children = cmds.listRelatives(memory_lod, children=True, type="transform", fullPath=True) or []
    renamed_full = next((c for c in children if c.split("|")[-1] == renamed_short), None)
    if not renamed_full:
        raise RuntimeError(f"Could not locate renamed locator '{renamed_short}' under Memory LOD")
    # Create an empty group under Memory LOD named after the selection
    cmds.select(clear=True)
    group = cmds.group(empty=True, name=sel_name, parent=memory_lod)
    group_long = cmds.ls(group, long=True)[0]
    _ensure_string_attr(group_long, "a3obSelectionName", "a3sn")
    cmds.setAttr(f"{group_long}.a3obSelectionName", sel_name, type="string")
    # Move the existing locator into the group
    cmds.parent(renamed_full, group_long, relative=False)
    # Add a second point locator inside the group
    new_locator = _add_point_to_group(group_long)
    cmds.inViewMessage(
        amg=f"'{sel_name}' promoted to a multi-point selection group",
        pos="midCenter", fade=True
    )
    return group_long, new_locator


def add_point_to_selection():
    load_plugin()
    selected = cmds.ls(selection=True, long=True) or []
    if not selected:
        cmds.warning("MayaObjectBuilder: Select a memory point or selection group first.")
        return
    node = selected[0].split(".")[0]
    if not _node_exists(node):
        cmds.warning("MayaObjectBuilder: Select a memory point or selection group first.")
        return
    # Resolve shape node to its transform
    if cmds.objectType(node) == "locator":
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        node = parents[0] if parents else node
    # Case 1: group container selected → add point inside it
    if _is_group_container(node):
        try:
            _add_point_to_group(node)
        except RuntimeError as exc:
            cmds.warning(f"MayaObjectBuilder: Could not add point: {exc}")
        return
    # Must have a locator shape to proceed
    if not cmds.listRelatives(node, shapes=True, type="locator", fullPath=True):
        cmds.warning("MayaObjectBuilder: Select a memory point or selection group first.")
        return
    # Case 2: locator inside a group container → add sibling
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if parents and _is_group_container(parents[0]):
        try:
            _add_point_to_group(parents[0])
        except RuntimeError as exc:
            cmds.warning(f"MayaObjectBuilder: Could not add point: {exc}")
        return
    # Case 3: direct locator under Memory LOD → auto-promote to group + add second point
    memory_lod = _memory_lod_parent(node)
    if not memory_lod:
        cmds.warning("MayaObjectBuilder: Selected memory point is not directly under a Memory LOD.")
        return
    try:
        _promote_locator_to_group(node, memory_lod)
    except RuntimeError as exc:
        cmds.warning(f"MayaObjectBuilder: Could not promote to group: {exc}")


__all__ = [
    "_find_memory_lod_from_selection",
    "_resolve_memory_lod",
    "MEMORY_LOCATOR_SCALE",
    "_shrink_locator",
    "_create_memory_locator",
    "add_memory_point",
    "_add_point_to_group",
    "_promote_locator_to_group",
    "add_point_to_selection",
]
