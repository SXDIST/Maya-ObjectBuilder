"""Module-level action wrappers and scene business logic driven by the dock."""

import contextlib

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


@contextlib.contextmanager
def _undo_chunk(name):
    """Group Maya operations into a single named undo chunk."""
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    finally:
        cmds.undoInfo(closeChunk=True)


def _selected_lod_definition():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_lod_definition()
    return LOD_DEFINITIONS[0]


def _lod_resolution_value(definition):
    if not definition["has_resolution"]:
        return definition["default_resolution"]
    dock = _active_qt_dock()
    if dock is not None:
        return dock.lod_resolution_value()
    return definition["default_resolution"]


def _lod_assignment_label(definition=None, resolution=None):
    definition = definition or _selected_lod_definition()
    resolution = _lod_resolution_value(definition) if resolution is None else resolution
    if definition["has_resolution"]:
        return f"{definition['label']} {resolution}"
    return definition["label"]


def _refresh_lod_assignment_ui(*_):
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_lod_assignment()


def _lod_node_name(definition, resolution):
    label = _lod_assignment_label(definition, resolution)
    return label.replace(" ", "_").replace("/", "_")


def assign_lod_to_selection():
    load_plugin()
    if not cmds.ls(selection=True):
        cmds.warning("Select a transform, mesh, or component before assigning LOD metadata")
        return
    with _undo_chunk("Create LOD"):
        definition = _selected_lod_definition()
        resolution = _lod_resolution_value(definition)
        cmds.a3obCreateLOD(lodType=definition["type"], resolution=resolution, name=_lod_node_name(definition, resolution))
        _refresh_context_ui()
        _refresh_lod_assignment_ui()


def create_empty_lod():
    load_plugin()
    selection = cmds.ls(selection=True) or []
    cmds.select(clear=True)
    definition = _selected_lod_definition()
    resolution = _lod_resolution_value(definition)
    node = cmds.a3obCreateLOD(lodType=definition["type"], resolution=resolution, name=_lod_node_name(definition, resolution))
    if node:
        cmds.select(node, replace=True)
    elif selection:
        cmds.select(selection, replace=True)
    _refresh_context_ui()
    _refresh_lod_assignment_ui()


LOD_ATTRS = (
    "a3obIsLOD", "a3obLodType", "a3obResolution",
    "a3obResolutionSignature", "a3obSourceVertexCount", "a3obSourceFaceCount",
)


def _remove_lod_from_selection():
    load_plugin()
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD transform to remove LOD status")
        return
    for attr in LOD_ATTRS:
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.deleteAttr(node, attribute=attr)
    _refresh_context_ui()


def generate_auto_lods_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    generated = _auto_lod_module().generate_auto_lods(dock.auto_lod_settings())
    if generated:
        _refresh_context_ui()


def apply_mass_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    value = dock.mass_value()
    mode = dock.mass_mode()
    with _undo_chunk("Set Mass"):
        cmds.a3obSetMass(value=value, selectedComponents=(mode == "Selected vertices"))


def clear_mass_from_ui():
    load_plugin()
    with _undo_chunk("Clear Mass"):
        cmds.a3obSetMass(clear=True)


def apply_flag_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    component_label = dock.flag_component()
    value = dock.flag_value()
    name = dock.flag_name()
    if not name:
        cmds.warning("Enter a flag set name")
        return
    with _undo_chunk("Set Flag"):
        cmds.a3obSetFlag(component=component_label.lower(), value=value, name=name)


def create_proxy_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    path = dock.proxy_path()
    index = dock.proxy_index()
    from_selection = dock.proxy_from_selection()
    if not path:
        cmds.warning("Enter a proxy path")
        return
    with _undo_chunk("Create Proxy"):
        cmds.a3obProxy(path=path, index=index, fromSelection=from_selection, update=True)


def import_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_import_path() if dock is not None else ""
    import_model_cfg(path or None)


def export_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_export_path() if dock is not None else ""
    export_model_cfg(path or None)


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


def _selected_named_property_lod():
    selected = _selected_lod_transform()
    if selected:
        return selected
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_named_property_lod()
    return None


def _refresh_named_properties(rebuild_lods=False):
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_named_properties()


def _set_named_property_value(name, value):
    lod = _selected_named_property_lod()
    if not lod:
        cmds.warning("Import a P3D or select a live Object Builder LOD")
        _refresh_named_properties(True)
        return False
    name = name.strip()
    value = value.strip()
    if not name:
        return False
    if not _ensure_string_attr(lod, "a3obProperties", "a3prop"):
        cmds.warning("Object Builder LOD was deleted")
        _refresh_named_properties(True)
        return False
    existing = _split_named_properties(_safe_get_attr(lod, "a3obProperties", "") or "")
    properties = [(key, val) for key, val in existing if key != name]
    properties.append((name, value))
    cmds.setAttr(lod + ".a3obProperties", _join_named_properties(properties), type="string")
    _refresh_named_properties()
    return True


def _commit_named_property_fields(*_):
    dock = _active_qt_dock()
    if dock is None:
        return
    _set_named_property_value(dock.named_property_name(), dock.named_property_value())


def _remove_named_property():
    lod = _selected_named_property_lod()
    dock = _active_qt_dock()
    name = dock.named_property_name() if dock is not None else ""
    if not lod or not name:
        cmds.warning("Select a named property on a live LOD to remove")
        _refresh_named_properties(True)
        return
    if not _ensure_string_attr(lod, "a3obProperties", "a3prop"):
        cmds.warning("Object Builder LOD was deleted")
        _refresh_named_properties(True)
        return
    properties = [(key, val) for key, val in _split_named_properties(_safe_get_attr(lod, "a3obProperties", "") or "") if key != name]
    cmds.setAttr(lod + ".a3obProperties", _join_named_properties(properties), type="string")
    if dock is not None:
        dock.clear_named_property_fields()
    _refresh_named_properties()


def _refresh_material_metadata():
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_material_metadata()


def _selected_material_metadata_item():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_material_metadata_item()
    return None


def _persist_selected_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        return None
    dock = _active_qt_dock()
    if dock is None:
        return None
    texture = _normalize_dayz_path(dock.material_texture_path())
    material = _normalize_dayz_path(dock.material_rvmat_path())
    changed = False
    all_targets = set(item["shading_groups"])
    if _node_exists(item["material_node"]):
        all_targets.add(item["material_node"])
        for sg in _valid_nodes(cmds.listConnections(item["material_node"], type="shadingEngine") or []):
            all_targets.add(sg)
    for target in all_targets:
        changed = _set_material_metadata_on_node(target, texture, material) or changed
    if not changed:
        cmds.warning("Material metadata target was deleted")
        return None
    item["texture"] = texture
    item["material"] = material
    return item


__all__ = [
    "_undo_chunk",
    "_selected_lod_definition",
    "_lod_resolution_value",
    "_lod_assignment_label",
    "_refresh_lod_assignment_ui",
    "_lod_node_name",
    "assign_lod_to_selection",
    "create_empty_lod",
    "LOD_ATTRS",
    "_remove_lod_from_selection",
    "generate_auto_lods_from_ui",
    "apply_mass_from_ui",
    "clear_mass_from_ui",
    "apply_flag_from_ui",
    "create_proxy_from_ui",
    "import_model_cfg_from_ui",
    "export_model_cfg_from_ui",
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
    "_find_memory_lod_from_selection",
    "_resolve_memory_lod",
    "MEMORY_LOCATOR_SCALE",
    "_shrink_locator",
    "_create_memory_locator",
    "add_memory_point",
    "_add_point_to_group",
    "_promote_locator_to_group",
    "add_point_to_selection",
    "_selected_named_property_lod",
    "_refresh_named_properties",
    "_set_named_property_value",
    "_commit_named_property_fields",
    "_remove_named_property",
    "_refresh_material_metadata",
    "_selected_material_metadata_item",
    "_persist_selected_material_metadata",
]
