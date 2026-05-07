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
_selection_manager_items = {}


def _plugin_path():
    return SCRIPT_PATH.parents[1] / "build" / "Debug" / "MayaObjectBuilder.mll"


def load_plugin():
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
    selected = cmds.fileDialog2(fileMode=1, caption="Import P3D", fileFilter="P3D (*.p3d)")
    if selected:
        cmds.file(selected[0], i=True, type=TRANSLATOR_NAME, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace="p3d")


def export_p3d():
    load_plugin()
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
    texture = _prompt("Set Material", "Texture path:", "")
    if texture is None:
        return
    material = _prompt("Set Material", "Material path:", "")
    if material is None:
        return
    cmds.a3obSetMaterial(texture=texture, material=material)


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
    cmds.button(label="Refresh", command=lambda *_: _refresh_selection_manager())
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
    cmds.frameLayout(label="P3D / model.cfg", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Import P3D", import_p3d),
        ("Export P3D", export_p3d),
        ("Import model.cfg", import_model_cfg),
        ("Export model.cfg", export_model_cfg),
    ])
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")

    tools_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    cmds.frameLayout(label="LOD Tools", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Create LOD", create_lod),
        ("Validate", validate),
    ])
    cmds.setParent("..")
    cmds.frameLayout(label="Object Builder Metadata", collapsable=True, collapse=False, marginWidth=8, marginHeight=6)
    _two_column_buttons([
        ("Set Mass", set_mass),
        ("Set Material", set_material),
        ("Set Flag", set_flag),
        ("Create Proxy", create_proxy),
    ])
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setParent("..")

    selections_tab = cmds.scrollLayout(childResizable=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=8)
    _build_selection_manager_ui()
    cmds.setParent("..")
    cmds.setParent("..")

    cmds.tabLayout(tabs, edit=True, tabLabel=[(files_tab, "Files"), (tools_tab, "Tools"), (selections_tab, "Selections")])
    cmds.setParent("..")
    _refresh_selection_manager()


def open_dock():
    if cmds.about(batch=True):
        return None
    if cmds.workspaceControl(DOCK_NAME, exists=True):
        cmds.workspaceControl(DOCK_NAME, edit=True, restore=True, visible=True)
        _refresh_selection_manager()
        return DOCK_NAME
    control = cmds.workspaceControl(DOCK_NAME, label="MayaObjectBuilder", retain=False, initialWidth=420, minimumWidth=360)
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
