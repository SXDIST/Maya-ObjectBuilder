from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


SCRIPT_PATH = Path(globals().get("__file__", r"C:\Users\targaryen\source\repos\maya\dayz-object-builder\scripts\objectBuilderMenu.py")).resolve()
MENU_NAME = "MayaObjectBuilderMenu"
PLUGIN_NAME = "MayaObjectBuilder"
TRANSLATOR_NAME = "Arma P3D"
DOCK_NAME = "MayaObjectBuilderWorkspaceControl"
LOD_TYPE_MENU = "MayaObjectBuilderLodTypeMenu"
LOD_RESOLUTION_FIELD = "MayaObjectBuilderLodResolutionField"
LOD_PREVIEW_TEXT = "MayaObjectBuilderLodPreviewText"
LOD_CONTEXT_TEXT = "MayaObjectBuilderLodContextText"
SELECTION_MANAGER_LIST = "MayaObjectBuilderSelectionList"
SELECTION_MANAGER_LOD_FILTER = "MayaObjectBuilderSelectionLodFilter"
SELECTION_MANAGER_TYPE_FILTER = "MayaObjectBuilderSelectionTypeFilter"
SELECTION_MANAGER_SEARCH = "MayaObjectBuilderSelectionSearch"
SELECTION_MANAGER_DETAILS = "MayaObjectBuilderSelectionDetails"
NAMED_PROPERTIES_LOD = "MayaObjectBuilderNamedPropertiesLod"
NAMED_PROPERTIES_LIST = "MayaObjectBuilderNamedPropertiesList"
NAMED_PROPERTIES_NAME = "MayaObjectBuilderNamedPropertiesName"
NAMED_PROPERTIES_VALUE = "MayaObjectBuilderNamedPropertiesValue"
NAMED_PROPERTIES_COMMON = "MayaObjectBuilderNamedPropertiesCommon"
MATERIAL_METADATA_LIST = "MayaObjectBuilderMaterialMetadataList"
MATERIAL_METADATA_TEXTURE = "MayaObjectBuilderMaterialTexture"
MATERIAL_METADATA_MATERIAL = "MayaObjectBuilderMaterialPath"
MASS_VALUE_FIELD = "MayaObjectBuilderMassValue"
MASS_MODE_MENU = "MayaObjectBuilderMassMode"
FLAG_COMPONENT_MENU = "MayaObjectBuilderFlagComponent"
FLAG_VALUE_FIELD = "MayaObjectBuilderFlagValue"
FLAG_NAME_FIELD = "MayaObjectBuilderFlagName"
PROXY_PATH_FIELD = "MayaObjectBuilderProxyPath"
PROXY_INDEX_FIELD = "MayaObjectBuilderProxyIndex"
PROXY_FROM_SELECTION_CHECK = "MayaObjectBuilderProxyFromSelection"
_selection_manager_items = {}
_named_property_lods = {}
_named_property_items = {}
_material_metadata_items = {}
_ui_script_jobs = []

COMMON_NAMED_PROPERTIES = [
    ("lodnoshadow", "1"),
    ("autocenter", "0"),
    ("buoyancy", "1"),
    ("class", "house"),
    ("forcenotalpha", "1"),
    ("map", "house"),
    ("prefershadowvolume", "1"),
]

LOD_DEFINITIONS = [
    {"type": 0, "label": "Resolution", "has_resolution": True, "default_resolution": 1},
    {"type": 1, "label": "View Gunner", "has_resolution": False, "default_resolution": 0},
    {"type": 2, "label": "View Pilot", "has_resolution": False, "default_resolution": 0},
    {"type": 3, "label": "View Cargo", "has_resolution": True, "default_resolution": 1},
    {"type": 4, "label": "ShadowVolume", "has_resolution": True, "default_resolution": 0},
    {"type": 5, "label": "Edit", "has_resolution": True, "default_resolution": 0},
    {"type": 6, "label": "Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 7, "label": "Geometry Buoyancy", "has_resolution": False, "default_resolution": 0},
    {"type": 8, "label": "Geometry PhysX", "has_resolution": False, "default_resolution": 0},
    {"type": 9, "label": "Memory", "has_resolution": False, "default_resolution": 0},
    {"type": 10, "label": "LandContact", "has_resolution": False, "default_resolution": 0},
    {"type": 11, "label": "Roadway", "has_resolution": False, "default_resolution": 0},
    {"type": 12, "label": "Paths", "has_resolution": False, "default_resolution": 0},
    {"type": 13, "label": "HitPoints", "has_resolution": False, "default_resolution": 0},
    {"type": 14, "label": "View Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 15, "label": "Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 16, "label": "View Cargo Geometry", "has_resolution": True, "default_resolution": 1},
    {"type": 17, "label": "View Cargo Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 18, "label": "View Commander", "has_resolution": False, "default_resolution": 0},
    {"type": 19, "label": "View Commander Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 20, "label": "View Commander Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 21, "label": "View Pilot Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 22, "label": "View Pilot Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 23, "label": "View Gunner Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 24, "label": "View Gunner Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 25, "label": "Subparts", "has_resolution": False, "default_resolution": 0},
    {"type": 26, "label": "Shadow View Cargo", "has_resolution": True, "default_resolution": 0},
    {"type": 27, "label": "Shadow View Pilot", "has_resolution": False, "default_resolution": 0},
    {"type": 28, "label": "Shadow View Gunner", "has_resolution": False, "default_resolution": 0},
    {"type": 29, "label": "Wreckage", "has_resolution": False, "default_resolution": 0},
    {"type": 30, "label": "Underground", "has_resolution": False, "default_resolution": 0},
    {"type": 31, "label": "GroundLayer", "has_resolution": False, "default_resolution": 0},
    {"type": 32, "label": "Navigation", "has_resolution": False, "default_resolution": 0},
]
LOD_TYPE_NAMES = {definition["type"]: definition["label"] for definition in LOD_DEFINITIONS}
LOD_DEFINITIONS_BY_LABEL = {definition["label"]: definition for definition in LOD_DEFINITIONS}


def _plugin_path():
    candidates = [
        SCRIPT_PATH.parent.parent / "plug-ins" / "MayaObjectBuilder.mll",
        SCRIPT_PATH.parents[1] / "build" / "Release" / "MayaObjectBuilder.mll",
        SCRIPT_PATH.parents[1] / "build" / "Debug" / "MayaObjectBuilder.mll",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def _ensure_script_path():
    scripts_dir = str(SCRIPT_PATH.parent).replace("\\", "/")
    mel.eval('if (!stringArrayContains("' + scripts_dir + '", stringToStringArray(`getenv MAYA_SCRIPT_PATH`, ";"))) putenv MAYA_SCRIPT_PATH (`getenv MAYA_SCRIPT_PATH` + ";' + scripts_dir + '")')
    mel.eval('source "' + scripts_dir + '/mayaObjectBuilderP3DOptions.mel"')


def load_plugin():
    _ensure_script_path()
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        return
    path = _plugin_path()
    if path.exists():
        cmds.loadPlugin(str(path))
    else:
        selected = cmds.fileDialog2(fileMode=1, caption="Load MayaObjectBuilder.mll")
        if selected:
            cmds.loadPlugin(selected[0])


def import_p3d():
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("Import")')
    selected = cmds.fileDialog2(fileMode=1, caption="Import P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.file(selected[0], i=True, type=TRANSLATOR_NAME, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")
        _refresh_context_ui()


def export_p3d():
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("ExportAll")')
    selected = cmds.fileDialog2(fileMode=0, caption="Export P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.file(rename=selected[0])
        cmds.file(exportAll=True, force=True, type=TRANSLATOR_NAME)


def import_model_cfg():
    load_plugin()
    selected = cmds.fileDialog2(fileMode=1, caption="Import model.cfg", fileFilter="Config (*.cfg)")
    if selected:
        cmds.a3obImportModelCfg(path=selected[0])


def export_model_cfg():
    load_plugin()
    selected = cmds.fileDialog2(fileMode=0, caption="Export model.cfg", fileFilter="Config (*.cfg)")
    if selected:
        cmds.a3obExportModelCfg(path=selected[0])


def _prompt(title, message, default=""):
    result = cmds.promptDialog(title=title, message=message, text=str(default), button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    if result != "OK":
        return None
    return cmds.promptDialog(query=True, text=True)


def _selected_lod_definition():
    if not cmds.optionMenu(LOD_TYPE_MENU, exists=True):
        return LOD_DEFINITIONS[0]
    label = cmds.optionMenu(LOD_TYPE_MENU, query=True, value=True)
    return LOD_DEFINITIONS_BY_LABEL.get(label, LOD_DEFINITIONS[0])


def _lod_resolution_value(definition):
    if not definition["has_resolution"]:
        return definition["default_resolution"]
    if cmds.intField(LOD_RESOLUTION_FIELD, exists=True):
        return cmds.intField(LOD_RESOLUTION_FIELD, query=True, value=True)
    return definition["default_resolution"]


def _lod_assignment_label(definition=None, resolution=None):
    definition = definition or _selected_lod_definition()
    resolution = _lod_resolution_value(definition) if resolution is None else resolution
    if definition["has_resolution"]:
        return f"{definition['label']} {resolution}"
    return definition["label"]


def _refresh_lod_assignment_ui(*_):
    if not cmds.optionMenu(LOD_TYPE_MENU, exists=True):
        return
    definition = _selected_lod_definition()
    if cmds.intField(LOD_RESOLUTION_FIELD, exists=True):
        cmds.intField(LOD_RESOLUTION_FIELD, edit=True, enable=definition["has_resolution"])
        if not definition["has_resolution"]:
            cmds.intField(LOD_RESOLUTION_FIELD, edit=True, value=definition["default_resolution"])
    selected_lod = _selected_lod_transform()
    target = selected_lod or "No LOD selected; Create Empty LOD will create a new transform."
    if cmds.text(LOD_CONTEXT_TEXT, exists=True):
        cmds.text(LOD_CONTEXT_TEXT, edit=True, label=f"Target: {target}")
    if cmds.text(LOD_PREVIEW_TEXT, exists=True):
        cmds.text(LOD_PREVIEW_TEXT, edit=True, label=f"Will assign: {_lod_assignment_label(definition)}")


def _lod_node_name(definition, resolution):
    label = _lod_assignment_label(definition, resolution)
    return label.replace(" ", "_").replace("/", "_")


def assign_lod_to_selection():
    load_plugin()
    if not cmds.ls(selection=True):
        cmds.warning("Select a transform, mesh, or component before assigning LOD metadata")
        return
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


def set_mass():
    load_plugin()
    action = cmds.confirmDialog(title="Set Mass", message="Set or clear mass values?", button=["Set", "Clear", "Cancel"], defaultButton="Set", cancelButton="Cancel", dismissString="Cancel")
    if action == "Clear":
        cmds.a3obSetMass(clear=True)
    elif action == "Set":
        value = _prompt("Set Mass", "Mass value:", "1.0")
        if value is not None:
            mode = cmds.confirmDialog(title="Set Mass", message="Apply only to selected vertices?", button=["Selected", "All", "Cancel"], defaultButton="All", cancelButton="Cancel", dismissString="Cancel")
            if mode != "Cancel":
                cmds.a3obSetMass(value=float(value), selectedComponents=(mode == "Selected"))


def set_material():
    load_plugin()
    open_dock()


def set_flag():
    load_plugin()
    component = cmds.confirmDialog(title="Set Flag", message="Component type:", button=["Face", "Vertex", "Cancel"], defaultButton="Face", cancelButton="Cancel", dismissString="Cancel")
    if component == "Cancel":
        return
    value = _prompt("Set Flag", "Flag value:", "1")
    if value is None:
        return
    name = _prompt("Set Flag", "Set name:", "a3ob_flag")
    if name is None:
        return
    cmds.a3obSetFlag(component=component.lower(), value=int(value), name=name)


def apply_mass_from_ui():
    load_plugin()
    value = cmds.floatField(MASS_VALUE_FIELD, query=True, value=True) if cmds.floatField(MASS_VALUE_FIELD, exists=True) else 1.0
    mode = cmds.optionMenu(MASS_MODE_MENU, query=True, value=True) if cmds.optionMenu(MASS_MODE_MENU, exists=True) else "All vertices"
    cmds.a3obSetMass(value=value, selectedComponents=(mode == "Selected vertices"))


def clear_mass_from_ui():
    load_plugin()
    cmds.a3obSetMass(clear=True)


def apply_flag_from_ui():
    load_plugin()
    component_label = cmds.optionMenu(FLAG_COMPONENT_MENU, query=True, value=True) if cmds.optionMenu(FLAG_COMPONENT_MENU, exists=True) else "Face"
    value = cmds.intField(FLAG_VALUE_FIELD, query=True, value=True) if cmds.intField(FLAG_VALUE_FIELD, exists=True) else 1
    name = cmds.textField(FLAG_NAME_FIELD, query=True, text=True).strip() if cmds.textField(FLAG_NAME_FIELD, exists=True) else "a3ob_flag"
    if not name:
        cmds.warning("Enter a flag set name")
        return
    cmds.a3obSetFlag(component=component_label.lower(), value=value, name=name)


def create_proxy_from_ui():
    load_plugin()
    path = cmds.textField(PROXY_PATH_FIELD, query=True, text=True).strip() if cmds.textField(PROXY_PATH_FIELD, exists=True) else ""
    if not path:
        cmds.warning("Enter a proxy path")
        return
    index = cmds.intField(PROXY_INDEX_FIELD, query=True, value=True) if cmds.intField(PROXY_INDEX_FIELD, exists=True) else 1
    from_selection = cmds.checkBox(PROXY_FROM_SELECTION_CHECK, query=True, value=True) if cmds.checkBox(PROXY_FROM_SELECTION_CHECK, exists=True) else True
    cmds.a3obProxy(path=path, index=index, fromSelection=from_selection, update=True)


def _set_lod_label(node):
    raw = node.split(":")[-1]
    for marker in ("_SEL_", "_VERTEX_FLAG_", "_FACE_FLAG_"):
        if marker in raw:
            base = raw.split(marker)[0]
            if base.startswith("Resolution_"):
                return "Resolution " + base.rsplit("_", 1)[-1]
            return base.replace("_", " ")
    return "Other"


def _set_kind(is_proxy, flag_component):
    if is_proxy:
        return "Proxy"
    if flag_component == "vertex":
        return "Vertex Flag"
    if flag_component == "face":
        return "Face Flag"
    return "Selection"


def _node_exists(node):
    return bool(node) and cmds.objExists(node)


def _attr_exists(node, attr):
    return _node_exists(node) and cmds.attributeQuery(attr, node=node, exists=True)


def _safe_get_attr(node, attr, default=None):
    if not _attr_exists(node, attr):
        return default
    value = cmds.getAttr(f"{node}.{attr}")
    return default if value is None else value


def _valid_nodes(nodes):
    return [node for node in nodes if _node_exists(node)]


def _live_set_members(set_node):
    if not _node_exists(set_node):
        return []
    members = cmds.sets(set_node, query=True) or []
    live_members = []
    for member in members:
        expanded = cmds.ls(member, flatten=True) or []
        live_members.extend(item for item in expanded if _node_exists(item.split(".", 1)[0]))
    return live_members


def _clear_selection_manager_state(message="Select a row to see details."):
    if cmds.text(SELECTION_MANAGER_DETAILS, exists=True):
        cmds.text(SELECTION_MANAGER_DETAILS, edit=True, label=message)


def _selection_sets():
    sets = []
    for node in cmds.ls(type="objectSet") or []:
        if not _attr_exists(node, "a3obSelectionName"):
            continue
        name = _safe_get_attr(node, "a3obSelectionName", "") or ""
        is_proxy = bool(_safe_get_attr(node, "a3obIsProxySelection", False))
        flag_component = _safe_get_attr(node, "a3obFlagComponent", "") or ""
        lod = _set_lod_label(node)
        sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod, "members": len(_live_set_members(node))})
    return sorted(sets, key=lambda item: (item["lod"].lower(), item["kind"], item["name"].lower(), item["node"].lower()))


def _selected_selection_set():
    selected = cmds.textScrollList(SELECTION_MANAGER_LIST, query=True, selectItem=True) or []
    if not selected:
        return None
    item = _selection_manager_items.get(selected[0])
    set_node = item["node"] if item else None
    if not _node_exists(set_node):
        if selected[0] in _selection_manager_items:
            del _selection_manager_items[selected[0]]
        return None
    return set_node


def _update_selection_details():
    if not cmds.text(SELECTION_MANAGER_DETAILS, exists=True):
        return
    set_node = _selected_selection_set()
    if not set_node:
        _clear_selection_manager_state()
        return
    members = _live_set_members(set_node)
    name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
    flag_component = _safe_get_attr(set_node, "a3obFlagComponent", "") or ""
    is_proxy = bool(_safe_get_attr(set_node, "a3obIsProxySelection", False))
    details = f"LOD: {_set_lod_label(set_node)}    Type: {_set_kind(is_proxy, flag_component)}    OB name: {name}    Members: {len(members)}\nMaya set: {set_node}"
    cmds.text(SELECTION_MANAGER_DETAILS, edit=True, label=details)


def _refresh_lod_filter(items):
    if not cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, exists=True):
        return
    current = cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, query=True, value=True)
    cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, edit=True, deleteAllItems=True)
    cmds.menuItem(label="All LODs", parent=SELECTION_MANAGER_LOD_FILTER)
    lods = sorted({item["lod"] for item in items})
    for lod in lods:
        cmds.menuItem(label=lod, parent=SELECTION_MANAGER_LOD_FILTER)
    if current in ["All LODs", *lods]:
        cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, edit=True, value=current)


def _refresh_selection_manager(rebuild_lods=True):
    global _selection_manager_items
    if not cmds.textScrollList(SELECTION_MANAGER_LIST, exists=True):
        return
    items = _selection_sets()
    if rebuild_lods:
        _refresh_lod_filter(items)
    lod_filter = cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, query=True, value=True) if cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, exists=True) else "All LODs"
    type_filter = cmds.optionMenu(SELECTION_MANAGER_TYPE_FILTER, query=True, value=True) if cmds.optionMenu(SELECTION_MANAGER_TYPE_FILTER, exists=True) else "All Types"
    search = (cmds.textField(SELECTION_MANAGER_SEARCH, query=True, text=True) if cmds.textField(SELECTION_MANAGER_SEARCH, exists=True) else "").lower()
    selected = cmds.textScrollList(SELECTION_MANAGER_LIST, query=True, selectItem=True) or []
    selected_label = selected[0] if selected else ""
    cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, removeAll=True)
    _selection_manager_items = {}
    for item in items:
        if lod_filter != "All LODs" and item["lod"] != lod_filter:
            continue
        if type_filter != "All Types" and item["kind"] != type_filter:
            continue
        searchable = f"{item['lod']} {item['kind']} {item['name']} {item['node']}".lower()
        if search and search not in searchable:
            continue
        label = f"{item['lod']} | {item['kind']} | {item['name']} | {item['node']}"
        _selection_manager_items[label] = item
        cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, append=label)
    if selected_label in _selection_manager_items:
        cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, selectItem=selected_label)
    else:
        _clear_selection_manager_state()
    _update_selection_details()


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
    node_name = set_node.split(":")[-1]
    prefix = node_name.split("_SEL_")[0] if "_SEL_" in node_name else node_name
    cmds.rename(set_node, prefix + "_SEL_" + new_name.replace(" ", "_"))
    _refresh_selection_manager()


def _create_selection_set():
    selection = cmds.ls(selection=True, flatten=True) or []
    if not selection:
        cmds.warning("Select mesh components before creating an Object Builder selection")
        return
    name = _prompt("Create Selection", "Object Builder selection name:", "camo")
    if not name:
        return
    set_node = cmds.sets(selection, name="a3ob_SEL_" + name.replace(" ", "_"))
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", name, type="string")
    _refresh_selection_manager()


def _add_to_selection_set():
    set_node = _selected_selection_set()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not set_node or not selection:
        cmds.warning("Select a live selection set and mesh components to add")
        _refresh_selection_manager(False)
        return
    cmds.sets(selection, add=set_node)
    _refresh_selection_manager()


def _remove_from_selection_set():
    set_node = _selected_selection_set()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not set_node or not selection:
        cmds.warning("Select a live selection set and mesh components to remove")
        _refresh_selection_manager(False)
        return
    cmds.sets(selection, remove=set_node)
    _refresh_selection_manager()


def _lod_label(node):
    if _attr_exists(node, "a3obLodType"):
        lod_type = _safe_get_attr(node, "a3obLodType", 0)
        resolution = _safe_get_attr(node, "a3obResolution", 0)
        name = LOD_TYPE_NAMES.get(lod_type, "LOD")
        suffix = f" {resolution}" if lod_type == 0 else ""
        return f"{name}{suffix}  |  {node}"
    return node


def _is_lod_transform(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery("a3obIsLOD", node=node, exists=True)


def _lod_transforms():
    return [node for node in cmds.ls(type="transform") or [] if _is_lod_transform(node)]


def _selected_lod_transform():
    for node in cmds.ls(selection=True, long=True) or []:
        current = node
        while current:
            if _is_lod_transform(current):
                return current
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            current = parents[0] if parents else ""
    return None


def _ensure_string_attr(node, attr, short_name):
    if not _node_exists(node):
        return False
    if not _attr_exists(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, dataType="string")
    return True


def _split_named_properties(raw):
    properties = []
    for part in (raw or "").split(";"):
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        properties.append((name.strip(), value.strip()))
    return properties


def _join_named_properties(properties):
    return ";".join(f"{name}={value}" for name, value in properties if name)


def _option_menu_value(control):
    if not cmds.optionMenu(control, exists=True):
        return ""
    items = cmds.optionMenu(control, query=True, itemListLong=True) or []
    if not items:
        return ""
    return cmds.optionMenu(control, query=True, value=True)


def _selected_named_property_lod():
    selected = _selected_lod_transform()
    if selected:
        return selected
    lod = _named_property_lods.get(_option_menu_value(NAMED_PROPERTIES_LOD))
    if _node_exists(lod):
        return lod
    _refresh_named_property_lods()
    lod = _named_property_lods.get(_option_menu_value(NAMED_PROPERTIES_LOD))
    return lod if _node_exists(lod) else None


def _refresh_named_property_lods():
    global _named_property_lods
    if not cmds.optionMenu(NAMED_PROPERTIES_LOD, exists=True):
        return
    current = _option_menu_value(NAMED_PROPERTIES_LOD)
    cmds.optionMenu(NAMED_PROPERTIES_LOD, edit=True, deleteAllItems=True)
    _named_property_lods = {}
    for lod in _lod_transforms():
        label = _lod_label(lod)
        _named_property_lods[label] = lod
        cmds.menuItem(label=label, parent=NAMED_PROPERTIES_LOD)
    labels = list(_named_property_lods)
    if not labels:
        cmds.menuItem(label="No Object Builder LODs", parent=NAMED_PROPERTIES_LOD, enable=False)
    elif current in _named_property_lods:
        cmds.optionMenu(NAMED_PROPERTIES_LOD, edit=True, value=current)
    else:
        cmds.optionMenu(NAMED_PROPERTIES_LOD, edit=True, value=labels[0])


def _refresh_named_properties(rebuild_lods=False):
    global _named_property_items
    if rebuild_lods:
        _refresh_named_property_lods()
    if not cmds.textScrollList(NAMED_PROPERTIES_LIST, exists=True):
        return
    cmds.textScrollList(NAMED_PROPERTIES_LIST, edit=True, removeAll=True)
    _named_property_items = {}
    lod = _selected_named_property_lod()
    if not lod:
        if cmds.textField(NAMED_PROPERTIES_NAME, exists=True):
            cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text="")
        if cmds.textField(NAMED_PROPERTIES_VALUE, exists=True):
            cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text="")
        return
    for label, node in _named_property_lods.items():
        if node == lod and _option_menu_value(NAMED_PROPERTIES_LOD) != label:
            cmds.optionMenu(NAMED_PROPERTIES_LOD, edit=True, value=label)
            break
    raw = _safe_get_attr(lod, "a3obProperties", "") or ""
    for name, value in _split_named_properties(raw):
        label = f"{name} = {value}"
        _named_property_items[label] = (name, value)
        cmds.textScrollList(NAMED_PROPERTIES_LIST, edit=True, append=label)


def _select_named_property():
    selected = cmds.textScrollList(NAMED_PROPERTIES_LIST, query=True, selectItem=True) or []
    if not selected:
        return
    name, value = _named_property_items.get(selected[0], ("", ""))
    cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text=name)
    cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text=value)


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
    name = cmds.textField(NAMED_PROPERTIES_NAME, query=True, text=True).strip()
    value = cmds.textField(NAMED_PROPERTIES_VALUE, query=True, text=True).strip()
    _set_named_property_value(name, value)


def _remove_named_property():
    lod = _selected_named_property_lod()
    name = cmds.textField(NAMED_PROPERTIES_NAME, query=True, text=True).strip()
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
    cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text="")
    cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text="")
    _refresh_named_properties()


def _apply_common_named_property(*_):
    selected = _option_menu_value(NAMED_PROPERTIES_COMMON)
    for name, value in COMMON_NAMED_PROPERTIES:
        label = f"{name} = {value}"
        if selected == label:
            cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text=name)
            cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text=value)
            _set_named_property_value(name, value)
            return


def _build_named_properties_ui():
    _section("Named Properties", "Edit Object Builder named properties on the selected LOD.")
    _labeled_row("LOD", lambda: cmds.optionMenu(NAMED_PROPERTIES_LOD, changeCommand=lambda *_: _refresh_named_properties(False)))
    _labeled_row("Preset", lambda: cmds.optionMenu(NAMED_PROPERTIES_COMMON, changeCommand=_apply_common_named_property))
    for name, value in COMMON_NAMED_PROPERTIES:
        cmds.menuItem(label=f"{name} = {value}", parent=NAMED_PROPERTIES_COMMON)
    cmds.textScrollList(NAMED_PROPERTIES_LIST, allowMultiSelection=False, height=96, selectCommand=lambda *_: _select_named_property())
    _labeled_row("Name", lambda: cmds.textField(NAMED_PROPERTIES_NAME, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields))
    _labeled_row("Value", lambda: cmds.textField(NAMED_PROPERTIES_VALUE, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields))
    _button_stack([
        ("Add / Update Property", _commit_named_property_fields),
        ("Remove Selected Property", _remove_named_property),
    ])
    _end_section()
    _refresh_named_properties(True)


def _mesh_shapes_from_selection():
    shapes = []
    seen = set()
    for item in cmds.ls(selection=True, flatten=True, long=True) or []:
        node = item.split(".", 1)[0]
        if not cmds.objExists(node):
            continue
        candidates = []
        if cmds.objectType(node, isType="mesh"):
            candidates.append(node)
        else:
            candidates.extend(cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or [])
            descendants = cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []
            candidates.extend(descendants)
        for shape in candidates:
            if shape not in seen:
                seen.add(shape)
                shapes.append(shape)
    return shapes


def _material_nodes_for_selection():
    nodes = []
    seen = set()
    for shape in _mesh_shapes_from_selection():
        shading_groups = _valid_nodes(cmds.listConnections(shape, type="shadingEngine") or [])
        for shading_group in shading_groups:
            if shading_group in {"initialShadingGroup", "initialParticleSE"} or shading_group in seen:
                continue
            seen.add(shading_group)
            materials = _valid_nodes(cmds.ls(cmds.listConnections(shading_group + ".surfaceShader") or [], materials=True) or [])
            material_node = materials[0] if materials else ""
            texture = ""
            material = ""
            for candidate in _valid_nodes([shading_group, material_node]):
                if not texture:
                    texture = _safe_get_attr(candidate, "a3obTexture", "") or ""
                if not material:
                    material = _safe_get_attr(candidate, "a3obMaterial", "") or ""
            nodes.append({"material_node": material_node, "shading_groups": [shading_group], "texture": texture, "material": material})
    return sorted(nodes, key=lambda item: ((item["material_node"] or "").lower(), item["shading_groups"][0].lower()))


def _refresh_material_metadata():
    global _material_metadata_items
    if not cmds.textScrollList(MATERIAL_METADATA_LIST, exists=True):
        return
    cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, removeAll=True)
    _material_metadata_items = {}
    items = _material_nodes_for_selection()
    if not items:
        cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, append="Select a mesh, LOD, or faces to edit its DayZ materials")
        return
    for item in items:
        material_node = item["material_node"] or "No material"
        shading_group = item["shading_groups"][0]
        label = f"{material_node} | {shading_group} | tex: {item['texture']} | rvmat: {item['material']}"
        _material_metadata_items[label] = item
        cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, append=label)


def _selected_material_metadata_item():
    selected = cmds.textScrollList(MATERIAL_METADATA_LIST, query=True, selectItem=True) or []
    if not selected:
        return None
    item = _material_metadata_items.get(selected[0])
    if not item:
        return None
    if not _node_exists(item["material_node"]) and not _valid_nodes(item["shading_groups"]):
        _refresh_material_metadata()
        return None
    item["shading_groups"] = _valid_nodes(item["shading_groups"])
    return item


def _select_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        return
    cmds.textField(MATERIAL_METADATA_TEXTURE, edit=True, text=item["texture"])
    cmds.textField(MATERIAL_METADATA_MATERIAL, edit=True, text=item["material"])


def _set_material_metadata_on_node(node, texture, material):
    if not _node_exists(node):
        return False
    if not _ensure_string_attr(node, "a3obTexture", "a3tx") or not _ensure_string_attr(node, "a3obMaterial", "a3mt"):
        return False
    cmds.setAttr(node + ".a3obTexture", texture, type="string")
    cmds.setAttr(node + ".a3obMaterial", material, type="string")
    return True


def _commit_selected_material_metadata(*_):
    item = _selected_material_metadata_item()
    if not item:
        return
    texture = cmds.textField(MATERIAL_METADATA_TEXTURE, query=True, text=True).strip()
    material = cmds.textField(MATERIAL_METADATA_MATERIAL, query=True, text=True).strip()
    changed = False
    if _node_exists(item["material_node"]):
        changed = _set_material_metadata_on_node(item["material_node"], texture, material) or changed
    for shading_group in item["shading_groups"]:
        changed = _set_material_metadata_on_node(shading_group, texture, material) or changed
    if not changed:
        cmds.warning("Material metadata target was deleted")
    _refresh_material_metadata()


def _assign_new_material_metadata_to_selection():
    texture = cmds.textField(MATERIAL_METADATA_TEXTURE, query=True, text=True).strip()
    material = cmds.textField(MATERIAL_METADATA_MATERIAL, query=True, text=True).strip()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not selection:
        cmds.warning("Select mesh faces before assigning a new DayZ material")
        return
    cmds.a3obSetMaterial(texture=texture, material=material)
    _refresh_material_metadata()


def _clear_selected_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        cmds.warning("Select a Maya material row to clear")
        return
    changed = False
    for node in _valid_nodes([item["material_node"]] + item["shading_groups"]):
        if _attr_exists(node, "a3obTexture"):
            cmds.setAttr(node + ".a3obTexture", "", type="string")
            changed = True
        if _attr_exists(node, "a3obMaterial"):
            cmds.setAttr(node + ".a3obMaterial", "", type="string")
            changed = True
    if not changed:
        cmds.warning("Material metadata target was deleted")
    _refresh_material_metadata()


def _build_material_metadata_ui():
    _section("DayZ Material / Texture Metadata", "Shows only materials used by the selected mesh, LOD, or faces.")
    cmds.textScrollList(MATERIAL_METADATA_LIST, allowMultiSelection=False, height=150, selectCommand=lambda *_: _select_material_metadata())
    _labeled_row("Texture", lambda: cmds.textField(MATERIAL_METADATA_TEXTURE, changeCommand=_commit_selected_material_metadata, enterCommand=_commit_selected_material_metadata))
    _labeled_row("Material", lambda: cmds.textField(MATERIAL_METADATA_MATERIAL, changeCommand=_commit_selected_material_metadata, enterCommand=_commit_selected_material_metadata))
    _button_stack([
        ("Assign New To Selected Faces", _assign_new_material_metadata_to_selection),
        ("Clear Highlighted Material", _clear_selected_material_metadata),
    ])
    _end_section()
    _refresh_material_metadata()


def _build_selection_manager_ui():
    _section("Selections", "Manage Object Builder selections, proxies, and flag sets.")
    _labeled_row("LOD", lambda: cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False)))
    cmds.menuItem(label="All LODs", parent=SELECTION_MANAGER_LOD_FILTER)
    _labeled_row("Type", lambda: cmds.optionMenu(SELECTION_MANAGER_TYPE_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False)))
    for label in ("All Types", "Selection", "Proxy", "Vertex Flag", "Face Flag"):
        cmds.menuItem(label=label, parent=SELECTION_MANAGER_TYPE_FILTER)
    _labeled_row("Search", lambda: cmds.textField(SELECTION_MANAGER_SEARCH, changeCommand=lambda *_: _refresh_selection_manager(False), enterCommand=lambda *_: _refresh_selection_manager(False)))
    cmds.textScrollList(SELECTION_MANAGER_LIST, allowMultiSelection=False, height=135, selectCommand=lambda *_: _update_selection_details(), doubleClickCommand=lambda *_: _select_set_members())
    cmds.text(SELECTION_MANAGER_DETAILS, label="Select a row to see details.", align="left", wordWrap=True)
    _compact_button_stack([
        ("Select Members", _select_set_members),
        ("Rename Selection Set", _rename_selection_set),
        ("Create From Selection", _create_selection_set),
        ("Add Selected Components", _add_to_selection_set),
        ("Remove Selected Components", _remove_from_selection_set),
    ])
    _end_section()


def selection_manager():
    open_dock()


def _refresh_context_ui():
    if cmds.textScrollList(NAMED_PROPERTIES_LIST, exists=True):
        _refresh_named_properties()
    if cmds.textScrollList(MATERIAL_METADATA_LIST, exists=True):
        _refresh_material_metadata()
    if cmds.textScrollList(SELECTION_MANAGER_LIST, exists=True):
        _refresh_selection_manager(False)
    if cmds.text(LOD_CONTEXT_TEXT, exists=True):
        _refresh_lod_assignment_ui()


def _install_context_refresh_job(parent):
    global _ui_script_jobs
    _ui_script_jobs = [job for job in _ui_script_jobs if cmds.scriptJob(exists=job)]
    for event in ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened"):
        job = cmds.scriptJob(event=[event, _refresh_context_ui], parent=parent, protected=True)
        _ui_script_jobs.append(job)



def _action_button(label, command):
    return cmds.button(label=label, height=32, command=lambda *_: command())


def _button_stack(items):
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    for label, command in items:
        _action_button(label, command)
    cmds.setParent("..")


def _compact_button_stack(items):
    cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
    for label, command in items:
        cmds.button(label=label, height=28, command=lambda *_, fn=command: fn())
    cmds.setParent("..")


def _button_pair(items):
    _button_stack(items)


def _two_column_buttons(items):
    _button_stack(items)


def _full_width_button(label, command):
    return _action_button(label, command)


def _labeled_row(label, control_builder):
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(96, 1), adjustableColumn=2, columnAttach=[(1, "right", 0), (2, "both", 6)])
    cmds.text(label=label, align="right")
    result = control_builder()
    cmds.setParent("..")
    return result


def _section(label, subtitle="", collapse=False):
    cmds.frameLayout(label=label, collapsable=True, collapse=collapse, marginWidth=10, marginHeight=8)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=7)
    if subtitle:
        cmds.text(label=subtitle, align="left", wordWrap=True)


def _end_section():
    cmds.setParent("..")
    cmds.setParent("..")


def _start_tab():
    tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    return tab


def _end_tab():
    cmds.setParent("..")
    cmds.setParent("..")


def _build_lod_assignment_ui():
    _section("LOD Assignment", "Select an Object Builder LOD type and assign it to the current transform or create an empty LOD.")
    cmds.text(LOD_CONTEXT_TEXT, label="Target: No Object Builder LOD selected.", align="left")
    _labeled_row("LOD type", lambda: cmds.optionMenu(LOD_TYPE_MENU, changeCommand=_refresh_lod_assignment_ui))
    for definition in LOD_DEFINITIONS:
        cmds.menuItem(label=definition["label"], parent=LOD_TYPE_MENU)
    _labeled_row("Resolution", lambda: cmds.intField(LOD_RESOLUTION_FIELD, minValue=0, value=1, changeCommand=_refresh_lod_assignment_ui))
    cmds.text(LOD_PREVIEW_TEXT, label="Will assign: Resolution 1", align="left")
    _full_width_button("Assign LOD to Selection", assign_lod_to_selection)
    _full_width_button("Create Empty LOD", create_empty_lod)
    _end_section()
    _refresh_lod_assignment_ui()


def _build_metadata_tools_ui():
    _section("Mass", "Apply or clear vertex mass metadata on the current selection.")
    _labeled_row("Value", lambda: cmds.floatField(MASS_VALUE_FIELD, value=1.0, precision=3))
    _labeled_row("Mode", lambda: cmds.optionMenu(MASS_MODE_MENU))
    cmds.menuItem(label="All vertices", parent=MASS_MODE_MENU)
    cmds.menuItem(label="Selected vertices", parent=MASS_MODE_MENU)
    _button_stack([
        ("Apply Mass", apply_mass_from_ui),
        ("Clear Mass", clear_mass_from_ui),
    ])
    _end_section()

    _section("Flags", "Create Object Builder face or vertex flag sets from the current selection.")
    _labeled_row("Component", lambda: cmds.optionMenu(FLAG_COMPONENT_MENU))
    cmds.menuItem(label="Face", parent=FLAG_COMPONENT_MENU)
    cmds.menuItem(label="Vertex", parent=FLAG_COMPONENT_MENU)
    _labeled_row("Value", lambda: cmds.intField(FLAG_VALUE_FIELD, value=1))
    _labeled_row("Set name", lambda: cmds.textField(FLAG_NAME_FIELD, text="a3ob_flag"))
    _full_width_button("Apply Flag", apply_flag_from_ui)
    _end_section()

    _section("Proxy", "Create or update proxy metadata without modal prompts.")
    _labeled_row("Path", lambda: cmds.textField(PROXY_PATH_FIELD))
    _labeled_row("Index", lambda: cmds.intField(PROXY_INDEX_FIELD, minValue=0, value=1))
    cmds.checkBox(PROXY_FROM_SELECTION_CHECK, label="Create from selected components", value=True)
    _full_width_button("Create Proxy", create_proxy_from_ui)
    _end_section()

    _build_named_properties_ui()


def _build_validation_ui():
    _section("Validation", "Check scene or selected LODs before export.")
    _two_column_buttons([
        ("Validate Scene", lambda: cmds.a3obValidate()),
        ("Validate Selection", lambda: cmds.a3obValidate(selectionOnly=True)),
    ])
    _end_section()


def _build_dock_contents():
    _ensure_script_path()
    tabs = cmds.tabLayout(innerMarginWidth=8, innerMarginHeight=8)

    lod_tab = _start_tab()
    cmds.text(label="MayaObjectBuilder", align="center", height=28)
    _build_lod_assignment_ui()
    _build_validation_ui()
    _end_tab()

    files_tab = _start_tab()
    _section("P3D", "Use Maya File > Import / Export and choose file type Arma P3D. P3D options live in Maya's file dialog option panel.", collapse=True)
    _end_section()
    _section("model.cfg", "Import or export Object Builder skeleton configuration.")
    _two_column_buttons([
        ("Import model.cfg", import_model_cfg),
        ("Export model.cfg", export_model_cfg),
    ])
    _end_section()
    _end_tab()

    metadata_tab = _start_tab()
    _build_metadata_tools_ui()
    _end_tab()

    materials_tab = _start_tab()
    _build_material_metadata_ui()
    _end_tab()

    selections_tab = _start_tab()
    _build_selection_manager_ui()
    _end_tab()

    validation_tab = _start_tab()
    _build_validation_ui()
    _end_tab()

    cmds.tabLayout(tabs, edit=True, tabLabel=[
        (lod_tab, "LOD"),
        (files_tab, "Files"),
        (metadata_tab, "Metadata"),
        (materials_tab, "Materials"),
        (selections_tab, "Selections"),
        (validation_tab, "Validation"),
    ])
    cmds.setParent("..")
    _refresh_selection_manager()


def open_dock():
    if cmds.about(batch=True):
        return None
    if cmds.workspaceControl(DOCK_NAME, exists=True):
        cmds.workspaceControl(DOCK_NAME, edit=True, restore=True, visible=True)
        _refresh_context_ui()
        return DOCK_NAME
    control = cmds.workspaceControl(DOCK_NAME, label="MayaObjectBuilder", retain=False, initialWidth=440, minimumWidth=380)
    for target in ("AttributeEditor", "AttributeEditorWorkspaceControl", "ChannelBoxLayerEditor"):
        if cmds.workspaceControl(target, exists=True):
            cmds.workspaceControl(DOCK_NAME, edit=True, tabToControl=(target, -1))
            break
    cmds.setParent(control)
    _build_dock_contents()
    _install_context_refresh_job(control)
    return control


def _kill_ui_script_jobs():
    global _ui_script_jobs
    for job in list(_ui_script_jobs):
        if cmds.scriptJob(exists=job):
            cmds.scriptJob(kill=job, force=True)
    _ui_script_jobs = []


def _remove_legacy_shelf_button():
    button_name = "MayaObjectBuilderShelfOpenButton"
    if cmds.shelfButton(button_name, exists=True):
        cmds.deleteUI(button_name)


def show_plugin_ui():
    if cmds.about(batch=True):
        return None
    _ensure_script_path()
    main_window = mel.eval("$tmp=$gMainWindow")
    if not cmds.menu(MENU_NAME, exists=True):
        menu = cmds.menu(MENU_NAME, label="MayaObjectBuilder", parent=main_window, tearOff=True)
        cmds.menuItem(label="Open MayaObjectBuilder", parent=menu, command=lambda *_: open_dock())
    _remove_legacy_shelf_button()
    return open_dock()


def hide_plugin_ui():
    if cmds.about(batch=True):
        return
    _kill_ui_script_jobs()
    if cmds.workspaceControl(DOCK_NAME, exists=True):
        cmds.deleteUI(DOCK_NAME)
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)
    _remove_legacy_shelf_button()


def create_proxy():
    load_plugin()
    path = _prompt("Create Proxy", "Proxy path:")
    if not path:
        return
    index = _prompt("Create Proxy", "Proxy index:", "1")
    if index is None:
        return
    mode = cmds.confirmDialog(title="Create Proxy", message="Create proxy selection from selected components?", button=["Yes", "No", "Cancel"], defaultButton="Yes", cancelButton="Cancel", dismissString="Cancel")
    if mode == "Cancel":
        return
    cmds.a3obProxy(path=path, index=int(index), fromSelection=(mode == "Yes"), update=True)


def validate():
    load_plugin()
    mode = cmds.confirmDialog(title="Validate", message="Validate selected LODs only?", button=["Selection", "All", "Cancel"], defaultButton="All", cancelButton="Cancel", dismissString="Cancel")
    if mode == "Selection":
        cmds.a3obValidate(selectionOnly=True)
    elif mode == "All":
        cmds.a3obValidate()


def install():
    load_plugin()
    return show_plugin_ui()


def uninstall():
    hide_plugin_ui()


if __name__ == "__main__":
    install()
