from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel


MENU_NAME = "MayaObjectBuilderMenu"
PLUGIN_NAME = "MayaObjectBuilder"
TRANSLATOR_NAME = "Arma P3D"


def _plugin_path():
    return Path(__file__).resolve().parents[1] / "build" / "Debug" / "MayaObjectBuilder.mll"


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
            cmds.a3obSetMass(value=float(value))


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
    main_window = mel.eval("$tmp=$gMainWindow")
    if cmds.menu(MENU_NAME, exists=True):
        cmds.deleteUI(MENU_NAME)

    menu = cmds.menu(MENU_NAME, label="MayaObjectBuilder", parent=main_window, tearOff=True)
    cmds.menuItem(label="Load Plugin", parent=menu, command=lambda *_: load_plugin())
    cmds.menuItem(divider=True, parent=menu)
    cmds.menuItem(label="Import P3D", parent=menu, command=lambda *_: import_p3d())
    cmds.menuItem(label="Export P3D", parent=menu, command=lambda *_: export_p3d())
    cmds.menuItem(label="Import model.cfg", parent=menu, command=lambda *_: import_model_cfg())
    cmds.menuItem(label="Export model.cfg", parent=menu, command=lambda *_: export_model_cfg())
    cmds.menuItem(divider=True, parent=menu)
    cmds.menuItem(label="Create LOD", parent=menu, command=lambda *_: create_lod())
    cmds.menuItem(label="Set Mass", parent=menu, command=lambda *_: set_mass())
    cmds.menuItem(label="Create Proxy", parent=menu, command=lambda *_: create_proxy())
    cmds.menuItem(label="Validate", parent=menu, command=lambda *_: validate())
    return menu


if __name__ == "__main__":
    install()
