import importlib
import re
import sys
from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel

try:
    omui = importlib.import_module("maya.OpenMayaUI")
    shiboken = importlib.import_module("shiboken6")
    wrapInstance = shiboken.wrapInstance
    qt_is_valid = shiboken.isValid
    qt_widgets = importlib.import_module("PySide6.QtWidgets")
    qt_core = importlib.import_module("PySide6.QtCore")
    QT_AVAILABLE = True
except ImportError:
    omui = None
    wrapInstance = None
    qt_is_valid = None
    qt_widgets = None
    qt_core = None
    QT_AVAILABLE = False


SCRIPT_PATH = Path(globals().get("__file__", r"C:\Users\targaryen\source\repos\maya\dayz-object-builder\scripts\objectBuilderMenu.py")).resolve()
MENU_NAME = "MayaObjectBuilderMenu"
PLUGIN_NAME = "MayaObjectBuilder"
TRANSLATOR_NAME = "Arma P3D"
DOCK_NAME = "MayaObjectBuilderWorkspaceControl"
LOD_TYPE_MENU = "MayaObjectBuilderLodTypeMenu"
LOD_RESOLUTION_FIELD = "MayaObjectBuilderLodResolutionField"
LOD_PREVIEW_TEXT = "MayaObjectBuilderLodPreviewText"
LOD_CONTEXT_TEXT = "MayaObjectBuilderLodContextText"
AUTO_LOD_PRESET_MENU = "MayaObjectBuilderAutoLodPreset"
AUTO_LOD_FIRST_MENU = "MayaObjectBuilderAutoLodFirst"
AUTO_LOD_RESOLUTION_CHECK = "MayaObjectBuilderAutoLodResolution"
AUTO_LOD_GEOMETRY_CHECK = "MayaObjectBuilderAutoLodGeometry"
AUTO_LOD_MEMORY_CHECK = "MayaObjectBuilderAutoLodMemory"
AUTO_LOD_FIRE_CHECK = "MayaObjectBuilderAutoLodFire"
AUTO_LOD_VIEW_CHECK = "MayaObjectBuilderAutoLodView"
AUTO_LOD_GEOMETRY_TYPE_MENU = "MayaObjectBuilderAutoLodGeometryType"
AUTO_LOD_FIRE_QUALITY_FIELD = "MayaObjectBuilderAutoLodFireQuality"
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
MODEL_CFG_IMPORT_FIELD = "MayaObjectBuilderModelCfgImportPath"
MODEL_CFG_EXPORT_FIELD = "MayaObjectBuilderModelCfgExportPath"
_selection_manager_items = {}
_named_property_lods = {}
_named_property_items = {}
_material_metadata_items = {}
_ui_script_jobs = []
_qt_dock_widget = None

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
    if str(SCRIPT_PATH.parent) not in sys.path:
        sys.path.insert(0, str(SCRIPT_PATH.parent))
    mel.eval('if (!stringArrayContains("' + scripts_dir + '", stringToStringArray(`getenv MAYA_SCRIPT_PATH`, ";"))) putenv MAYA_SCRIPT_PATH (`getenv MAYA_SCRIPT_PATH` + ";' + scripts_dir + '")')
    mel.eval('source "' + scripts_dir + '/mayaObjectBuilderP3DOptions.mel"')


def _auto_lod_module():
    _ensure_script_path()
    return importlib.import_module("objectBuilderAutoLOD")


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
    selected = cmds.fileDialog2(fileMode=1, caption="Import P3D", fileFilter="Arma P3D (*.p3d)", selectFileFilter="Arma P3D")
    if selected:
        cmds.file(selected[0], i=True, type=TRANSLATOR_NAME, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")
        _refresh_context_ui()


def export_p3d():
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("ExportAll")')
    selected = cmds.fileDialog2(fileMode=0, caption="Export P3D", fileFilter="Arma P3D (*.p3d)", selectFileFilter="Arma P3D")
    if selected:
        cmds.file(rename=selected[0])
        cmds.file(exportAll=True, force=True, type=TRANSLATOR_NAME)


def import_model_cfg(path=None):
    load_plugin()
    selected_path = path
    if not selected_path:
        selected = cmds.fileDialog2(fileMode=1, caption="Import model.cfg", fileFilter="Config (*.cfg)")
        selected_path = selected[0] if selected else ""
    if selected_path:
        cmds.a3obImportModelCfg(path=selected_path)


def export_model_cfg(path=None):
    load_plugin()
    selected_path = path
    if not selected_path:
        selected = cmds.fileDialog2(fileMode=0, caption="Export model.cfg", fileFilter="Config (*.cfg)")
        selected_path = selected[0] if selected else ""
    if selected_path:
        cmds.a3obExportModelCfg(path=selected_path)


def _prompt(title, message, default=""):
    result = cmds.promptDialog(title=title, message=message, text=str(default), button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    if result != "OK":
        return None
    return cmds.promptDialog(query=True, text=True)


def _active_qt_dock():
    global _qt_dock_widget
    if _qt_dock_widget is None:
        return None
    if not QT_AVAILABLE or qt_is_valid is None:
        _qt_dock_widget = None
        return None
    try:
        if not qt_is_valid(_qt_dock_widget) or _qt_dock_widget.isHidden():
            _qt_dock_widget = None
            return None
    except RuntimeError:
        _qt_dock_widget = None
        return None
    return _qt_dock_widget


def _selected_lod_definition():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_lod_definition()
    if not cmds.optionMenu(LOD_TYPE_MENU, exists=True):
        return LOD_DEFINITIONS[0]
    label = cmds.optionMenu(LOD_TYPE_MENU, query=True, value=True)
    return LOD_DEFINITIONS_BY_LABEL.get(label, LOD_DEFINITIONS[0])


def _lod_resolution_value(definition):
    if not definition["has_resolution"]:
        return definition["default_resolution"]
    dock = _active_qt_dock()
    if dock is not None:
        return dock.lod_resolution_value()
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_lod_assignment()
        return
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


def _auto_lod_settings_from_legacy_ui():
    return {
        "preset": _option_menu_value(AUTO_LOD_PRESET_MENU).upper() or "QUADS",
        "first_lod": _option_menu_value(AUTO_LOD_FIRST_MENU) or "LOD1",
        "resolution": cmds.checkBox(AUTO_LOD_RESOLUTION_CHECK, query=True, value=True) if cmds.checkBox(AUTO_LOD_RESOLUTION_CHECK, exists=True) else True,
        "geometry": cmds.checkBox(AUTO_LOD_GEOMETRY_CHECK, query=True, value=True) if cmds.checkBox(AUTO_LOD_GEOMETRY_CHECK, exists=True) else True,
        "memory": cmds.checkBox(AUTO_LOD_MEMORY_CHECK, query=True, value=True) if cmds.checkBox(AUTO_LOD_MEMORY_CHECK, exists=True) else False,
        "fire_geometry": cmds.checkBox(AUTO_LOD_FIRE_CHECK, query=True, value=True) if cmds.checkBox(AUTO_LOD_FIRE_CHECK, exists=True) else False,
        "view_geometry": cmds.checkBox(AUTO_LOD_VIEW_CHECK, query=True, value=True) if cmds.checkBox(AUTO_LOD_VIEW_CHECK, exists=True) else False,
        "geometry_type": (_option_menu_value(AUTO_LOD_GEOMETRY_TYPE_MENU) or "BOX").upper(),
        "fire_quality": cmds.intField(AUTO_LOD_FIRE_QUALITY_FIELD, query=True, value=True) if cmds.intField(AUTO_LOD_FIRE_QUALITY_FIELD, exists=True) else 2,
    }


def generate_auto_lods_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    settings = dock.auto_lod_settings() if dock is not None else _auto_lod_settings_from_legacy_ui()
    generated = _auto_lod_module().generate_auto_lods(settings)
    if generated:
        _refresh_context_ui()


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
    dock = _active_qt_dock()
    if dock is not None:
        value = dock.mass_value()
        mode = dock.mass_mode()
    else:
        value = cmds.floatField(MASS_VALUE_FIELD, query=True, value=True) if cmds.floatField(MASS_VALUE_FIELD, exists=True) else 1.0
        mode = cmds.optionMenu(MASS_MODE_MENU, query=True, value=True) if cmds.optionMenu(MASS_MODE_MENU, exists=True) else "All vertices"
    cmds.a3obSetMass(value=value, selectedComponents=(mode == "Selected vertices"))


def clear_mass_from_ui():
    load_plugin()
    cmds.a3obSetMass(clear=True)


def apply_flag_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is not None:
        component_label = dock.flag_component()
        value = dock.flag_value()
        name = dock.flag_name()
    else:
        component_label = cmds.optionMenu(FLAG_COMPONENT_MENU, query=True, value=True) if cmds.optionMenu(FLAG_COMPONENT_MENU, exists=True) else "Face"
        value = cmds.intField(FLAG_VALUE_FIELD, query=True, value=True) if cmds.intField(FLAG_VALUE_FIELD, exists=True) else 1
        name = cmds.textField(FLAG_NAME_FIELD, query=True, text=True).strip() if cmds.textField(FLAG_NAME_FIELD, exists=True) else "a3ob_flag"
    if not name:
        cmds.warning("Enter a flag set name")
        return
    cmds.a3obSetFlag(component=component_label.lower(), value=value, name=name)


def create_proxy_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is not None:
        path = dock.proxy_path()
        index = dock.proxy_index()
        from_selection = dock.proxy_from_selection()
    else:
        path = cmds.textField(PROXY_PATH_FIELD, query=True, text=True).strip() if cmds.textField(PROXY_PATH_FIELD, exists=True) else ""
        index = cmds.intField(PROXY_INDEX_FIELD, query=True, value=True) if cmds.intField(PROXY_INDEX_FIELD, exists=True) else 1
        from_selection = cmds.checkBox(PROXY_FROM_SELECTION_CHECK, query=True, value=True) if cmds.checkBox(PROXY_FROM_SELECTION_CHECK, exists=True) else True
    if not path:
        cmds.warning("Enter a proxy path")
        return
    cmds.a3obProxy(path=path, index=index, fromSelection=from_selection, update=True)


def import_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_import_path() if dock is not None else ""
    if not path:
        path = cmds.textField(MODEL_CFG_IMPORT_FIELD, query=True, text=True).strip() if cmds.textField(MODEL_CFG_IMPORT_FIELD, exists=True) else ""
    import_model_cfg(path or None)


def export_model_cfg_from_ui():
    dock = _active_qt_dock()
    path = dock.model_cfg_export_path() if dock is not None else ""
    if not path:
        path = cmds.textField(MODEL_CFG_EXPORT_FIELD, query=True, text=True).strip() if cmds.textField(MODEL_CFG_EXPORT_FIELD, exists=True) else ""
    export_model_cfg(path or None)


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


def _normalize_dayz_path(path):
    path = (path or "").strip().replace("/", "\\")
    if len(path) >= 2 and path[1] == ":":
        path = path[2:].lstrip("\\")
    return re.sub(r"\\+", r"\\", path)


def _strip_drive_letter(path):
    return _normalize_dayz_path(path)


def _live_set_members(set_node):
    if not _node_exists(set_node):
        return []
    members = cmds.sets(set_node, query=True) or []
    live_members = []
    for member in members:
        expanded = cmds.ls(member, flatten=True) or []
        live_members.extend(item for item in expanded if _node_exists(item.split(".", 1)[0]))
    return live_members


def _mesh_shapes_for_item(item):
    node = item.split(".", 1)[0]
    if not _node_exists(node):
        return []
    if cmds.objectType(node, isType="mesh"):
        return [node]
    return cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []


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


def _clear_selection_manager_state(message="Select a row to see details."):
    dock = _active_qt_dock()
    if dock is not None:
        dock.set_selection_details(message)
        return
    if cmds.text(SELECTION_MANAGER_DETAILS, exists=True):
        cmds.text(SELECTION_MANAGER_DETAILS, edit=True, label=message)


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


def _normalize_object_builder_sets():
    for node in cmds.ls(type="objectSet") or []:
        if _is_object_builder_set(node):
            _hide_object_builder_set(node)


def _selection_sets():
    _normalize_object_builder_sets()
    sets = []
    for node in cmds.ls(type="objectSet") or []:
        if not _is_object_builder_set(node) or not _attr_exists(node, "a3obSelectionName"):
            continue
        name = _safe_get_attr(node, "a3obSelectionName", "") or ""
        is_proxy = bool(_safe_get_attr(node, "a3obIsProxySelection", False))
        flag_component = _safe_get_attr(node, "a3obFlagComponent", "") or ""
        lod = _set_lod_label(node)
        sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod})
    return sorted(sets, key=lambda item: (item["lod"].lower(), item["kind"], item["name"].lower(), item["node"].lower()))


def _selected_selection_set():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_selection_set_node()
    if not cmds.textScrollList(SELECTION_MANAGER_LIST, exists=True):
        return None
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


def _selection_set_details(set_node):
    members = _live_set_members(set_node)
    name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
    flag_component = _safe_get_attr(set_node, "a3obFlagComponent", "") or ""
    is_proxy = bool(_safe_get_attr(set_node, "a3obIsProxySelection", False))
    return f"LOD: {_set_lod_label(set_node)}    Type: {_set_kind(is_proxy, flag_component)}    OB name: {name}    Members: {len(members)}\nMaya set: {set_node}"


def _update_selection_details():
    set_node = _selected_selection_set()
    if not set_node:
        _clear_selection_manager_state()
        return
    details = _selection_set_details(set_node)
    dock = _active_qt_dock()
    if dock is not None:
        dock.set_selection_details(details)
        return
    if cmds.text(SELECTION_MANAGER_DETAILS, exists=True):
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_selection_manager(rebuild_lods)
        return
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
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_named_property_lod()
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_named_properties(rebuild_lods)
        return
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.select_named_property()
        return
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
    dock = _active_qt_dock()
    if dock is not None:
        name = dock.named_property_name()
        value = dock.named_property_value()
    else:
        name = cmds.textField(NAMED_PROPERTIES_NAME, query=True, text=True).strip()
        value = cmds.textField(NAMED_PROPERTIES_VALUE, query=True, text=True).strip()
    _set_named_property_value(name, value)


def _remove_named_property():
    lod = _selected_named_property_lod()
    dock = _active_qt_dock()
    name = dock.named_property_name() if dock is not None else cmds.textField(NAMED_PROPERTIES_NAME, query=True, text=True).strip()
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.clear_named_property_fields()
    else:
        cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text="")
        cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text="")
    _refresh_named_properties()


def _apply_common_named_property(*_):
    dock = _active_qt_dock()
    selected = dock.named_property_preset() if dock is not None else _option_menu_value(NAMED_PROPERTIES_COMMON)
    for name, value in COMMON_NAMED_PROPERTIES:
        label = f"{name} = {value}"
        if selected == label:
            if dock is not None:
                dock.set_named_property_fields(name, value)
            else:
                cmds.textField(NAMED_PROPERTIES_NAME, edit=True, text=name)
                cmds.textField(NAMED_PROPERTIES_VALUE, edit=True, text=value)
            _set_named_property_value(name, value)
            return


def _build_named_properties_ui():
    _card("Named Properties", "Select a LOD, choose a preset or edit key/value pairs inline.")
    _labeled_row("LOD", lambda: cmds.optionMenu(NAMED_PROPERTIES_LOD, changeCommand=lambda *_: _refresh_named_properties(False)))
    _labeled_row("Preset", lambda: cmds.optionMenu(NAMED_PROPERTIES_COMMON, changeCommand=_apply_common_named_property))
    for name, value in COMMON_NAMED_PROPERTIES:
        cmds.menuItem(label=f"{name} = {value}", parent=NAMED_PROPERTIES_COMMON)
    cmds.textScrollList(NAMED_PROPERTIES_LIST, allowMultiSelection=False, height=96, selectCommand=lambda *_: _select_named_property())
    _labeled_row("Name", lambda: cmds.textField(NAMED_PROPERTIES_NAME, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields))
    _labeled_row("Value", lambda: cmds.textField(NAMED_PROPERTIES_VALUE, changeCommand=_commit_named_property_fields, enterCommand=_commit_named_property_fields))
    _action_row([
        ("Add / Update", _commit_named_property_fields, "Commit the current name/value pair."),
        ("Remove", _remove_named_property, "Remove the selected named property."),
    ], columns=2)
    _end_card()
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


def _material_metadata_label(item):
    name = item["material_node"] or "No material"
    texture = item["texture"] or "—"
    rvmat = item["material"] or "—"
    return f"{name}\n    tex: {texture}    rvmat: {rvmat}"


def _refresh_material_metadata():
    global _material_metadata_items
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_material_metadata()
        return
    if not cmds.textScrollList(MATERIAL_METADATA_LIST, exists=True):
        return
    cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, removeAll=True)
    _material_metadata_items = {}
    items = _material_nodes_for_selection()
    if not items:
        cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, append="Select a mesh, LOD, or faces to edit its DayZ materials")
        return
    for item in items:
        label = _material_metadata_label(item)
        _material_metadata_items[label] = item
        cmds.textScrollList(MATERIAL_METADATA_LIST, edit=True, append=label)


def _selected_material_metadata_item():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_material_metadata_item()
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
    dock = _active_qt_dock()
    if dock is not None:
        dock.select_material_metadata()
        return
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


def _persist_selected_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        return None
    dock = _active_qt_dock()
    if dock is not None:
        texture = _strip_drive_letter(dock.material_texture_path())
        material = _strip_drive_letter(dock.material_rvmat_path())
    else:
        texture = _strip_drive_letter(cmds.textField(MATERIAL_METADATA_TEXTURE, query=True, text=True).strip())
        material = _strip_drive_letter(cmds.textField(MATERIAL_METADATA_MATERIAL, query=True, text=True).strip())
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


def _commit_selected_material_metadata(*_):
    if _persist_selected_material_metadata() is None:
        return
    _refresh_material_metadata()


def _assign_new_material_metadata_to_selection():
    dock = _active_qt_dock()
    if dock is not None:
        texture = dock.material_texture_path()
        material = dock.material_rvmat_path()
    else:
        texture = _normalize_dayz_path(cmds.textField(MATERIAL_METADATA_TEXTURE, query=True, text=True))
        material = _normalize_dayz_path(cmds.textField(MATERIAL_METADATA_MATERIAL, query=True, text=True))
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
    _card("DayZ Material / Texture Metadata", "Select a material row, edit texture/material paths, then apply to faces or clear the highlighted row.")
    cmds.textScrollList(MATERIAL_METADATA_LIST, allowMultiSelection=False, height=150, selectCommand=lambda *_: _select_material_metadata())
    _path_row("Texture", MATERIAL_METADATA_TEXTURE, "Select texture path", "Texture (*.paa)", change_command=_commit_selected_material_metadata)
    _path_row("Material", MATERIAL_METADATA_MATERIAL, "Select material path", "Material (*.rvmat)", change_command=_commit_selected_material_metadata)
    _action_row([
        ("Apply to Faces", _assign_new_material_metadata_to_selection, "Assign the current metadata to selected faces."),
        ("Clear Row", _clear_selected_material_metadata, "Clear Object Builder metadata on the selected material row."),
    ], columns=2)
    _end_card()
    _refresh_material_metadata()


def _build_selection_manager_ui():
    _card("Selections", "Filter, inspect, and edit Object Builder selections, proxies, and flag sets.")
    _labeled_row("LOD", lambda: cmds.optionMenu(SELECTION_MANAGER_LOD_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False)))
    cmds.menuItem(label="All LODs", parent=SELECTION_MANAGER_LOD_FILTER)
    _labeled_row("Type", lambda: cmds.optionMenu(SELECTION_MANAGER_TYPE_FILTER, changeCommand=lambda *_: _refresh_selection_manager(False)))
    for label in ("All Types", "Selection", "Proxy", "Vertex Flag", "Face Flag"):
        cmds.menuItem(label=label, parent=SELECTION_MANAGER_TYPE_FILTER)
    _labeled_row("Search", lambda: cmds.textField(SELECTION_MANAGER_SEARCH, changeCommand=lambda *_: _refresh_selection_manager(False), enterCommand=lambda *_: _refresh_selection_manager(False)))
    cmds.textScrollList(SELECTION_MANAGER_LIST, allowMultiSelection=False, height=155, selectCommand=lambda *_: _update_selection_details(), doubleClickCommand=lambda *_: _select_set_members())
    cmds.text(SELECTION_MANAGER_DETAILS, label="Select a row to see details.", align="left", wordWrap=True)
    _action_row([
        ("Select", _select_set_members, "Select live members of the highlighted set."),
        ("Rename", _rename_selection_set, "Rename the Object Builder selection."),
        ("Create", _create_selection_set, "Create a selection set from selected components."),
        ("Find", find_components_from_ui, "Find closed mesh components and create Component## sets."),
    ], columns=4, height=26)
    _action_row([
        ("Add", _add_to_selection_set, "Add selected components to the highlighted set."),
        ("Remove", _remove_from_selection_set, "Remove selected components from the highlighted set."),
        ("Delete", _delete_selection_set, "Delete the highlighted Object Builder set."),
        ("Clear OB", _clear_all_object_builder_sets, "Clear all Object Builder selection sets."),
    ], columns=4, height=26)
    _end_card()


def selection_manager():
    open_dock()


def _refresh_context_ui():
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_lod_assignment()
        dock.refresh_named_properties(True)
        dock.refresh_material_metadata()
        dock.refresh_selection_manager(True)
        return
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



def _action_button(label, command, height=32, annotation=""):
    kwargs = {"label": label, "height": height, "command": lambda *_: command()}
    if annotation:
        kwargs["annotation"] = annotation
    return cmds.button(**kwargs)


def _icon_action(label, command, image="", annotation=""):
    if image:
        try:
            return cmds.iconTextButton(style="iconAndTextVertical", image1=image, label=label, height=48, command=lambda *_: command(), annotation=annotation or label)
        except RuntimeError:
            pass
    return _action_button(label, command, height=32, annotation=annotation)


def _button_stack(items):
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    for item in items:
        label, command = item[:2]
        annotation = item[2] if len(item) > 2 else ""
        _action_button(label, command, annotation=annotation)
    cmds.setParent("..")


def _compact_button_stack(items):
    cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
    for item in items:
        label, command = item[:2]
        annotation = item[2] if len(item) > 2 else ""
        cmds.button(label=label, height=28, command=lambda *_, fn=command: fn(), annotation=annotation)
    cmds.setParent("..")


def _action_row(items, columns=2, height=30):
    if not items:
        return
    columns = max(1, min(columns, len(items)))
    cmds.rowColumnLayout(numberOfColumns=columns, columnSpacing=[(index + 1, 4) for index in range(columns)], rowSpacing=[(1, 4), (2, 4), (3, 4), (4, 4)])
    for item in items:
        label, command = item[:2]
        annotation = item[2] if len(item) > 2 else ""
        cmds.button(label=label, width=92, height=height, command=lambda *_, fn=command: fn(), annotation=annotation)
    cmds.setParent("..")


def _quick_action_bar(items):
    cmds.frameLayout(label="Quick Actions", collapsable=True, collapse=False, marginWidth=6, marginHeight=4)
    cmds.rowColumnLayout(numberOfColumns=3, columnSpacing=[(1, 4), (2, 4), (3, 4)], rowSpacing=[(1, 4), (2, 4)])
    for item in items:
        label, command = item[:2]
        annotation = item[2] if len(item) > 2 else ""
        cmds.button(label=label, width=112, height=26, command=lambda *_, fn=command: fn(), annotation=annotation)
    cmds.setParent("..")
    cmds.setParent("..")


def _button_pair(items):
    _action_row(items, columns=2)


def _two_column_buttons(items):
    _action_row(items, columns=2)


def _full_width_button(label, command):
    return _action_button(label, command)


def _browse_path(field, mode, caption, file_filter=""):
    selected = cmds.fileDialog2(fileMode=mode, caption=caption, fileFilter=file_filter) if file_filter else cmds.fileDialog2(fileMode=mode, caption=caption)
    if selected and cmds.textField(field, exists=True):
        path = _normalize_dayz_path(selected[0])
        cmds.textField(field, edit=True, text=path)
        return path
    return ""


def _clear_text_field(field):
    if cmds.textField(field, exists=True):
        cmds.textField(field, edit=True, text="")


def _path_row(label, field, browse_caption, file_filter="", folder=False, save=False, change_command=None):
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(96, 220, 34, 34), adjustableColumn=2)
    cmds.text(label=label, align="right")
    text_kwargs = {"text": ""}
    if change_command:
        text_kwargs["changeCommand"] = change_command
        text_kwargs["enterCommand"] = change_command
    cmds.textField(field, **text_kwargs)
    mode = 3 if folder else (0 if save else 1)
    cmds.button(label="...", annotation=browse_caption, command=lambda *_: _browse_path(field, mode, browse_caption, file_filter))
    cmds.button(label="X", annotation="Clear path", command=lambda *_: _clear_text_field(field))
    cmds.setParent("..")


def _card(label, subtitle="", collapse=False):
    _section(label, subtitle, collapse=collapse)


def _end_card():
    _end_section()


def _labeled_row(label, control_builder):
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(96, 260), adjustableColumn=2)
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
    _card("LOD Assignment", "Choose an Object Builder LOD type, then apply it to the current transform or create an empty LOD container.")
    cmds.text(LOD_CONTEXT_TEXT, label="Target: No Object Builder LOD selected.", align="left", wordWrap=True)
    _labeled_row("LOD type", lambda: cmds.optionMenu(LOD_TYPE_MENU, changeCommand=_refresh_lod_assignment_ui))
    for definition in LOD_DEFINITIONS:
        cmds.menuItem(label=definition["label"], parent=LOD_TYPE_MENU)
    _labeled_row("Resolution", lambda: cmds.intField(LOD_RESOLUTION_FIELD, minValue=0, value=1, changeCommand=_refresh_lod_assignment_ui))
    cmds.text(LOD_PREVIEW_TEXT, label="Will assign: Resolution 1", align="left", wordWrap=True)
    _action_row([
        ("Assign", assign_lod_to_selection, "Assign the selected LOD type to the current selection."),
        ("Create Empty", create_empty_lod, "Create a new empty LOD transform with the selected type."),
    ], columns=2)
    _end_card()
    _refresh_lod_assignment_ui()

    _card("Auto LOD", "Generate Maya-native DayZ LODs from the selected mesh using the imported Blender addon defaults.")
    _labeled_row("Preset", lambda: cmds.optionMenu(AUTO_LOD_PRESET_MENU))
    for label in ("QUADS", "TRIS", "CUSTOM"):
        cmds.menuItem(label=label, parent=AUTO_LOD_PRESET_MENU)
    _labeled_row("First LOD", lambda: cmds.optionMenu(AUTO_LOD_FIRST_MENU))
    for label in ("LOD1", "LOD0"):
        cmds.menuItem(label=label, parent=AUTO_LOD_FIRST_MENU)
    cmds.checkBox(AUTO_LOD_RESOLUTION_CHECK, label="Resolution LODs", value=True)
    cmds.checkBox(AUTO_LOD_GEOMETRY_CHECK, label="Geometry LOD", value=True)
    cmds.checkBox(AUTO_LOD_MEMORY_CHECK, label="Memory LOD", value=False)
    cmds.checkBox(AUTO_LOD_FIRE_CHECK, label="Fire Geometry LOD", value=False)
    cmds.checkBox(AUTO_LOD_VIEW_CHECK, label="View Geometry LOD", value=False)
    _labeled_row("Geometry", lambda: cmds.optionMenu(AUTO_LOD_GEOMETRY_TYPE_MENU))
    for label in ("BOX", "NONE"):
        cmds.menuItem(label=label, parent=AUTO_LOD_GEOMETRY_TYPE_MENU)
    _labeled_row("Fire quality", lambda: cmds.intField(AUTO_LOD_FIRE_QUALITY_FIELD, minValue=1, maxValue=10, value=2))
    _action_row([("Generate Auto LOD", generate_auto_lods_from_ui, "Generate Resolution, Geometry, Memory, Fire, and View LODs from the selected mesh.")], columns=1)
    _end_card()


def _build_metadata_tools_ui():
    _card("Mass", "Apply or clear vertex mass metadata on the current selection.")
    _labeled_row("Value", lambda: cmds.floatField(MASS_VALUE_FIELD, value=1.0, precision=3))
    _labeled_row("Mode", lambda: cmds.optionMenu(MASS_MODE_MENU))
    cmds.menuItem(label="All vertices", parent=MASS_MODE_MENU)
    cmds.menuItem(label="Selected vertices", parent=MASS_MODE_MENU)
    _action_row([
        ("Apply", apply_mass_from_ui, "Apply mass using the selected mode."),
        ("Clear", clear_mass_from_ui, "Clear mass metadata from the current selection."),
    ], columns=2)
    _end_card()

    _card("Flags", "Create Object Builder face or vertex flag sets from the current selection.")
    _labeled_row("Component", lambda: cmds.optionMenu(FLAG_COMPONENT_MENU))
    cmds.menuItem(label="Face", parent=FLAG_COMPONENT_MENU)
    cmds.menuItem(label="Vertex", parent=FLAG_COMPONENT_MENU)
    _labeled_row("Value", lambda: cmds.intField(FLAG_VALUE_FIELD, value=1))
    _labeled_row("Set name", lambda: cmds.textField(FLAG_NAME_FIELD, text="a3ob_flag"))
    _action_row([("Apply Flag", apply_flag_from_ui, "Create or update a flag set from the current selection.")], columns=1)
    _end_card()

    _card("Proxy", "Create or update proxy metadata with a visible path picker.")
    _path_row("Path", PROXY_PATH_FIELD, "Select proxy P3D", "P3D (*.p3d)")
    _labeled_row("Index", lambda: cmds.intField(PROXY_INDEX_FIELD, minValue=0, value=1))
    cmds.checkBox(PROXY_FROM_SELECTION_CHECK, label="Create from selected components", value=True)
    _action_row([("Create Proxy", create_proxy_from_ui, "Create or update the proxy selection metadata.")], columns=1)
    _end_card()

    _build_named_properties_ui()


def _build_validation_ui():
    _card("Validation", "Check Object Builder LODs before export. Scene checks every LOD; Selection checks only selected LODs/components.")
    _action_row([
        ("Scene", lambda: cmds.a3obValidate(), "Validate all Object Builder LODs in the scene."),
        ("Selection", lambda: cmds.a3obValidate(selectionOnly=True), "Validate only selected Object Builder LODs."),
    ], columns=2)
    _end_card()


def _qt_button(label, callback, tooltip=""):
    button = qt_widgets.QPushButton(label)
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    return button


class MayaObjectBuilderDock(qt_widgets.QWidget if QT_AVAILABLE else object):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MayaObjectBuilderQtDock")
        self.lod_type_combo = None
        self.lod_resolution = None
        self.lod_context = None
        self.lod_preview = None
        self.auto_lod_preset = None
        self.auto_lod_first = None
        self.auto_lod_resolution = None
        self.auto_lod_geometry = None
        self.auto_lod_memory = None
        self.auto_lod_fire = None
        self.auto_lod_view = None
        self.auto_lod_geometry_type = None
        self.auto_lod_fire_quality = None
        self.model_cfg_import = None
        self.model_cfg_export = None
        self.mass_value_field = None
        self.mass_mode_combo = None
        self.flag_component_combo = None
        self.flag_value_field = None
        self.flag_name_field = None
        self.proxy_path_field = None
        self.proxy_index_field = None
        self.proxy_from_selection_check = None
        self.named_lod_combo = None
        self.named_preset_combo = None
        self.named_list = None
        self.named_name_field = None
        self.named_value_field = None
        self.named_lods = {}
        self.named_items = {}
        self.material_list = None
        self.material_texture = None
        self.material_rvmat = None
        self.material_items = {}
        self.selection_lod_filter = None
        self.selection_type_filter = None
        self.selection_search = None
        self.selection_list = None
        self.selection_details = None
        self.selection_items = {}
        self._build_ui()
        self.refresh_lod_assignment()

    def _build_ui(self):
        layout = qt_widgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.addWidget(self._build_quick_actions())

        tabs = qt_widgets.QTabWidget()
        tabs.addTab(self._build_lod_tab(), "LOD")
        tabs.addTab(self._build_files_tab(), "Files")
        tabs.addTab(self._build_metadata_tab(), "Metadata")
        tabs.addTab(self._build_named_properties_tab(), "Properties")
        tabs.addTab(self._build_materials_tab(), "Materials")
        tabs.addTab(self._build_selections_tab(), "Selections")
        tabs.addTab(self._build_validation_tab(), "Validation")
        layout.addWidget(tabs)

    def _build_quick_actions(self):
        group = qt_widgets.QGroupBox("Quick Actions")
        layout = qt_widgets.QGridLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        actions = [
            ("Import P3D", import_p3d, "Open a P3D through Maya's native Arma P3D importer."),
            ("Export P3D", export_p3d, "Export the current scene through Maya's native Arma P3D exporter."),
            ("Import CFG", import_model_cfg_from_ui, "Import a model.cfg skeleton file."),
            ("Export CFG", export_model_cfg_from_ui, "Export selected/root skeleton joints to model.cfg."),
            ("Validate Scene", lambda: cmds.a3obValidate(), "Validate all Object Builder LODs in the scene."),
            ("Validate Sel", lambda: cmds.a3obValidate(selectionOnly=True), "Validate selected Object Builder LODs."),
        ]
        for index, (label, callback, tooltip) in enumerate(actions):
            layout.addWidget(_qt_button(label, callback, tooltip), index // 3, index % 3)
        return group

    def _build_lod_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.lod_context = qt_widgets.QLabel()
        self.lod_context.setWordWrap(True)
        layout.addWidget(self.lod_context)

        form = qt_widgets.QFormLayout()
        self.lod_type_combo = qt_widgets.QComboBox()
        for definition in LOD_DEFINITIONS:
            self.lod_type_combo.addItem(definition["label"], definition["type"])
        self.lod_type_combo.currentIndexChanged.connect(self.refresh_lod_assignment)
        form.addRow("LOD type", self.lod_type_combo)

        self.lod_resolution = qt_widgets.QSpinBox()
        self.lod_resolution.setMinimum(0)
        self.lod_resolution.setValue(1)
        self.lod_resolution.valueChanged.connect(self.refresh_lod_assignment)
        form.addRow("Resolution", self.lod_resolution)
        layout.addLayout(form)

        self.lod_preview = qt_widgets.QLabel()
        self.lod_preview.setWordWrap(True)
        layout.addWidget(self.lod_preview)

        buttons = qt_widgets.QHBoxLayout()
        buttons.addWidget(_qt_button("Assign", assign_lod_to_selection, "Assign the selected LOD type to the current selection."))
        buttons.addWidget(_qt_button("Create Empty", create_empty_lod, "Create a new empty LOD transform with the selected type."))
        layout.addLayout(buttons)

        auto_group = qt_widgets.QGroupBox("Auto LOD")
        auto_layout = qt_widgets.QFormLayout(auto_group)
        self.auto_lod_preset = qt_widgets.QComboBox()
        self.auto_lod_preset.addItems(["QUADS", "TRIS", "CUSTOM"])
        self.auto_lod_first = qt_widgets.QComboBox()
        self.auto_lod_first.addItems(["LOD1", "LOD0"])
        self.auto_lod_resolution = qt_widgets.QCheckBox("Resolution LODs")
        self.auto_lod_resolution.setChecked(True)
        self.auto_lod_geometry = qt_widgets.QCheckBox("Geometry LOD")
        self.auto_lod_geometry.setChecked(True)
        self.auto_lod_memory = qt_widgets.QCheckBox("Memory LOD")
        self.auto_lod_fire = qt_widgets.QCheckBox("Fire Geometry LOD")
        self.auto_lod_view = qt_widgets.QCheckBox("View Geometry LOD")
        self.auto_lod_geometry_type = qt_widgets.QComboBox()
        self.auto_lod_geometry_type.addItems(["BOX", "NONE"])
        self.auto_lod_fire_quality = qt_widgets.QSpinBox()
        self.auto_lod_fire_quality.setRange(1, 10)
        self.auto_lod_fire_quality.setValue(2)
        auto_layout.addRow("Preset", self.auto_lod_preset)
        auto_layout.addRow("First LOD", self.auto_lod_first)
        auto_layout.addRow(self.auto_lod_resolution)
        auto_layout.addRow(self.auto_lod_geometry)
        auto_layout.addRow(self.auto_lod_memory)
        auto_layout.addRow(self.auto_lod_fire)
        auto_layout.addRow(self.auto_lod_view)
        auto_layout.addRow("Geometry", self.auto_lod_geometry_type)
        auto_layout.addRow("Fire quality", self.auto_lod_fire_quality)
        auto_layout.addRow(_qt_button("Generate Auto LOD", generate_auto_lods_from_ui, "Generate DayZ LODs from the selected mesh."))
        layout.addWidget(auto_group)
        layout.addStretch()
        return widget

    def _build_files_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        p3d_group = qt_widgets.QGroupBox("P3D")
        p3d_layout = qt_widgets.QVBoxLayout(p3d_group)
        p3d_hint = qt_widgets.QLabel("Use Maya's native File dialog with the Arma P3D translator and option panel.")
        p3d_hint.setWordWrap(True)
        p3d_layout.addWidget(p3d_hint)
        p3d_buttons = qt_widgets.QHBoxLayout()
        p3d_buttons.addWidget(_qt_button("Import P3D", import_p3d))
        p3d_buttons.addWidget(_qt_button("Export P3D", export_p3d))
        p3d_layout.addLayout(p3d_buttons)
        layout.addWidget(p3d_group)

        cfg_group = qt_widgets.QGroupBox("model.cfg")
        cfg_layout = qt_widgets.QFormLayout(cfg_group)
        self.model_cfg_import = self._path_picker("Import path", "Select model.cfg", 1, "Config (*.cfg)")
        self.model_cfg_export = self._path_picker("Export path", "Export model.cfg", 0, "Config (*.cfg)")
        cfg_layout.addRow("Import", self.model_cfg_import)
        cfg_layout.addRow("Export", self.model_cfg_export)
        cfg_buttons = qt_widgets.QHBoxLayout()
        cfg_buttons.addWidget(_qt_button("Import CFG", import_model_cfg_from_ui))
        cfg_buttons.addWidget(_qt_button("Export CFG", export_model_cfg_from_ui))
        cfg_layout.addRow(cfg_buttons)
        layout.addWidget(cfg_group)
        layout.addStretch()
        return widget

    def _path_picker(self, label, caption, mode, file_filter):
        container = qt_widgets.QWidget()
        layout = qt_widgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        field = qt_widgets.QLineEdit()
        browse = qt_widgets.QPushButton("...")
        clear = qt_widgets.QPushButton("X")
        browse.setToolTip(caption)
        clear.setToolTip(f"Clear {label}")
        browse.clicked.connect(lambda: self._browse_qt_path(field, caption, mode, file_filter))
        clear.clicked.connect(field.clear)
        layout.addWidget(field, 1)
        layout.addWidget(browse)
        layout.addWidget(clear)
        return container

    def _browse_qt_path(self, field, caption, mode, file_filter):
        selected = cmds.fileDialog2(fileMode=mode, caption=caption, fileFilter=file_filter)
        if selected:
            field.setText(_normalize_dayz_path(selected[0]))

    def _build_metadata_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = qt_widgets.QLabel("Apply Object Builder metadata to the current mesh or component selection.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        mass_group = qt_widgets.QGroupBox("Mass")
        mass_layout = qt_widgets.QFormLayout(mass_group)
        self.mass_value_field = qt_widgets.QDoubleSpinBox()
        self.mass_value_field.setDecimals(3)
        self.mass_value_field.setValue(1.0)
        self.mass_value_field.setRange(-1000000.0, 1000000.0)
        self.mass_mode_combo = qt_widgets.QComboBox()
        self.mass_mode_combo.addItems(["All vertices", "Selected vertices"])
        mass_layout.addRow("Value", self.mass_value_field)
        mass_layout.addRow("Mode", self.mass_mode_combo)
        mass_buttons = qt_widgets.QHBoxLayout()
        mass_buttons.addWidget(_qt_button("Apply", apply_mass_from_ui))
        mass_buttons.addWidget(_qt_button("Clear", clear_mass_from_ui))
        mass_layout.addRow(mass_buttons)
        layout.addWidget(mass_group)

        flags_group = qt_widgets.QGroupBox("Flags")
        flags_layout = qt_widgets.QFormLayout(flags_group)
        self.flag_component_combo = qt_widgets.QComboBox()
        self.flag_component_combo.addItems(["Face", "Vertex"])
        self.flag_value_field = qt_widgets.QSpinBox()
        self.flag_value_field.setRange(-2147483648, 2147483647)
        self.flag_value_field.setValue(1)
        self.flag_name_field = qt_widgets.QLineEdit("a3ob_flag")
        flags_layout.addRow("Component", self.flag_component_combo)
        flags_layout.addRow("Value", self.flag_value_field)
        flags_layout.addRow("Set name", self.flag_name_field)
        flags_layout.addRow(_qt_button("Apply Flag", apply_flag_from_ui))
        layout.addWidget(flags_group)

        proxy_group = qt_widgets.QGroupBox("Proxy")
        proxy_layout = qt_widgets.QFormLayout(proxy_group)
        self.proxy_path_field = self._path_picker("Proxy path", "Select proxy P3D", 1, "Arma P3D (*.p3d)")
        self.proxy_index_field = qt_widgets.QSpinBox()
        self.proxy_index_field.setRange(0, 2147483647)
        self.proxy_index_field.setValue(1)
        self.proxy_from_selection_check = qt_widgets.QCheckBox("Create from selected components")
        self.proxy_from_selection_check.setChecked(True)
        proxy_layout.addRow("Path", self.proxy_path_field)
        proxy_layout.addRow("Index", self.proxy_index_field)
        proxy_layout.addRow(self.proxy_from_selection_check)
        proxy_layout.addRow(_qt_button("Create Proxy", create_proxy_from_ui))
        layout.addWidget(proxy_group)

        layout.addStretch()
        return widget

    def _build_named_properties_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = qt_widgets.QLabel("Named properties are stored on the selected Object Builder LOD and exported into the P3D TAGG metadata.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = qt_widgets.QFormLayout()
        self.named_lod_combo = qt_widgets.QComboBox()
        self.named_lod_combo.currentIndexChanged.connect(lambda *_: self.refresh_named_properties(False))
        self.named_preset_combo = qt_widgets.QComboBox()
        self.named_preset_combo.addItems([f"{name} = {value}" for name, value in COMMON_NAMED_PROPERTIES])
        self.named_preset_combo.currentIndexChanged.connect(_apply_common_named_property)
        form.addRow("LOD", self.named_lod_combo)
        form.addRow("Preset", self.named_preset_combo)
        layout.addLayout(form)

        self.named_list = qt_widgets.QListWidget()
        self.named_list.currentItemChanged.connect(lambda *_: self.select_named_property())
        layout.addWidget(self.named_list, 1)

        edit_form = qt_widgets.QFormLayout()
        self.named_name_field = qt_widgets.QLineEdit()
        self.named_name_field.setPlaceholderText("property name")
        self.named_value_field = qt_widgets.QLineEdit()
        self.named_value_field.setPlaceholderText("property value")
        edit_form.addRow("Name", self.named_name_field)
        edit_form.addRow("Value", self.named_value_field)
        layout.addLayout(edit_form)

        named_buttons = qt_widgets.QHBoxLayout()
        named_buttons.addWidget(_qt_button("Add / Update", _commit_named_property_fields, "Save the current name/value pair on the active LOD."))
        named_buttons.addWidget(_qt_button("Remove", _remove_named_property, "Remove the selected property from the active LOD."))
        layout.addLayout(named_buttons)

        self.refresh_named_properties(True)
        return widget

    def _build_materials_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = qt_widgets.QLabel("Pick a Maya material, then set its texture and rvmat paths. Edits save to the selected material instantly.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.material_list = qt_widgets.QListWidget()
        self.material_list.currentItemChanged.connect(lambda *_: self.select_material_metadata())
        layout.addWidget(self.material_list, 1)

        form = qt_widgets.QFormLayout()
        self.material_texture = self._path_picker("Texture", "Select texture path", 1, "Texture (*.paa)")
        self.material_rvmat = self._path_picker("Material", "Select material path", 1, "Material (*.rvmat)")
        form.addRow("Texture", self.material_texture)
        form.addRow("Material", self.material_rvmat)
        layout.addLayout(form)

        texture_field = self.material_texture.findChild(qt_widgets.QLineEdit) if self.material_texture is not None else None
        rvmat_field = self.material_rvmat.findChild(qt_widgets.QLineEdit) if self.material_rvmat is not None else None
        if texture_field is not None:
            texture_field.textChanged.connect(lambda *_: self._on_material_path_edited())
        if rvmat_field is not None:
            rvmat_field.textChanged.connect(lambda *_: self._on_material_path_edited())

        self.refresh_material_metadata()
        return widget

    def _build_selections_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = qt_widgets.QLabel("Filter and maintain Object Builder selections, proxy sets, and face/vertex flag sets.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        filters = qt_widgets.QHBoxLayout()
        self.selection_lod_filter = qt_widgets.QComboBox()
        self.selection_type_filter = qt_widgets.QComboBox()
        self.selection_type_filter.addItems(["All Types", "Selection", "Proxy", "Vertex Flag", "Face Flag"])
        self.selection_search = qt_widgets.QLineEdit()
        self.selection_search.setPlaceholderText("Search LOD, type, name, or Maya set")
        self.selection_lod_filter.currentIndexChanged.connect(lambda *_: self.refresh_selection_manager(False))
        self.selection_type_filter.currentIndexChanged.connect(lambda *_: self.refresh_selection_manager(False))
        self.selection_search.textChanged.connect(lambda *_: self.refresh_selection_manager(False))
        filters.addWidget(self.selection_lod_filter)
        filters.addWidget(self.selection_type_filter)
        filters.addWidget(self.selection_search)
        layout.addLayout(filters)

        self.selection_list = qt_widgets.QListWidget()
        self.selection_list.currentItemChanged.connect(lambda *_: _update_selection_details())
        self.selection_list.itemDoubleClicked.connect(lambda *_: _select_set_members())
        layout.addWidget(self.selection_list, 1)

        self.selection_details = qt_widgets.QLabel("Select a row to see details.")
        self.selection_details.setWordWrap(True)
        layout.addWidget(self.selection_details)

        first_row = qt_widgets.QHBoxLayout()
        for label, callback in (("Select", _select_set_members), ("Rename", _rename_selection_set), ("Create", _create_selection_set), ("Find", find_components_from_ui)):
            first_row.addWidget(_qt_button(label, callback))
        layout.addLayout(first_row)

        second_row = qt_widgets.QHBoxLayout()
        for label, callback in (("Add Members", _add_to_selection_set), ("Remove Members", _remove_from_selection_set), ("Delete Set", _delete_selection_set), ("Clear OB", _clear_all_object_builder_sets)):
            second_row.addWidget(_qt_button(label, callback))
        layout.addLayout(second_row)

        self.refresh_selection_manager(True)
        return widget

    def _build_validation_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        label = qt_widgets.QLabel("Check Object Builder LODs before export. Scene checks every LOD; Selection checks only selected LODs/components.")
        label.setWordWrap(True)
        layout.addWidget(label)
        buttons = qt_widgets.QHBoxLayout()
        buttons.addWidget(_qt_button("Scene", lambda: cmds.a3obValidate()))
        buttons.addWidget(_qt_button("Selection", lambda: cmds.a3obValidate(selectionOnly=True)))
        layout.addLayout(buttons)
        layout.addStretch()
        return widget

    def _placeholder_tab(self, title, message):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        label = qt_widgets.QLabel(message)
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()
        return widget

    def selected_lod_definition(self):
        index = self.lod_type_combo.currentIndex() if self.lod_type_combo is not None else 0
        lod_type = self.lod_type_combo.itemData(index) if self.lod_type_combo is not None else LOD_DEFINITIONS[0]["type"]
        for definition in LOD_DEFINITIONS:
            if definition["type"] == lod_type:
                return definition
        return LOD_DEFINITIONS[0]

    def auto_lod_settings(self):
        return {
            "preset": self.auto_lod_preset.currentText() if self.auto_lod_preset is not None else "QUADS",
            "first_lod": self.auto_lod_first.currentText() if self.auto_lod_first is not None else "LOD1",
            "resolution": self.auto_lod_resolution.isChecked() if self.auto_lod_resolution is not None else True,
            "geometry": self.auto_lod_geometry.isChecked() if self.auto_lod_geometry is not None else True,
            "memory": self.auto_lod_memory.isChecked() if self.auto_lod_memory is not None else False,
            "fire_geometry": self.auto_lod_fire.isChecked() if self.auto_lod_fire is not None else False,
            "view_geometry": self.auto_lod_view.isChecked() if self.auto_lod_view is not None else False,
            "geometry_type": self.auto_lod_geometry_type.currentText() if self.auto_lod_geometry_type is not None else "BOX",
            "fire_quality": self.auto_lod_fire_quality.value() if self.auto_lod_fire_quality is not None else 2,
        }

    def lod_resolution_value(self):
        return self.lod_resolution.value() if self.lod_resolution is not None else 1

    def model_cfg_import_path(self):
        field = self.model_cfg_import.findChild(qt_widgets.QLineEdit) if self.model_cfg_import is not None else None
        return field.text().strip() if field is not None else ""

    def model_cfg_export_path(self):
        field = self.model_cfg_export.findChild(qt_widgets.QLineEdit) if self.model_cfg_export is not None else None
        return field.text().strip() if field is not None else ""

    def mass_value(self):
        return self.mass_value_field.value() if self.mass_value_field is not None else 1.0

    def mass_mode(self):
        return self.mass_mode_combo.currentText() if self.mass_mode_combo is not None else "All vertices"

    def flag_component(self):
        return self.flag_component_combo.currentText() if self.flag_component_combo is not None else "Face"

    def flag_value(self):
        return self.flag_value_field.value() if self.flag_value_field is not None else 1

    def flag_name(self):
        return self.flag_name_field.text().strip() if self.flag_name_field is not None else "a3ob_flag"

    def proxy_path(self):
        field = self.proxy_path_field.findChild(qt_widgets.QLineEdit) if self.proxy_path_field is not None else None
        return field.text().strip() if field is not None else ""

    def proxy_index(self):
        return self.proxy_index_field.value() if self.proxy_index_field is not None else 1

    def proxy_from_selection(self):
        return self.proxy_from_selection_check.isChecked() if self.proxy_from_selection_check is not None else True

    def selected_named_property_lod(self):
        if self.named_lod_combo is None:
            return None
        label = self.named_lod_combo.currentText()
        lod = self.named_lods.get(label)
        return lod if _node_exists(lod) else None

    def named_property_name(self):
        return self.named_name_field.text().strip() if self.named_name_field is not None else ""

    def named_property_value(self):
        return self.named_value_field.text().strip() if self.named_value_field is not None else ""

    def named_property_preset(self):
        return self.named_preset_combo.currentText() if self.named_preset_combo is not None else ""

    def set_named_property_fields(self, name, value):
        if self.named_name_field is not None:
            self.named_name_field.setText(name)
        if self.named_value_field is not None:
            self.named_value_field.setText(value)

    def clear_named_property_fields(self):
        self.set_named_property_fields("", "")

    def refresh_named_property_lods(self):
        if self.named_lod_combo is None:
            return
        current = self.named_lod_combo.currentText()
        self.named_lod_combo.blockSignals(True)
        self.named_lod_combo.clear()
        self.named_lods = {}
        for lod in _lod_transforms():
            label = _lod_label(lod)
            self.named_lods[label] = lod
            self.named_lod_combo.addItem(label)
        if not self.named_lods:
            self.named_lod_combo.addItem("No Object Builder LODs")
        elif current in self.named_lods:
            self.named_lod_combo.setCurrentText(current)
        self.named_lod_combo.blockSignals(False)

    def refresh_named_properties(self, rebuild_lods=False):
        if self.named_list is None:
            return
        if rebuild_lods:
            self.refresh_named_property_lods()
        self.named_list.clear()
        self.named_items = {}
        lod = self.selected_named_property_lod()
        if not lod:
            self.clear_named_property_fields()
            return
        raw = _safe_get_attr(lod, "a3obProperties", "") or ""
        for name, value in _split_named_properties(raw):
            label = f"{name} = {value}"
            self.named_items[label] = (name, value)
            self.named_list.addItem(label)

    def select_named_property(self):
        current = self.named_list.currentItem() if self.named_list is not None else None
        if current is None:
            return
        name, value = self.named_items.get(current.text(), ("", ""))
        self.set_named_property_fields(name, value)

    def material_texture_path(self):
        field = self.material_texture.findChild(qt_widgets.QLineEdit) if self.material_texture is not None else None
        return _normalize_dayz_path(field.text()) if field is not None else ""

    def material_rvmat_path(self):
        field = self.material_rvmat.findChild(qt_widgets.QLineEdit) if self.material_rvmat is not None else None
        return _normalize_dayz_path(field.text()) if field is not None else ""

    def selected_material_metadata_item(self):
        current = self.material_list.currentItem() if self.material_list is not None else None
        if current is None:
            return None
        item = self.material_items.get(current.text())
        if not item:
            return None
        if not _node_exists(item["material_node"]) and not _valid_nodes(item["shading_groups"]):
            self.refresh_material_metadata()
            return None
        item["shading_groups"] = _valid_nodes(item["shading_groups"])
        return item

    def select_material_metadata(self):
        item = self.selected_material_metadata_item()
        if not item:
            return
        texture = self.material_texture.findChild(qt_widgets.QLineEdit) if self.material_texture is not None else None
        rvmat = self.material_rvmat.findChild(qt_widgets.QLineEdit) if self.material_rvmat is not None else None
        if texture is not None:
            texture.blockSignals(True)
            try:
                texture.setText(item["texture"])
            finally:
                texture.blockSignals(False)
        if rvmat is not None:
            rvmat.blockSignals(True)
            try:
                rvmat.setText(item["material"])
            finally:
                rvmat.blockSignals(False)

    def _on_material_path_edited(self):
        if self.material_list is None:
            return
        current = self.material_list.currentItem()
        if current is None:
            return
        item = _persist_selected_material_metadata()
        if item is None:
            return
        new_label = _material_metadata_label(item)
        old_label = current.text()
        if new_label == old_label:
            return
        current.setText(new_label)
        if hasattr(self, "material_items"):
            self.material_items.pop(old_label, None)
            self.material_items[new_label] = item

    def refresh_material_metadata(self):
        if self.material_list is None:
            return
        current = self.material_list.currentItem()
        prev_label = current.text() if current else None
        self.material_list.clear()
        self.material_items = {}
        items = _material_nodes_for_selection()
        if not items:
            self.material_list.addItem("Select a mesh, LOD, or faces to edit its DayZ materials")
            return
        line_h = self.material_list.fontMetrics().height()
        row_size = qt_core.QSize(0, line_h * 2 + 8) if qt_core is not None else None
        for item in items:
            label = _material_metadata_label(item)
            self.material_items[label] = item
            list_item = qt_widgets.QListWidgetItem(label)
            if row_size is not None:
                list_item.setSizeHint(row_size)
            self.material_list.addItem(list_item)
        if prev_label and qt_core is not None:
            matches = self.material_list.findItems(prev_label, qt_core.Qt.MatchExactly)
            if matches:
                self.material_list.setCurrentItem(matches[0])
                return
        if self.material_list.count() > 0:
            self.material_list.setCurrentRow(0)

    def selected_selection_set_node(self):
        current = self.selection_list.currentItem() if self.selection_list is not None else None
        if current is None:
            return None
        item = self.selection_items.get(current.text())
        set_node = item["node"] if item else None
        if not _node_exists(set_node):
            if current.text() in self.selection_items:
                del self.selection_items[current.text()]
            return None
        return set_node

    def set_selection_details(self, message):
        if self.selection_details is not None:
            self.selection_details.setText(message)

    def refresh_selection_lods(self, items):
        if self.selection_lod_filter is None:
            return
        current = self.selection_lod_filter.currentText()
        self.selection_lod_filter.blockSignals(True)
        self.selection_lod_filter.clear()
        self.selection_lod_filter.addItem("All LODs")
        lods = sorted({item["lod"] for item in items})
        self.selection_lod_filter.addItems(lods)
        if current in ["All LODs", *lods]:
            self.selection_lod_filter.setCurrentText(current)
        self.selection_lod_filter.blockSignals(False)

    def refresh_selection_manager(self, rebuild_lods=True):
        if self.selection_list is None:
            return
        items = _selection_sets()
        if rebuild_lods:
            self.refresh_selection_lods(items)
        lod_filter = self.selection_lod_filter.currentText() if self.selection_lod_filter is not None else "All LODs"
        type_filter = self.selection_type_filter.currentText() if self.selection_type_filter is not None else "All Types"
        search = self.selection_search.text().lower() if self.selection_search is not None else ""
        selected = self.selection_list.currentItem()
        selected_label = selected.text() if selected is not None else ""
        self.selection_list.clear()
        self.selection_items = {}
        for item in items:
            if lod_filter != "All LODs" and item["lod"] != lod_filter:
                continue
            if type_filter != "All Types" and item["kind"] != type_filter:
                continue
            searchable = f"{item['lod']} {item['kind']} {item['name']} {item['node']}".lower()
            if search and search not in searchable:
                continue
            label = f"{item['lod']} | {item['kind']} | {item['name']} | {item['node']}"
            self.selection_items[label] = item
            self.selection_list.addItem(label)
        matches = self.selection_list.findItems(selected_label, qt_core.Qt.MatchExactly) if selected_label else []
        if matches:
            self.selection_list.setCurrentItem(matches[0])
        else:
            self.set_selection_details("Select a row to see details.")
        _update_selection_details()

    def refresh_lod_assignment(self, *_):
        definition = self.selected_lod_definition()
        if self.lod_resolution is not None:
            self.lod_resolution.setEnabled(definition["has_resolution"])
            if not definition["has_resolution"]:
                self.lod_resolution.blockSignals(True)
                self.lod_resolution.setValue(definition["default_resolution"])
                self.lod_resolution.blockSignals(False)
        selected_lod = _selected_lod_transform()
        target = selected_lod or "No LOD selected; Create Empty LOD will create a new transform."
        if self.lod_context is not None:
            self.lod_context.setText(f"Target: {target}")
        if self.lod_preview is not None:
            self.lod_preview.setText(f"Will assign: {_lod_assignment_label(definition)}")


def _qt_workspace_parent(control):
    if not QT_AVAILABLE:
        return None
    pointer = omui.MQtUtil.findControl(control)
    if pointer is None:
        pointer = omui.MQtUtil.findLayout(control)
    if pointer is None:
        return None
    return wrapInstance(int(pointer), qt_widgets.QWidget)


def _build_qt_dock(control):
    global _qt_dock_widget
    parent = _qt_workspace_parent(control)
    if parent is None:
        return False
    _qt_dock_widget = MayaObjectBuilderDock(parent)
    layout = parent.layout()
    if layout is None:
        layout = qt_widgets.QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(_qt_dock_widget)
    _qt_dock_widget.show()
    return True


def _delete_qt_dock():
    global _qt_dock_widget
    widget = _active_qt_dock()
    if widget is not None:
        widget.setParent(None)
        widget.deleteLater()
    _qt_dock_widget = None


def _build_dock_contents():
    _ensure_script_path()
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _quick_action_bar([
        ("Import P3D", import_p3d, "Open a P3D through Maya's native Arma P3D importer."),
        ("Export P3D", export_p3d, "Export the current scene through Maya's native Arma P3D exporter."),
        ("Import CFG", import_model_cfg, "Import a model.cfg skeleton file."),
        ("Export CFG", export_model_cfg, "Export selected/root skeleton joints to model.cfg."),
        ("Validate Scene", lambda: cmds.a3obValidate(), "Validate all Object Builder LODs in the scene."),
        ("Validate Sel", lambda: cmds.a3obValidate(selectionOnly=True), "Validate selected Object Builder LODs."),
    ])
    tabs = cmds.tabLayout(innerMarginWidth=8, innerMarginHeight=8)

    lod_tab = _start_tab()
    cmds.text(label="MayaObjectBuilder", align="center", height=28)
    _build_lod_assignment_ui()
    _build_validation_ui()
    _end_tab()

    files_tab = _start_tab()
    _card("P3D", "Launch Maya's native Arma P3D import/export. Detailed P3D options remain in the file dialog option panel.")
    _action_row([
        ("Import P3D", import_p3d, "Import a P3D file through the native translator."),
        ("Export P3D", export_p3d, "Export the scene through the native translator."),
    ], columns=2)
    _end_card()
    _card("model.cfg", "Pick explicit config paths when you want fast skeleton import/export without hunting through menus.")
    _path_row("Import", MODEL_CFG_IMPORT_FIELD, "Select model.cfg to import", "Config (*.cfg)")
    _path_row("Export", MODEL_CFG_EXPORT_FIELD, "Choose model.cfg export path", "Config (*.cfg)", save=True)
    _action_row([
        ("Import", import_model_cfg_from_ui, "Import the selected model.cfg path."),
        ("Export", export_model_cfg_from_ui, "Export to the selected model.cfg path."),
    ], columns=2)
    _end_card()
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
    if QT_AVAILABLE and _build_qt_dock(control):
        _install_context_refresh_job(control)
        return control
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
    _delete_qt_dock()
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
