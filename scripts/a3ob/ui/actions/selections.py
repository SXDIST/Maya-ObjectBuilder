"""selections action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _clear_selection_manager_state(message="Select a row to see details."):
    dock = _active_qt_dock()
    if dock is not None:
        dock.set_selection_details(message)


def _selected_selection_set():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_selection_set_node()
    return None


def _update_selection_details():
    set_node = _selected_selection_set()
    if not set_node:
        _clear_selection_manager_state()
        return
    details = _selection_set_details(set_node)
    dock = _active_qt_dock()
    if dock is not None:
        dock.set_selection_details(details)


def _refresh_selection_manager(rebuild_lods=True):
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_selection_manager(rebuild_lods)


def _select_set_members():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a live selection set in the MayaObjectBuilder Selection Manager")
        _refresh_selection_manager(False)
        return
    members = _live_set_members(set_node)
    if not members:
        cmds.warning("Selection set has no live members")
        _refresh_selection_manager(False)
        return
    cmds.select(members, replace=True)


def _rename_selection_set():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a live selection set in the MayaObjectBuilder Selection Manager")
        _refresh_selection_manager(False)
        return
    old_name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
    new_name = _prompt("Rename Selection", "Object Builder selection name:", old_name)
    if not new_name:
        return
    if not _node_exists(set_node):
        cmds.warning("Selection set was deleted")
        _refresh_selection_manager(False)
        return
    cmds.setAttr(set_node + ".a3obSelectionName", new_name, type="string")
    _hide_object_builder_set(set_node)
    node_name = set_node.split(":")[-1]
    prefix = node_name.split("_SEL_")[0] if "_SEL_" in node_name else node_name
    cmds.rename(set_node, prefix + "_SEL_" + new_name.replace(" ", "_"))
    _refresh_selection_manager()


def find_components_from_ui():
    load_plugin()
    cmds.a3obFindComponents()
    _refresh_context_ui()


def _create_selection_set():
    selection = _canonical_selection_components()
    if not selection:
        cmds.warning("Select a mesh, faces, or vertices before creating an Object Builder selection")
        return
    name = _prompt("Create Selection", "Object Builder selection name:", "camo")
    if not name:
        return
    set_node = cmds.sets(selection, name="a3ob_SEL_" + name.replace(" ", "_"))
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", name, type="string")
    _hide_object_builder_set(set_node)
    _refresh_selection_manager()


def _add_to_selection_set():
    set_node = _selected_selection_set()
    selection = _canonical_selection_components()
    if not set_node or not selection:
        cmds.warning("Select a live selection set and mesh, faces, or vertices to add")
        _refresh_selection_manager(False)
        return
    cmds.sets(selection, add=set_node)
    _refresh_selection_manager()


def _remove_from_selection_set():
    set_node = _selected_selection_set()
    selection = _canonical_selection_components()
    if not set_node or not selection:
        cmds.warning("Select a live selection set and mesh, faces, or vertices to remove")
        _refresh_selection_manager(False)
        return
    cmds.sets(selection, remove=set_node)
    _refresh_selection_manager()


def _delete_selection_set():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a live selection set to delete")
        _refresh_selection_manager(False)
        return
    cmds.delete(set_node)
    _clear_selection_manager_state()
    _refresh_selection_manager()


def _clear_all_object_builder_sets():
    sets = [node for node in cmds.ls(type="objectSet") or [] if _is_object_builder_set(node)]
    if not sets:
        cmds.warning("No Object Builder selection sets to clear")
        _refresh_selection_manager(False)
        return
    cmds.delete(sets)
    _clear_selection_manager_state("Object Builder selection sets cleared.")
    _refresh_selection_manager()


__all__ = [
    "_clear_selection_manager_state",
    "_selected_selection_set",
    "_update_selection_details",
    "_refresh_selection_manager",
    "_select_set_members",
    "_rename_selection_set",
    "find_components_from_ui",
    "_create_selection_set",
    "_add_to_selection_set",
    "_remove_from_selection_set",
    "_delete_selection_set",
    "_clear_all_object_builder_sets",
]
