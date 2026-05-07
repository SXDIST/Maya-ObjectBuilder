from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


SCRIPT_PATH = Path(globals().get("__file__", r"C:\Users\targaryen\source\repos\maya\dayz-object-builder\scripts\objectBuilderMenu.py")).resolve()
MENU_NAME = "MayaObjectBuilderMenu"
PLUGIN_NAME = "MayaObjectBuilder"
TRANSLATOR_NAME = "Arma P3D"
DOCK_NAME = "MayaObjectBuilderWorkspaceControl"
SHELF_NAME = "MayaObjectBuilderShelf"
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

LOD_TYPE_NAMES = {
    0: "Resolution",
    1: "View Gunner",
    2: "View Pilot",
    3: "View Cargo",
    4: "ShadowVolume",
    5: "Edit",
    6: "Geometry",
    7: "Geometry Buoyancy",
    8: "Geometry PhysX",
    9: "Memory",
    10: "LandContact",
    11: "Roadway",
    12: "Paths",
    13: "HitPoints",
    14: "View Geometry",
    15: "Fire Geometry",
    16: "View Cargo Geometry",
    17: "View Cargo Fire Geometry",
    18: "View Commander",
    19: "View Commander Geometry",
    20: "View Commander Fire Geometry",
    21: "View Pilot Geometry",
    22: "View Pilot Fire Geometry",
    23: "View Gunner Geometry",
    24: "View Gunner Fire Geometry",
    25: "Subparts",
    26: "Shadow View Cargo",
    27: "Shadow View Pilot",
    28: "Shadow View Gunner",
    29: "Wreckage",
    30: "Underground",
    31: "GroundLayer",
    32: "Navigation",
}


def _plugin_path():
    return SCRIPT_PATH.parents[1] / "build" / "Debug" / "MayaObjectBuilder.mll"


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


def create_lod():
    load_plugin()
    name = _prompt("Create LOD", "Name:", "a3ob_LOD")
    if name is None:
        return
    lod_type = _prompt("Create LOD", "LOD type:", "1")
    if lod_type is None:
        return
    resolution = _prompt("Create LOD", "Resolution:", "0")
    if resolution is None:
        return
    cmds.a3obCreateLOD(lodType=int(lod_type), resolution=int(resolution), name=name)


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


def _selection_sets():
    sets = []
    for node in cmds.ls(type="objectSet") or []:
        if cmds.attributeQuery("a3obSelectionName", node=node, exists=True):
            name = cmds.getAttr(node + ".a3obSelectionName") or ""
            is_proxy = cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True) and cmds.getAttr(node + ".a3obIsProxySelection")
            flag_component = cmds.getAttr(node + ".a3obFlagComponent") if cmds.attributeQuery("a3obFlagComponent", node=node, exists=True) else ""
            lod = _set_lod_label(node)
            sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod})
    return sorted(sets, key=lambda item: (item["lod"].lower(), item["kind"], item["name"].lower(), item["node"].lower()))


def _selected_selection_set():
    selected = cmds.textScrollList(SELECTION_MANAGER_LIST, query=True, selectItem=True) or []
    if not selected:
        return None
    item = _selection_manager_items.get(selected[0])
    return item["node"] if item else None


def _update_selection_details():
    if not cmds.text(SELECTION_MANAGER_DETAILS, exists=True):
        return
    set_node = _selected_selection_set()
    if not set_node:
        cmds.text(SELECTION_MANAGER_DETAILS, edit=True, label="Select a row to see details.")
        return
    members = cmds.sets(set_node, query=True) or []
    name = cmds.getAttr(set_node + ".a3obSelectionName") or ""
    flag_component = cmds.getAttr(set_node + ".a3obFlagComponent") if cmds.attributeQuery("a3obFlagComponent", node=set_node, exists=True) else ""
    is_proxy = cmds.attributeQuery("a3obIsProxySelection", node=set_node, exists=True) and cmds.getAttr(set_node + ".a3obIsProxySelection")
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
        label = f"{item['lod']:<18} | {item['kind']:<11} | {item['name']:<24} | {item['node']}"
        _selection_manager_items[label] = item
        cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, append=label)
    _update_selection_details()


def _select_set_members():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a selection set in the MayaObjectBuilder Selection Manager")
        return
    members = cmds.sets(set_node, query=True) or []
    cmds.select(members, replace=True)


def _rename_selection_set():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a selection set in the MayaObjectBuilder Selection Manager")
        return
    old_name = cmds.getAttr(set_node + ".a3obSelectionName") or ""
    new_name = _prompt("Rename Selection", "Object Builder selection name:", old_name)
    if not new_name:
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
        cmds.warning("Select a selection set and mesh components to add")
        return
    cmds.sets(selection, add=set_node)
    _refresh_selection_manager()


def _remove_from_selection_set():
    set_node = _selected_selection_set()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not set_node or not selection:
        cmds.warning("Select a selection set and mesh components to remove")
        return
    cmds.sets(selection, remove=set_node)
    _refresh_selection_manager()


def _lod_label(node):
    if cmds.attributeQuery("a3obLodType", node=node, exists=True):
        lod_type = cmds.getAttr(node + ".a3obLodType")
        resolution = cmds.getAttr(node + ".a3obResolution") if cmds.attributeQuery("a3obResolution", node=node, exists=True) else 0
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
    if not cmds.attributeQuery(attr, node=node, exists=True):
        cmds.addAttr(node, longName=attr, shortName=short_name, dataType="string")


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
    if lod:
        return lod
    _refresh_named_property_lods()
    return _named_property_lods.get(_option_menu_value(NAMED_PROPERTIES_LOD))


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
    lod = _selected_lod_transform() or _named_property_lods.get(_option_menu_value(NAMED_PROPERTIES_LOD))
    if not lod:
        _refresh_named_property_lods()
        lod = _named_property_lods.get(_option_menu_value(NAMED_PROPERTIES_LOD))
    if not lod:
        return
    for label, node in _named_property_lods.items():
        if node == lod and _option_menu_value(NAMED_PROPERTIES_LOD) != label:
            cmds.optionMenu(NAMED_PROPERTIES_LOD, edit=True, value=label)
            break
    raw = cmds.getAttr(lod + ".a3obProperties") if cmds.attributeQuery("a3obProperties", node=lod, exists=True) else ""
    for name, value in _split_named_properties(raw):
        label = f"{name:<24} = {value}"
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
        cmds.warning("Import a P3D or select an Object Builder LOD")
        return False
    name = name.strip()
    value = value.strip()
    if not name:
        return False
    _ensure_string_attr(lod, "a3obProperties", "a3prop")
    existing = _split_named_properties(cmds.getAttr(lod + ".a3obProperties") or "")
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
        cmds.warning("Select a named property to remove")
        return
    _ensure_string_attr(lod, "a3obProperties", "a3prop")
    properties = [(key, val) for key, val in _split_named_properties(cmds.getAttr(lod + ".a3obProperties") or "") if key != name]
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
    cmds.frameLayout(label="Named Properties", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="LOD")
    cmds.optionMenu(NAMED_PROPERTIES_LOD, changeCommand=lambda *_: _refresh_named_properties(False))
    cmds.setParent("..")
    cmds.textScrollList(NAMED_PROPERTIES_LIST, allowMultiSelection=False, height=150, selectCommand=lambda *_: _select_named_property())
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="Name")
    cmds.textField(NAMED_PROPERTIES_NAME, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="Value")
    cmds.textField(NAMED_PROPERTIES_VALUE, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="Common")
    cmds.optionMenu(NAMED_PROPERTIES_COMMON, changeCommand=_apply_common_named_property)
    for name, value in COMMON_NAMED_PROPERTIES:
        cmds.menuItem(label=f"{name} = {value}")
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=1, columnWidth=[(1, 160)])
    cmds.button(label="Remove Selected", command=lambda *_: _remove_named_property())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")
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
        shading_groups = cmds.listConnections(shape, type="shadingEngine") or []
        for shading_group in shading_groups:
            if shading_group in {"initialShadingGroup", "initialParticleSE"} or shading_group in seen:
                continue
            seen.add(shading_group)
            materials = cmds.ls(cmds.listConnections(shading_group + ".surfaceShader") or [], materials=True) or []
            material_node = materials[0] if materials else ""
            texture = ""
            material = ""
            for candidate in [shading_group, material_node]:
                if candidate and not texture and cmds.attributeQuery("a3obTexture", node=candidate, exists=True):
                    texture = cmds.getAttr(candidate + ".a3obTexture") or ""
                if candidate and not material and cmds.attributeQuery("a3obMaterial", node=candidate, exists=True):
                    material = cmds.getAttr(candidate + ".a3obMaterial") or ""
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
        label = f"{material_node:<28} | {shading_group:<28} | tex: {item['texture']} | rvmat: {item['material']}"
        _material_metadata_items[label] = item
        cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, append=label)


def _selected_material_metadata_item():
    selected = cmds.textScrollList(MATERIAL_METADATA_LIST, query=True, selectItem=True) or []
    return _material_metadata_items.get(selected[0]) if selected else None


def _select_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        return
    cmds.textField(MATERIAL_METADATA_TEXTURE, edit=True, text=item["texture"])
    cmds.textField(MATERIAL_METADATA_MATERIAL, edit=True, text=item["material"])


def _set_material_metadata_on_node(node, texture, material):
    _ensure_string_attr(node, "a3obTexture", "a3tx")
    _ensure_string_attr(node, "a3obMaterial", "a3mt")
    cmds.setAttr(node + ".a3obTexture", texture, type="string")
    cmds.setAttr(node + ".a3obMaterial", material, type="string")


def _commit_selected_material_metadata(*_):
    item = _selected_material_metadata_item()
    if not item:
        return
    texture = cmds.textField(MATERIAL_METADATA_TEXTURE, query=True, text=True).strip()
    material = cmds.textField(MATERIAL_METADATA_MATERIAL, query=True, text=True).strip()
    if item["material_node"]:
        _set_material_metadata_on_node(item["material_node"], texture, material)
    for shading_group in item["shading_groups"]:
        _set_material_metadata_on_node(shading_group, texture, material)
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
    for node in [item["material_node"]] + item["shading_groups"]:
        if not node:
            continue
        if cmds.attributeQuery("a3obTexture", node=node, exists=True):
            cmds.setAttr(node + ".a3obTexture", "", type="string")
        if cmds.attributeQuery("a3obMaterial", node=node, exists=True):
            cmds.setAttr(node + ".a3obMaterial", "", type="string")
    _refresh_material_metadata()


def _build_material_metadata_ui():
    cmds.frameLayout(label="DayZ Material / Texture Metadata", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.text(label="Shows only materials used by the selected mesh, LOD, or faces.", align="left")
    cmds.textScrollList(MATERIAL_METADATA_LIST, allowMultiSelection=False, height=170, selectCommand=lambda *_: _select_material_metadata())
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="Texture")
    cmds.textField(MATERIAL_METADATA_TEXTURE, changeCommand=_commit_selected_material_metadata, enterCommand=_commit_selected_material_metadata)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 300), adjustableColumn=2)
    cmds.text(label="Material")
    cmds.textField(MATERIAL_METADATA_MATERIAL, changeCommand=_commit_selected_material_metadata, enterCommand=_commit_selected_material_metadata)
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 195), (2, 195)])
    cmds.button(label="Assign New To Selected Faces", command=lambda *_: _assign_new_material_metadata_to_selection())
    cmds.button(label="Clear Highlighted Material", command=lambda *_: _clear_selected_material_metadata())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")
    _refresh_material_metadata()


def _build_selection_manager_ui():
    cmds.frameLayout(label="Selections", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="LOD")
    cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False))
    cmds.menuItem(label="All LODs")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="Type")
    cmds.optionMenu(SELECTION_MANAGER_TYPE_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False))
    for label in ("All Types", "Selection", "Proxy", "Vertex Flag", "Face Flag"):
        cmds.menuItem(label=label)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="Search")
    cmds.textField(SELECTION_MANAGER_SEARCH, changeCommand=lambda *_: _refresh_selection_manager(False), enterCommand=lambda *_: _refresh_selection_manager(False))
    cmds.setParent("..")
    cmds.textScrollList(SELECTION_MANAGER_LIST, allowMultiSelection=False, height=210, selectCommand=lambda *_: _update_selection_details(), doubleClickCommand=lambda *_: _select_set_members())
    cmds.text(SELECTION_MANAGER_DETAILS, label="Select a row to see details.", align="left")
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    cmds.button(label="Select Members", command=lambda *_: _select_set_members())
    cmds.button(label="Rename", command=lambda *_: _rename_selection_set())
    cmds.button(label="Create From Selection", command=lambda *_: _create_selection_set())
    cmds.button(label="Add Selected Components", command=lambda *_: _add_to_selection_set())
    cmds.button(label="Remove Selected Components", command=lambda *_: _remove_from_selection_set())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def selection_manager():
    open_dock()


def _refresh_context_ui():
    if cmds.textScrollList(NAMED_PROPERTIES_LIST, exists=True):
        _refresh_named_properties()
    if cmds.textScrollList(MATERIAL_METADATA_LIST, exists=True):
        _refresh_material_metadata()
    if cmds.textScrollList(SELECTION_MANAGER_LIST, exists=True):
        _refresh_selection_manager(False)


def _install_context_refresh_job(parent):
    global _ui_script_jobs
    _ui_script_jobs = [job for job in _ui_script_jobs if cmds.scriptJob(exists=job)]
    job = cmds.scriptJob(event=["SelectionChanged", _refresh_context_ui], parent=parent, protected=True)
    _ui_script_jobs.append(job)



def _two_column_buttons(items):
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    for label, command in items:
        cmds.button(label=label, command=lambda *_, fn=command: fn())
    cmds.setParent("..")


def _build_dock_contents():
    load_plugin()
    tabs = cmds.tabLayout(innerMarginWidth=6, innerMarginHeight=6)

    files_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    cmds.text(label="MayaObjectBuilder", align="center", height=28)
    cmds.frameLayout(label="P3D", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.text(label="Import/export settings are in Maya's file dialog option panel.", align="left")
    _two_column_buttons([
        ("Import P3D", import_p3d),
        ("Export P3D", export_p3d),
    ])
    cmds.setParent("..")

    cmds.frameLayout(label="model.cfg", collapsable=True, collapse=True, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Import model.cfg", import_model_cfg),
        ("Export model.cfg", export_model_cfg),
    ])
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")

    tools_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    cmds.frameLayout(label="Validation", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Validate", validate),
    ])
    cmds.setParent("..")
    cmds.frameLayout(label="Advanced LOD Creation", collapsable=True, collapse=True, marginWidth=8, marginHeight=6)
    cmds.text(label="Only for building a new P3D scene from scratch.", align="left")
    cmds.button(label="Create LOD", command=lambda *_: create_lod())
    cmds.setParent("..")
    cmds.frameLayout(label="Object Builder Metadata", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Set Mass", set_mass),
        ("Set Flag", set_flag),
        ("Create Proxy", create_proxy),
    ])
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")

    properties_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_named_properties_ui()
    cmds.setParent("..")
    cmds.setParent("..")

    materials_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_material_metadata_ui()
    cmds.setParent("..")
    cmds.setParent("..")

    selections_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_selection_manager_ui()
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.tabLayout(tabs, edit=True, tabLabel=[(files_tab, "Files"), (tools_tab, "Tools"), (properties_tab, "Properties"), (materials_tab, "Materials"), (selections_tab, "Selections")])
    cmds.setParent("..")
    _refresh_selection_manager()


def open_dock():
    if cmds.about(batch=True):
        return None
    if cmds.workspaceControl(DOCK_NAME, exists=True):
        cmds.workspaceControl(DOCK_NAME, edit=True, restore=True, visible=True)
        _refresh_context_ui()
        return DOCK_NAME
    control = cmds.workspaceControl(DOCK_NAME, label="MayaObjectBuilder", retain=False, initialWidth=420, minimumWidth=360)
    for target in ("AttributeEditor", "AttributeEditorWorkspaceControl", "ChannelBoxLayerEditor"):
        if cmds.workspaceControl(target, exists=True):
            cmds.workspaceControl(DOCK_NAME, edit=True, tabToControl=(target, -1))
            break
    cmds.setParent(control)
    _build_dock_contents()
    _install_context_refresh_job(control)
    return control


def install_shelf_button():
    if cmds.about(batch=True):
        return None
    shelf = cmds.shelfLayout(SHELF_NAME, parent="ShelfLayout", cellWidth=34, cellHeight=34) if not cmds.shelfLayout(SHELF_NAME, exists=True) else SHELF_NAME
    button_name = SHELF_NAME + "OpenButton"
    if cmds.shelfButton(button_name, exists=True):
        cmds.deleteUI(button_name)
    command = "import runpy; ns = runpy.run_path(r'" + str(SCRIPT_PATH) + "'); ns['open_dock']()"
    return cmds.shelfButton(button_name, parent=shelf, label="MOB", annotation="Open MayaObjectBuilder", image="commandButton.png", command=command, sourceType="python")


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
    if cmds.about(batch=True):
        return None
    main_window = mel.eval("$tmp=$gMainWindow")
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)

    menu = cmds.menu(MENU_NAME, label="MayaObjectBuilder", parent=main_window, tearOff=True)
    cmds.menuItem(label="Open MayaObjectBuilder", parent=menu, command=lambda *_: open_dock())
    cmds.menuItem(label="Load Plugin", parent=menu, command=lambda *_: load_plugin())
    install_shelf_button()
    open_dock()
    return menu


if __name__ == "__main__":
    install()
