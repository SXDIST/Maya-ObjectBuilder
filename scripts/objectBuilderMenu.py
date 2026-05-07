from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


SCRIPT_PATH = Path(globals().get("__file__", r"C:\Users\targaryen\source\repos\maya\dayz-object-builder\scripts\objectBuilderMenu.py")).resolve()
MENU_NAME = "MayaObjectBuilderMenu"
PLUGIN_NAME = "MayaObjectBuilder"
TRANSLATOR_NAME = "Arma P3D"
DOCK_NAME = "MayaObjectBuilderWorkspaceControl"
SHELF_NAME = "MayaObjectBuilderShelf"

CONTEXT_SELECTED = "MayaObjectBuilderContextSelected"
CONTEXT_KIND = "MayaObjectBuilderContextKind"
STATUS_TEXT = "MayaObjectBuilderStatusText"
SELECTION_SCRIPT_JOB = None

LOD_TYPE_MENU = "MayaObjectBuilderLodTypeMenu"
LOD_RESOLUTION_FIELD = "MayaObjectBuilderLodResolutionField"
LOD_SIGNATURE_TEXT = "MayaObjectBuilderLodSignatureText"
LOD_COUNTS_TEXT = "MayaObjectBuilderLodCountsText"
LOD_RENAME_CHECK = "MayaObjectBuilderLodRenameCheck"

NAMED_PROPS_LIST = "MayaObjectBuilderNamedPropsList"
NAMED_PROP_NAME = "MayaObjectBuilderNamedPropName"
NAMED_PROP_VALUE = "MayaObjectBuilderNamedPropValue"

PROXY_LIST = "MayaObjectBuilderProxyList"
PROXY_PATH_FIELD = "MayaObjectBuilderProxyPathField"
PROXY_INDEX_FIELD = "MayaObjectBuilderProxyIndexField"

SELECTION_CREATE_TYPE_MENU = "MayaObjectBuilderSelectionCreateType"
SELECTION_CREATE_NAME_FIELD = "MayaObjectBuilderSelectionCreateName"
SELECTION_CREATE_FLAG_FIELD = "MayaObjectBuilderSelectionCreateFlag"

SELECTION_MANAGER_LIST = "MayaObjectBuilderSelectionList"
SELECTION_MANAGER_LOD_FILTER = "MayaObjectBuilderSelectionLodFilter"
SELECTION_MANAGER_TYPE_FILTER = "MayaObjectBuilderSelectionTypeFilter"
SELECTION_MANAGER_SEARCH = "MayaObjectBuilderSelectionSearch"
SELECTION_MANAGER_DETAILS = "MayaObjectBuilderSelectionDetails"

MATERIAL_TEXTURE_FIELD = "MayaObjectBuilderMaterialTexture"
MATERIAL_MATERIAL_FIELD = "MayaObjectBuilderMaterialMaterial"
MASS_VALUE_FIELD = "MayaObjectBuilderMassValue"
FLAG_NAME_FIELD = "MayaObjectBuilderFlagName"
FLAG_VALUE_FIELD = "MayaObjectBuilderFlagValue"
FLAG_COMPONENT_MENU = "MayaObjectBuilderFlagComponent"

_selection_manager_items = {}
_named_property_items = {}
_proxy_items = {}

LOD_TYPES = [
    ("Resolution", 0, True),
    ("View - Gunner", 1, False),
    ("View - Pilot", 2, False),
    ("View - Cargo", 3, True),
    ("Shadow Volume", 4, True),
    ("Edit", 5, True),
    ("Geometry", 6, False),
    ("Geometry Buoyancy", 7, False),
    ("Geometry PhysX", 8, False),
    ("Memory", 9, False),
    ("Land Contact", 10, False),
    ("Roadway", 11, False),
    ("Paths", 12, False),
    ("Hit-points", 13, False),
    ("View Geometry", 14, False),
    ("Fire Geometry", 15, False),
    ("View - Cargo Geometry", 16, True),
    ("View - Cargo Fire Geometry", 17, False),
    ("View - Commander", 18, False),
    ("View - Commander Geometry", 19, False),
    ("View - Commander Fire Geometry", 20, False),
    ("View - Pilot Geometry", 21, False),
    ("View - Pilot Fire Geometry", 22, False),
    ("View - Gunner Geometry", 23, False),
    ("View - Gunner Fire Geometry", 24, False),
    ("Sub Parts", 25, False),
    ("Shadow Volume - Cargo View", 26, True),
    ("Shadow Volume - Pilot View", 27, False),
    ("Shadow Volume - Gunner View", 28, False),
    ("Wreckage", 29, False),
    ("Underground (VBS)", 30, False),
    ("Groundlayer (VBS)", 31, False),
    ("Navigation (VBS)", 32, False),
    ("Unknown", -1, True),
]
LOD_BY_LABEL = {item[0]: item for item in LOD_TYPES}
LOD_BY_ID = {item[1]: item for item in LOD_TYPES}

LOD_SIGNATURES = {
    1: 1.0e3,
    2: 1.1e3,
    6: 1.0e13,
    7: 2.0e13,
    30: 3.0e13,
    8: 4.0e13,
    32: 5.0e13,
    9: 1.0e15,
    10: 2.0e15,
    11: 3.0e15,
    12: 4.0e15,
    13: 5.0e15,
    14: 6.0e15,
    15: 7.0e15,
    17: 9.0e15,
    18: 1.0e16,
    19: 1.1e16,
    20: 1.2e16,
    21: 1.3e16,
    22: 1.4e16,
    23: 1.5e16,
    24: 1.6e16,
    25: 1.7e16,
    27: 1.9e16,
    28: 2.0e16,
    29: 2.1e16,
    31: 1.3e4,
}

COMMON_NAMED_PROPERTIES = [
    ("autocenter", "0"),
    ("buoyancy", "1"),
    ("class", "house"),
    ("forcenotalpha", "1"),
    ("lodnoshadow", "1"),
    ("map", "house"),
    ("prefershadowvolume", "1"),
]

COMMON_PROXY_PATHS = [
    "proxy\\weapon",
    "proxy\\magazine",
    "proxy\\inventory",
    "proxy\\driver",
    "proxy\\cargo",
]


# Plugin / file operations

def _plugin_path():
    return SCRIPT_PATH.parents[1] / "build" / "Debug" / "MayaObjectBuilder.mll"


def _ensure_script_path():
    scripts_dir = str(SCRIPT_PATH.parent).replace("\\", "/")
    mel.eval('if (!stringArrayContains("' + scripts_dir + '", stringToStringArray(`getenv MAYA_SCRIPT_PATH`, ";"))) putenv MAYA_SCRIPT_PATH (`getenv MAYA_SCRIPT_PATH` + ";' + scripts_dir + '")')
    mel.eval('source "' + scripts_dir + '/mayaObjectBuilderP3DOptions.mel"')


def load_plugin():
    _ensure_script_path()
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        _set_status("Plugin already loaded.")
        return
    path = _plugin_path()
    if path.exists():
        cmds.loadPlugin(str(path))
        _set_status(f"Loaded {path.name}.")
    else:
        selected = cmds.fileDialog2(fileMode=1, caption="Load MayaObjectBuilder.mll")
        if selected:
            cmds.loadPlugin(selected[0])
            _set_status("Loaded selected plugin.")


def import_p3d():
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("Import")')
    selected = cmds.fileDialog2(fileMode=1, caption="Import P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.file(selected[0], i=True, type=TRANSLATOR_NAME, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")
        _set_status(f"Imported {Path(selected[0]).name}.")
        refresh_ui()


def export_p3d():
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("ExportAll")')
    selected = cmds.fileDialog2(fileMode=0, caption="Export P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.file(rename=selected[0])
        cmds.file(exportAll=True, force=True, type=TRANSLATOR_NAME)
        _set_status(f"Exported {Path(selected[0]).name}.")


def import_model_cfg():
    load_plugin()
    selected = cmds.fileDialog2(fileMode=1, caption="Import model.cfg", fileFilter="Config (*.cfg)")
    if selected:
        cmds.a3obImportModelCfg(path=selected[0])
        _set_status(f"Imported {Path(selected[0]).name}.")


def export_model_cfg():
    load_plugin()
    selected = cmds.fileDialog2(fileMode=0, caption="Export model.cfg", fileFilter="Config (*.cfg)")
    if selected:
        cmds.a3obExportModelCfg(path=selected[0])
        _set_status(f"Exported {Path(selected[0]).name}.")


# Generic helpers

def _prompt(title, message, default=""):
    result = cmds.promptDialog(title=title, message=message, text=str(default), button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
    if result != "OK":
        return None
    return cmds.promptDialog(query=True, text=True)


def _set_status(message):
    if cmds.text(STATUS_TEXT, exists=True):
        cmds.text(STATUS_TEXT, edit=True, label=message)


def _install_selection_script_job():
    global SELECTION_SCRIPT_JOB
    if cmds.about(batch=True):
        return
    if SELECTION_SCRIPT_JOB is not None and cmds.scriptJob(exists=SELECTION_SCRIPT_JOB):
        return
    SELECTION_SCRIPT_JOB = cmds.scriptJob(event=["SelectionChanged", lambda: refresh_ui()], protected=True)


def _kill_selection_script_job():
    global SELECTION_SCRIPT_JOB
    if SELECTION_SCRIPT_JOB is not None and cmds.scriptJob(exists=SELECTION_SCRIPT_JOB):
        cmds.scriptJob(kill=SELECTION_SCRIPT_JOB, force=True)
    SELECTION_SCRIPT_JOB = None


def _has_attr(node, attr):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery(attr, node=node, exists=True)


def _ensure_string_attr(node, attr, short_name):
    if not _has_attr(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, dataType="string")


def _ensure_bool_attr(node, attr, short_name):
    if not _has_attr(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, attributeType="bool")


def _ensure_int_attr(node, attr, short_name):
    if not _has_attr(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, attributeType="long")


def _ensure_double_attr(node, attr, short_name):
    if not _has_attr(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, attributeType="double")


def _get_string_attr(node, attr, default=""):
    if not _has_attr(node, attr):
        return default
    value = cmds.getAttr(f"{node}.{attr}")
    return value if value is not None else default


def _set_string_attr(node, attr, short_name, value):
    _ensure_string_attr(node, attr, short_name)
    cmds.setAttr(f"{node}.{attr}", value, type="string")


def _get_int_attr(node, attr, default=0):
    if not _has_attr(node, attr):
        return default
    value = cmds.getAttr(f"{node}.{attr}")
    return int(value) if value is not None else default


def _set_int_attr(node, attr, short_name, value):
    _ensure_int_attr(node, attr, short_name)
    cmds.setAttr(f"{node}.{attr}", int(value))


def _get_double_attr(node, attr, default=0.0):
    if not _has_attr(node, attr):
        return default
    value = cmds.getAttr(f"{node}.{attr}")
    return float(value) if value is not None else default


def _set_double_attr(node, attr, short_name, value):
    _ensure_double_attr(node, attr, short_name)
    cmds.setAttr(f"{node}.{attr}", float(value))


def _set_bool_attr(node, attr, short_name, value):
    _ensure_bool_attr(node, attr, short_name)
    cmds.setAttr(f"{node}.{attr}", bool(value))


def _selected_node():
    selected = cmds.ls(selection=True, long=False) or []
    if not selected:
        return None
    node = selected[0].split(".")[0]
    if cmds.objExists(node):
        return node
    return None


def _lod_from_selection():
    node = _selected_node()
    if not node:
        return None
    if _has_attr(node, "a3obIsLOD"):
        return node
    parents = cmds.listRelatives(node, parent=True, fullPath=False) or []
    for parent in parents:
        if _has_attr(parent, "a3obIsLOD"):
            return parent
    for ancestor in cmds.listRelatives(node, allParents=True, fullPath=False) or []:
        if _has_attr(ancestor, "a3obIsLOD"):
            return ancestor
    return None


def _context_kind(node):
    if not node:
        return "Nothing selected"
    if _has_attr(node, "a3obIsProxy"):
        return "Proxy"
    if _has_attr(node, "a3obIsLOD"):
        return "P3D LOD"
    if _has_attr(node, "a3obSelectionName"):
        return "Object Builder Set"
    if cmds.nodeType(node) == "mesh":
        return "Mesh Shape"
    if cmds.nodeType(node) == "transform":
        return "Transform"
    return cmds.nodeType(node)


def _safe_node_name(text):
    return text.replace(" ", "_").replace("-", "_").replace("/", "_").replace("\\", "_").replace(":", "_")


def _lod_signature(lod_type, resolution):
    if lod_type in (0, -1):
        return float(resolution)
    if lod_type == 3:
        return 1.2e3 + float(resolution)
    if lod_type == 4:
        return 1.0e4 + float(resolution)
    if lod_type == 5:
        return 2.0e4 + float(resolution)
    if lod_type == 16:
        return 8.0e15 + float(resolution) * 1.0e13
    if lod_type == 26:
        return 1.8e16 + float(resolution) * 1.0e13
    return LOD_SIGNATURES.get(lod_type, float(resolution))


def _lod_display_name(lod_type, resolution):
    label, _, has_resolution = LOD_BY_ID.get(lod_type, ("Unknown", -1, True))
    if has_resolution:
        return f"{label} {resolution}"
    return label


def _current_lod_label():
    if not cmds.optionMenu(LOD_TYPE_MENU, exists=True):
        return "Resolution"
    return cmds.optionMenu(LOD_TYPE_MENU, query=True, value=True)


def _set_option_menu_value(menu, value):
    if cmds.optionMenu(menu, exists=True):
        try:
            cmds.optionMenu(menu, edit=True, value=value)
        except RuntimeError:
            pass


# Legacy commands, still exposed through dock buttons

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
    _set_status(f"Created LOD {name}.")
    refresh_ui()


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
    refresh_ui()


def set_material():
    load_plugin()
    texture = _prompt("Set Material", "Texture path:", "")
    if texture is None:
        return
    material = _prompt("Set Material", "Material path:", "")
    if material is None:
        return
    cmds.a3obSetMaterial(texture=texture, material=material)
    _set_status("Applied material metadata.")


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
    _set_status(f"Created {component.lower()} flag set {name}.")
    refresh_ui()


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
    _set_status(f"Created proxy {path}.{index}.")
    refresh_ui()


def validate():
    load_plugin()
    mode = cmds.confirmDialog(title="Validate", message="Validate selected LODs only?", button=["Selection", "All", "Cancel"], defaultButton="All", cancelButton="Cancel", dismissString="Cancel")
    if mode == "Selection":
        cmds.a3obValidate(selectionOnly=True)
        _set_status("Validation finished for selection. See Script Editor for details.")
    elif mode == "All":
        cmds.a3obValidate()
        _set_status("Validation finished. See Script Editor for details.")


# Context / refresh

def refresh_ui():
    node = _selected_node()
    lod = _lod_from_selection()
    if cmds.text(CONTEXT_SELECTED, exists=True):
        cmds.text(CONTEXT_SELECTED, edit=True, label=f"Selected: {node or 'None'}")
    if cmds.text(CONTEXT_KIND, exists=True):
        cmds.text(CONTEXT_KIND, edit=True, label=f"Context: {_context_kind(node)}")
    _refresh_lod_panel(lod)
    _refresh_named_properties(lod)
    _refresh_proxy_panel(lod)
    _refresh_selection_manager()
    _set_status(f"Ready. Active LOD: {lod or 'None'}")


def _build_context_header():
    cmds.frameLayout(label="Context", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.text(CONTEXT_SELECTED, label="Selected: None", align="left")
    cmds.text(CONTEXT_KIND, label="Context: Nothing selected", align="left")
    cmds.setParent("..")
    cmds.setParent("..")


# LOD properties

def _build_lod_properties_ui():
    cmds.frameLayout(label="LOD Properties", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(90, 250), adjustableColumn=2)
    cmds.text(label="Type")
    cmds.optionMenu(LOD_TYPE_MENU, changeCommand=lambda *_: _update_lod_signature_preview())
    for label, _, _ in LOD_TYPES:
        cmds.menuItem(label=label)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(90, 250), adjustableColumn=2)
    cmds.text(label="Resolution")
    cmds.intField(LOD_RESOLUTION_FIELD, value=0, changeCommand=lambda *_: _update_lod_signature_preview())
    cmds.setParent("..")
    cmds.text(LOD_SIGNATURE_TEXT, label="Signature: 0", align="left")
    cmds.text(LOD_COUNTS_TEXT, label="Source: vertices 0, faces 0", align="left")
    cmds.checkBox(LOD_RENAME_CHECK, label="Rename node from LOD type", value=True)
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    cmds.button(label="Apply LOD Settings", command=lambda *_: _apply_lod_settings())
    cmds.button(label="Select Active LOD", command=lambda *_: _select_active_lod())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def _refresh_lod_panel(lod):
    if not cmds.optionMenu(LOD_TYPE_MENU, exists=True):
        return
    if not lod:
        _set_option_menu_value(LOD_TYPE_MENU, "Resolution")
        if cmds.intField(LOD_RESOLUTION_FIELD, exists=True):
            cmds.intField(LOD_RESOLUTION_FIELD, edit=True, value=0)
        if cmds.text(LOD_SIGNATURE_TEXT, exists=True):
            cmds.text(LOD_SIGNATURE_TEXT, edit=True, label="Signature: no active LOD")
        if cmds.text(LOD_COUNTS_TEXT, exists=True):
            cmds.text(LOD_COUNTS_TEXT, edit=True, label="Source: no active LOD")
        return
    lod_type = _get_int_attr(lod, "a3obLodType", 0)
    resolution = _get_int_attr(lod, "a3obResolution", 0)
    label = LOD_BY_ID.get(lod_type, ("Unknown", -1, True))[0]
    _set_option_menu_value(LOD_TYPE_MENU, label)
    cmds.intField(LOD_RESOLUTION_FIELD, edit=True, value=resolution)
    _update_lod_signature_preview()
    vertices = _get_int_attr(lod, "a3obSourceVertexCount", 0)
    faces = _get_int_attr(lod, "a3obSourceFaceCount", 0)
    signature = _get_double_attr(lod, "a3obResolutionSignature", _lod_signature(lod_type, resolution))
    cmds.text(LOD_COUNTS_TEXT, edit=True, label=f"Source: vertices {vertices}, faces {faces}, stored signature {signature:g}")


def _update_lod_signature_preview():
    if not cmds.text(LOD_SIGNATURE_TEXT, exists=True):
        return
    label = _current_lod_label()
    lod_type = LOD_BY_LABEL.get(label, ("Resolution", 0, True))[1]
    resolution = cmds.intField(LOD_RESOLUTION_FIELD, query=True, value=True) if cmds.intField(LOD_RESOLUTION_FIELD, exists=True) else 0
    signature = _lod_signature(lod_type, resolution)
    has_resolution = LOD_BY_LABEL.get(label, ("Resolution", 0, True))[2]
    cmds.text(LOD_SIGNATURE_TEXT, edit=True, label=f"Signature: {signature:g}")
    if cmds.intField(LOD_RESOLUTION_FIELD, exists=True):
        cmds.intField(LOD_RESOLUTION_FIELD, edit=True, enable=has_resolution)


def _apply_lod_settings():
    lod = _lod_from_selection()
    if not lod:
        cmds.warning("Select a LOD transform before applying LOD settings")
        return
    label = _current_lod_label()
    lod_type = LOD_BY_LABEL.get(label, ("Resolution", 0, True))[1]
    resolution = cmds.intField(LOD_RESOLUTION_FIELD, query=True, value=True)
    signature = _lod_signature(lod_type, resolution)
    _set_bool_attr(lod, "a3obIsLOD", "a3lod", True)
    _set_int_attr(lod, "a3obLodType", "a3lt", lod_type)
    _set_int_attr(lod, "a3obResolution", "a3res", resolution)
    _set_double_attr(lod, "a3obResolutionSignature", "a3sig", signature)
    if cmds.checkBox(LOD_RENAME_CHECK, query=True, value=True):
        lod = cmds.rename(lod, _safe_node_name(_lod_display_name(lod_type, resolution)))
    cmds.select(lod, replace=True)
    _set_status(f"Applied LOD settings: {_lod_display_name(lod_type, resolution)}.")
    refresh_ui()


def _select_active_lod():
    lod = _lod_from_selection()
    if lod:
        cmds.select(lod, replace=True)
        refresh_ui()


# Named properties

def _parse_properties(raw):
    properties = []
    for item in raw.split(";"):
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
        else:
            key, value = item, ""
        properties.append((key, value))
    return properties


def _serialize_properties(properties):
    return ";".join(f"{key}={value}" for key, value in properties if key)


def _build_named_properties_ui():
    cmds.frameLayout(label="Named Properties", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.textScrollList(NAMED_PROPS_LIST, allowMultiSelection=False, height=130, selectCommand=lambda *_: _select_named_property())
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70, 260), adjustableColumn=2)
    cmds.text(label="Name")
    cmds.textField(NAMED_PROP_NAME)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70, 260), adjustableColumn=2)
    cmds.text(label="Value")
    cmds.textField(NAMED_PROP_VALUE)
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 120), (2, 120), (3, 120)])
    cmds.button(label="Add / Update", command=lambda *_: _upsert_named_property())
    cmds.button(label="Remove", command=lambda *_: _remove_named_property())
    cmds.button(label="Paste Common", command=lambda *_: _paste_common_named_property())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def _refresh_named_properties(lod):
    global _named_property_items
    if not cmds.textScrollList(NAMED_PROPS_LIST, exists=True):
        return
    cmds.textScrollList(NAMED_PROPS_LIST, edit=True, removeAll=True)
    _named_property_items = {}
    if not lod:
        cmds.textScrollList(NAMED_PROPS_LIST, edit=True, append="No active LOD selected")
        return
    properties = _parse_properties(_get_string_attr(lod, "a3obProperties", ""))
    if not properties:
        cmds.textScrollList(NAMED_PROPS_LIST, edit=True, append="No named properties on active LOD")
        return
    for key, value in properties:
        label = f"{key} = {value}"
        _named_property_items[label] = (key, value)
        cmds.textScrollList(NAMED_PROPS_LIST, edit=True, append=label)


def _selected_named_property():
    selected = cmds.textScrollList(NAMED_PROPS_LIST, query=True, selectItem=True) or []
    if not selected:
        return None
    return _named_property_items.get(selected[0])


def _select_named_property():
    item = _selected_named_property()
    if not item:
        return
    key, value = item
    cmds.textField(NAMED_PROP_NAME, edit=True, text=key)
    cmds.textField(NAMED_PROP_VALUE, edit=True, text=value)


def _upsert_named_property():
    lod = _lod_from_selection()
    if not lod:
        cmds.warning("Select a LOD before editing named properties")
        return
    key = cmds.textField(NAMED_PROP_NAME, query=True, text=True).strip()
    value = cmds.textField(NAMED_PROP_VALUE, query=True, text=True).strip()
    if not key:
        cmds.warning("Named property name cannot be empty")
        return
    load_plugin()
    cmds.a3obNamedProperty(set=(key, value))
    _set_status(f"Set named property {key} = {value}.")
    refresh_ui()


def _remove_named_property():
    lod = _lod_from_selection()
    item = _selected_named_property()
    if not lod or not item:
        cmds.warning("Select a named property to remove")
        return
    key, _ = item
    load_plugin()
    cmds.a3obNamedProperty(remove=key)
    _set_status(f"Removed named property {key}.")
    refresh_ui()


def _paste_common_named_property():
    buttons = [f"{key} = {value}" for key, value in COMMON_NAMED_PROPERTIES] + ["Cancel"]
    result = cmds.confirmDialog(title="Paste Common Named Property", message="Choose a common named property", button=buttons, cancelButton="Cancel", dismissString="Cancel")
    if result == "Cancel":
        return
    key, value = result.split(" = ", 1)
    cmds.textField(NAMED_PROP_NAME, edit=True, text=key)
    cmds.textField(NAMED_PROP_VALUE, edit=True, text=value)
    _upsert_named_property()


# Proxy access

def _proxy_display_name(path, index):
    if not path:
        path = "unknown"
    return f"{path} {index}"


def _proxy_nodes_for_lod(lod):
    proxies = []
    if not lod:
        return proxies
    descendants = cmds.listRelatives(lod, allDescendents=True, fullPath=False) or []
    for node in descendants:
        if _has_attr(node, "a3obIsProxy"):
            path = _get_string_attr(node, "a3obProxyPath", "")
            index = _get_int_attr(node, "a3obProxyIndex", 1)
            proxies.append({"node": node, "kind": "Placeholder", "path": path, "index": index})
    for node in cmds.ls(type="objectSet") or []:
        if _has_attr(node, "a3obIsProxySelection") and cmds.getAttr(f"{node}.a3obIsProxySelection"):
            name = _get_string_attr(node, "a3obSelectionName", "")
            if name.startswith("proxy:"):
                raw = name[len("proxy:"):]
                path, _, raw_index = raw.rpartition(".")
                try:
                    index = int(raw_index)
                except ValueError:
                    path, index = raw, 1
                proxies.append({"node": node, "kind": "Selection", "path": path, "index": index})
    return sorted(proxies, key=lambda item: (item["kind"], item["path"], item["index"], item["node"]))


def _build_proxy_access_ui():
    cmds.frameLayout(label="Proxy Access", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.textScrollList(PROXY_LIST, allowMultiSelection=False, height=120, selectCommand=lambda *_: _select_proxy_item(), doubleClickCommand=lambda *_: _select_proxy_node())
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70, 260), adjustableColumn=2)
    cmds.text(label="Path")
    cmds.textField(PROXY_PATH_FIELD)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(70, 260), adjustableColumn=2)
    cmds.text(label="Index")
    cmds.intField(PROXY_INDEX_FIELD, value=1)
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 120), (2, 120), (3, 120)])
    cmds.button(label="Create / Update", command=lambda *_: _create_or_update_proxy_from_panel())
    cmds.button(label="Select", command=lambda *_: _select_proxy_node())
    cmds.button(label="Remove", command=lambda *_: _remove_proxy_item())
    cmds.button(label="Browse Path", command=lambda *_: _browse_proxy_path())
    cmds.button(label="Paste Common", command=lambda *_: _paste_common_proxy_path())
    cmds.button(label="Clear Fields", command=lambda *_: _clear_proxy_fields())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def _refresh_proxy_panel(lod):
    global _proxy_items
    if not cmds.textScrollList(PROXY_LIST, exists=True):
        return
    cmds.textScrollList(PROXY_LIST, edit=True, removeAll=True)
    _proxy_items = {}
    if not lod:
        cmds.textScrollList(PROXY_LIST, edit=True, append="No active LOD selected")
        return
    proxies = _proxy_nodes_for_lod(lod)
    if not proxies:
        cmds.textScrollList(PROXY_LIST, edit=True, append="No proxies on active LOD")
        return
    for item in proxies:
        members = len(cmds.sets(item["node"], query=True) or []) if item["kind"] == "Selection" else "node"
        label = f"{item['kind']:<11} | {_proxy_display_name(item['path'], item['index']):<36} | {members} | {item['node']}"
        _proxy_items[label] = item
        cmds.textScrollList(PROXY_LIST, edit=True, append=label)


def _selected_proxy_item():
    selected = cmds.textScrollList(PROXY_LIST, query=True, selectItem=True) or []
    if not selected:
        return None
    return _proxy_items.get(selected[0])


def _select_proxy_item():
    item = _selected_proxy_item()
    if not item:
        return
    cmds.textField(PROXY_PATH_FIELD, edit=True, text=item["path"])
    cmds.intField(PROXY_INDEX_FIELD, edit=True, value=item["index"])


def _select_proxy_node():
    item = _selected_proxy_item()
    if not item:
        cmds.warning("Select a proxy row")
        return
    if item["kind"] == "Selection":
        members = cmds.sets(item["node"], query=True) or []
        cmds.select(members, replace=True)
    else:
        cmds.select(item["node"], replace=True)
    _set_status(f"Selected proxy {item['node']}.")


def _browse_proxy_path():
    selected = cmds.fileDialog2(fileMode=1, caption="Select Proxy P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.textField(PROXY_PATH_FIELD, edit=True, text=selected[0])


def _paste_common_proxy_path():
    result = cmds.confirmDialog(title="Paste Common Proxy", message="Choose a common proxy path", button=COMMON_PROXY_PATHS + ["Cancel"], cancelButton="Cancel", dismissString="Cancel")
    if result != "Cancel":
        cmds.textField(PROXY_PATH_FIELD, edit=True, text=result)


def _clear_proxy_fields():
    cmds.textField(PROXY_PATH_FIELD, edit=True, text="")
    cmds.intField(PROXY_INDEX_FIELD, edit=True, value=1)


def _create_or_update_proxy_from_panel():
    load_plugin()
    path = cmds.textField(PROXY_PATH_FIELD, query=True, text=True).strip()
    index = cmds.intField(PROXY_INDEX_FIELD, query=True, value=True)
    if not path:
        cmds.warning("Proxy path cannot be empty")
        return
    item = _selected_proxy_item()
    if item:
        cmds.select(item["node"], replace=True)
        cmds.a3obUpdateProxy(path=path, index=index)
        _set_status(f"Updated proxy {path}.{index}.")
    else:
        cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
        _set_status(f"Created proxy {path}.{index} from selected components.")
    refresh_ui()


def _remove_proxy_item():
    item = _selected_proxy_item()
    if not item:
        cmds.warning("Select a proxy row to remove")
        return
    result = cmds.confirmDialog(title="Remove Proxy", message=f"Remove {item['node']}?", button=["Remove", "Cancel"], defaultButton="Cancel", cancelButton="Cancel", dismissString="Cancel")
    if result != "Remove":
        return
    cmds.delete(item["node"])
    _set_status(f"Removed proxy {item['node']}.")
    refresh_ui()


# Selection manager

def _set_lod_label(node):
    raw = node.split(":")[-1]
    for marker in ("_SEL_", "_VERTEX_FLAG_", "_FACE_FLAG_", "_PROXY_"):
        if marker in raw:
            return raw.split(marker)[0].replace("_", " ")
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
        if _has_attr(node, "a3obSelectionName"):
            name = _get_string_attr(node, "a3obSelectionName", "")
            is_proxy = _has_attr(node, "a3obIsProxySelection") and cmds.getAttr(f"{node}.a3obIsProxySelection")
            flag_component = _get_string_attr(node, "a3obFlagComponent", "") if _has_attr(node, "a3obFlagComponent") else ""
            lod = _set_lod_label(node)
            members = len(cmds.sets(node, query=True) or [])
            sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod, "members": members})
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
    name = _get_string_attr(set_node, "a3obSelectionName", "")
    flag_component = _get_string_attr(set_node, "a3obFlagComponent", "") if _has_attr(set_node, "a3obFlagComponent") else ""
    is_proxy = _has_attr(set_node, "a3obIsProxySelection") and cmds.getAttr(f"{set_node}.a3obIsProxySelection")
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
    visible_count = 0
    for item in items:
        if lod_filter != "All LODs" and item["lod"] != lod_filter:
            continue
        if type_filter != "All Types" and item["kind"] != type_filter:
            continue
        searchable = f"{item['lod']} {item['kind']} {item['name']} {item['node']}".lower()
        if search and search not in searchable:
            continue
        label = f"{item['lod']:<18} | {item['kind']:<11} | {item['members']:<5} | {item['name']:<24} | {item['node']}"
        _selection_manager_items[label] = item
        cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, append=label)
        visible_count += 1
    if visible_count == 0:
        cmds.textScrollList(SELECTION_MANAGER_LIST, edit=True, append="No Object Builder selection sets match the current filters")
    _update_selection_details()


def _select_set_members():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a selection set in the MayaObjectBuilder Selection Manager")
        return
    members = cmds.sets(set_node, query=True) or []
    cmds.select(members, replace=True)
    _set_status(f"Selected {len(members)} members from {set_node}.")


def _rename_selection_set():
    set_node = _selected_selection_set()
    if not set_node:
        cmds.warning("Select a selection set in the MayaObjectBuilder Selection Manager")
        return
    old_name = _get_string_attr(set_node, "a3obSelectionName", "")
    new_name = _prompt("Rename Selection", "Object Builder selection name:", old_name)
    if not new_name:
        return
    _set_string_attr(set_node, "a3obSelectionName", "a3sn", new_name)
    node_name = set_node.split(":")[-1]
    prefix = node_name.split("_SEL_")[0] if "_SEL_" in node_name else node_name
    cmds.rename(set_node, prefix + "_SEL_" + _safe_node_name(new_name))
    _set_status(f"Renamed selection {old_name} to {new_name}.")
    refresh_ui()


def _create_selection_set():
    selection = cmds.ls(selection=True, flatten=True) or []
    if not selection:
        cmds.warning("Select mesh components before creating an Object Builder selection")
        return
    kind = cmds.optionMenu(SELECTION_CREATE_TYPE_MENU, query=True, value=True) if cmds.optionMenu(SELECTION_CREATE_TYPE_MENU, exists=True) else "Selection"
    name = cmds.textField(SELECTION_CREATE_NAME_FIELD, query=True, text=True).strip() if cmds.textField(SELECTION_CREATE_NAME_FIELD, exists=True) else ""
    if not name:
        name = _prompt("Create Selection", "Object Builder selection name:", "camo")
    if not name:
        return
    if kind == "Proxy Selection":
        load_plugin()
        index = cmds.intField(PROXY_INDEX_FIELD, query=True, value=True) if cmds.intField(PROXY_INDEX_FIELD, exists=True) else 1
        cmds.a3obProxy(path=name, index=index, fromSelection=True, update=True)
        _set_status(f"Created proxy selection proxy:{name}.{index}.")
    elif kind in ("Vertex Flag", "Face Flag"):
        load_plugin()
        value = cmds.intField(SELECTION_CREATE_FLAG_FIELD, query=True, value=True) if cmds.intField(SELECTION_CREATE_FLAG_FIELD, exists=True) else 1
        component = "vertex" if kind == "Vertex Flag" else "face"
        cmds.a3obSetFlag(component=component, value=value, name=name)
        _set_status(f"Created {component} flag set {name}.")
    else:
        set_node = cmds.sets(selection, name="a3ob_SEL_" + _safe_node_name(name))
        _set_string_attr(set_node, "a3obSelectionName", "a3sn", name)
        _set_status(f"Created selection {name}.")
    refresh_ui()


def _add_to_selection_set():
    set_node = _selected_selection_set()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not set_node or not selection:
        cmds.warning("Select a selection set and mesh components to add")
        return
    cmds.sets(selection, add=set_node)
    _set_status(f"Added {len(selection)} components to {set_node}.")
    refresh_ui()


def _remove_from_selection_set():
    set_node = _selected_selection_set()
    selection = cmds.ls(selection=True, flatten=True) or []
    if not set_node or not selection:
        cmds.warning("Select a selection set and mesh components to remove")
        return
    cmds.sets(selection, remove=set_node)
    _set_status(f"Removed {len(selection)} components from {set_node}.")
    refresh_ui()


def _build_selection_manager_ui():
    cmds.frameLayout(label="Selections", collapsable=False, marginWidth=8, marginHeight=6)
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
    cmds.text(label="LOD                | Type        | Count | OB Name                  | Maya set", align="left")
    cmds.textScrollList(SELECTION_MANAGER_LIST, allowMultiSelection=False, height=260, selectCommand=lambda *_: _update_selection_details(), doubleClickCommand=lambda *_: _select_set_members())
    cmds.text(SELECTION_MANAGER_DETAILS, label="Select a row to see details.", align="left")
    cmds.frameLayout(label="Create From Current Selection", collapsable=True, collapse=False, marginWidth=6, marginHeight=4)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="Type")
    cmds.optionMenu(SELECTION_CREATE_TYPE_MENU)
    for label in ("Selection", "Proxy Selection", "Vertex Flag", "Face Flag"):
        cmds.menuItem(label=label)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="Name / Path")
    cmds.textField(SELECTION_CREATE_NAME_FIELD, text="camo")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 250), adjustableColumn=2)
    cmds.text(label="Flag Value")
    cmds.intField(SELECTION_CREATE_FLAG_FIELD, value=1)
    cmds.setParent("..")
    cmds.button(label="Create Typed Set", command=lambda *_: _create_selection_set())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    cmds.button(label="Refresh", command=lambda *_: refresh_ui())
    cmds.button(label="Select Members", command=lambda *_: _select_set_members())
    cmds.button(label="Rename", command=lambda *_: _rename_selection_set())
    cmds.button(label="Add Selected Components", command=lambda *_: _add_to_selection_set())
    cmds.button(label="Remove Selected Components", command=lambda *_: _remove_from_selection_set())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def selection_manager():
    open_dock()


# Material / mass / flags / validation panels

def _build_material_ui():
    cmds.frameLayout(label="Material / Texture Metadata", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Texture")
    cmds.textField(MATERIAL_TEXTURE_FIELD)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Material")
    cmds.textField(MATERIAL_MATERIAL_FIELD)
    cmds.setParent("..")
    cmds.button(label="Apply To Selected Faces / Mesh", command=lambda *_: _apply_material_from_panel())
    cmds.setParent("..")
    cmds.setParent("..")


def _apply_material_from_panel():
    load_plugin()
    texture = cmds.textField(MATERIAL_TEXTURE_FIELD, query=True, text=True)
    material = cmds.textField(MATERIAL_MATERIAL_FIELD, query=True, text=True)
    cmds.a3obSetMaterial(texture=texture, material=material)
    _set_status("Applied material metadata to selection.")


def _build_mass_ui():
    cmds.frameLayout(label="Mass", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Value")
    cmds.floatField(MASS_VALUE_FIELD, value=1.0)
    cmds.setParent("..")
    cmds.rowColumnLayout(numberOfColumns=3, columnWidth=[(1, 120), (2, 120), (3, 120)])
    cmds.button(label="Set Selected", command=lambda *_: _apply_mass_from_panel(True))
    cmds.button(label="Set All", command=lambda *_: _apply_mass_from_panel(False))
    cmds.button(label="Clear", command=lambda *_: _clear_mass_from_panel())
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def _apply_mass_from_panel(selected_components):
    load_plugin()
    value = cmds.floatField(MASS_VALUE_FIELD, query=True, value=True)
    cmds.a3obSetMass(value=value, selectedComponents=selected_components)
    _set_status("Updated mass values.")
    refresh_ui()


def _clear_mass_from_panel():
    load_plugin()
    result = cmds.confirmDialog(title="Clear Mass", message="Clear mass values on selected LODs?", button=["Clear", "Cancel"], defaultButton="Cancel", cancelButton="Cancel", dismissString="Cancel")
    if result == "Clear":
        cmds.a3obSetMass(clear=True)
        _set_status("Cleared mass values.")
        refresh_ui()


def _build_flags_ui():
    cmds.frameLayout(label="Flag Sets", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Component")
    cmds.optionMenu(FLAG_COMPONENT_MENU)
    cmds.menuItem(label="Face")
    cmds.menuItem(label="Vertex")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Name")
    cmds.textField(FLAG_NAME_FIELD, text="a3ob_flag")
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 260), adjustableColumn=2)
    cmds.text(label="Value")
    cmds.intField(FLAG_VALUE_FIELD, value=1)
    cmds.setParent("..")
    cmds.button(label="Create Flag Set From Selection", command=lambda *_: _create_flag_from_panel())
    cmds.setParent("..")
    cmds.setParent("..")


def _create_flag_from_panel():
    load_plugin()
    component = cmds.optionMenu(FLAG_COMPONENT_MENU, query=True, value=True).lower()
    value = cmds.intField(FLAG_VALUE_FIELD, query=True, value=True)
    name = cmds.textField(FLAG_NAME_FIELD, query=True, text=True)
    cmds.a3obSetFlag(component=component, value=value, name=name)
    _set_status(f"Created {component} flag set {name}.")
    refresh_ui()


def _build_validation_ui():
    cmds.frameLayout(label="Validation", collapsable=False, marginWidth=8, marginHeight=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=6)
    cmds.text(label="Validation output is currently written to Script Editor.", align="left")
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    cmds.button(label="Validate Selected", command=lambda *_: _validate_from_panel(True))
    cmds.button(label="Validate All", command=lambda *_: _validate_from_panel(False))
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")


def _validate_from_panel(selection_only):
    load_plugin()
    if selection_only:
        cmds.a3obValidate(selectionOnly=True)
        _set_status("Validation finished for selection. See Script Editor.")
    else:
        cmds.a3obValidate()
        _set_status("Validation finished. See Script Editor.")


# Dock construction

def _two_column_buttons(items):
    cmds.rowColumnLayout(numberOfColumns=2, columnWidth=[(1, 180), (2, 180)])
    for label, command in items:
        cmds.button(label=label, command=lambda *_, fn=command: fn())
    cmds.setParent("..")


def _build_files_tab():
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_context_header()
    cmds.frameLayout(label="P3D / model.cfg", collapsable=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Import P3D", import_p3d),
        ("Export P3D", export_p3d),
        ("Import model.cfg", import_model_cfg),
        ("Export model.cfg", export_model_cfg),
    ])
    cmds.setParent("..")
    _build_validation_ui()
    cmds.setParent("..")


def _build_lod_tab():
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_context_header()
    _build_lod_properties_ui()
    _build_named_properties_ui()
    _build_proxy_access_ui()
    cmds.setParent("..")


def _build_tools_tab():
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_context_header()
    cmds.frameLayout(label="Create", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Create LOD", create_lod),
        ("Create Proxy", create_proxy),
    ])
    cmds.setParent("..")
    _build_material_ui()
    _build_mass_ui()
    _build_flags_ui()
    cmds.setParent("..")


def _build_dock_contents():
    load_plugin()
    root = cmds.formLayout()
    title = cmds.text(label="MayaObjectBuilder", align="center", height=26)
    status = cmds.text(STATUS_TEXT, label="Ready.", align="left", height=22)
    tabs = cmds.tabLayout(innerMarginWidth=6, innerMarginHeight=6)

    cmds.setParent(tabs)
    files_tab = cmds.scrollLayout(childResizable=True)
    _build_files_tab()
    cmds.setParent(tabs)

    lod_tab = cmds.scrollLayout(childResizable=True)
    _build_lod_tab()
    cmds.setParent(tabs)

    selections_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_context_header()
    _build_selection_manager_ui()
    cmds.setParent(selections_tab)
    cmds.setParent(tabs)

    tools_tab = cmds.scrollLayout(childResizable=True)
    _build_tools_tab()
    cmds.setParent(tabs)

    cmds.tabLayout(tabs, edit=True, tabLabel=[(files_tab, "Files"), (lod_tab, "LOD"), (selections_tab, "Selections"), (tools_tab, "Tools")])
    cmds.setParent(root)
    cmds.formLayout(
        root,
        edit=True,
        attachForm=[
            (title, "top", 0),
            (title, "left", 0),
            (title, "right", 0),
            (tabs, "left", 0),
            (tabs, "right", 0),
            (status, "left", 6),
            (status, "right", 0),
            (status, "bottom", 0),
        ],
        attachControl=[
            (tabs, "top", 0, title),
            (tabs, "bottom", 0, status),
        ],
    )
    cmds.setParent("..")
    _install_selection_script_job()
    refresh_ui()


def open_dock():
    if cmds.about(batch=True):
        return None
    if cmds.workspaceControl(DOCK_NAME, exists=True):
        cmds.workspaceControl(DOCK_NAME, edit=True, restore=True, visible=True)
        refresh_ui()
        return DOCK_NAME
    control = cmds.workspaceControl(DOCK_NAME, label="MayaObjectBuilder", retain=False, initialWidth=460, minimumWidth=420)
    for target in ("AttributeEditor", "AttributeEditorWorkspaceControl", "ChannelBoxLayerEditor"):
        if cmds.workspaceControl(target, exists=True):
            cmds.workspaceControl(DOCK_NAME, edit=True, tabToControl=(target, -1))
            break
    cmds.setParent(control)
    _build_dock_contents()
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
