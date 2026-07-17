"""Plugin/menu entry points, dock lifecycle and the module singletons."""

import importlib
import sys
from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403


# scripts/ dir (…/scripts/a3ob/ui/entry.py -> parents[2] = scripts/), so the .mel
# option box and the sibling plug-ins/ folder resolve the same as the old monolith.
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "objectBuilderMenu.py"


MENU_NAME = "MayaObjectBuilderMenu"


PLUGIN_NAME = "MayaObjectBuilder"


TRANSLATOR_NAME = "Arma P3D"


DOCK_NAME = "MayaObjectBuilderWorkspaceControl"


_ui_script_jobs = {}  # event_name -> scriptJob id


_qt_dock_widget = None


def _plugin_path():
    # Pure-Python plugin: plug-ins/ is a sibling of scripts/ both in the repo and in
    # the installed Documents/maya/MayaObjectBuilder/ layout.
    return SCRIPT_PATH.parent.parent / "plug-ins" / "MayaObjectBuilder.py"


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
        selected = cmds.fileDialog2(fileMode=1, caption="Load MayaObjectBuilder.py")
        if selected:
            cmds.loadPlugin(selected[0])


def import_p3d():
    # Open Maya's native File > Import dialog (with the Arma P3D translator options),
    # rather than a custom flow. Native import merges the P3D into the current scene
    # without ever renaming it, so nothing turns the scene into a ".p3d project".
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("Import")')
    mel.eval("Import")
    _refresh_context_ui()


def export_p3d():
    # Open Maya's native File > Export All dialog (Export runtime command ->
    # `projectViewer ExportAll`). Native export writes the chosen path WITHOUT renaming
    # the current scene or switching the project — unlike the old file(rename=...) flow,
    # which left the scene named ".p3d" so the next Ctrl+S clobbered the exported model.
    load_plugin()
    mel.eval('mayaObjectBuilderP3DSetFileAction("Export")')
    mel.eval("Export")


def _validate_scene_no_flush():
    load_plugin()
    cmds.undoInfo(stateWithoutFlush=True)
    try:
        cmds.a3obValidate()
    finally:
        cmds.undoInfo(stateWithoutFlush=False)


def _validate_selection_no_flush():
    load_plugin()
    cmds.undoInfo(stateWithoutFlush=True)
    try:
        cmds.a3obValidate(selectionOnly=True)
    finally:
        cmds.undoInfo(stateWithoutFlush=False)


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
        cmds.undoInfo(stateWithoutFlush=True)
        try:
            cmds.a3obExportModelCfg(path=selected_path)
        finally:
            cmds.undoInfo(stateWithoutFlush=False)


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


def _refresh_context_ui():
    dock = _active_qt_dock()
    if dock is None:
        return
    dock.refresh_lod_assignment()
    dock.refresh_named_properties()
    dock.refresh_material_metadata()
    dock.refresh_selection_manager(True)


def _install_context_refresh_job(parent):
    global _ui_script_jobs
    _ui_script_jobs = {ev: jid for ev, jid in _ui_script_jobs.items()
                       if cmds.scriptJob(exists=jid)}
    for event in ("SelectionChanged", "Undo", "Redo", "SceneOpened", "NewSceneOpened"):
        if event in _ui_script_jobs:
            continue
        job = cmds.scriptJob(event=[event, _refresh_context_ui], parent=parent, protected=True)
        _ui_script_jobs[event] = job


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
    from a3ob.ui.dock import MayaObjectBuilderDock  # local import avoids an import cycle
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
        timer = getattr(widget, "_poll_timer", None)
        if timer is not None:
            timer.stop()  # stop the auto-refresh poll before teardown (avoids exit-time crashes)
        widget.setParent(None)
        widget.deleteLater()
    _qt_dock_widget = None


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
    if not (QT_AVAILABLE and _build_qt_dock(control)):
        cmds.warning("MayaObjectBuilder requires PySide6; UI could not be built.")
        return control
    _install_context_refresh_job(control)
    return control


def _kill_ui_script_jobs():
    global _ui_script_jobs
    for jid in list(_ui_script_jobs.values()):
        if cmds.scriptJob(exists=jid):
            cmds.scriptJob(kill=jid, force=True)
    _ui_script_jobs = {}


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


def install():
    load_plugin()
    return show_plugin_ui()


def uninstall():
    hide_plugin_ui()


if __name__ == "__main__":
    install()


__all__ = [
    "SCRIPT_PATH",
    "MENU_NAME",
    "PLUGIN_NAME",
    "TRANSLATOR_NAME",
    "DOCK_NAME",
    "_ui_script_jobs",
    "_qt_dock_widget",
    "_plugin_path",
    "_ensure_script_path",
    "_auto_lod_module",
    "load_plugin",
    "import_p3d",
    "export_p3d",
    "_validate_scene_no_flush",
    "_validate_selection_no_flush",
    "import_model_cfg",
    "export_model_cfg",
    "_prompt",
    "_active_qt_dock",
    "_refresh_context_ui",
    "_install_context_refresh_job",
    "_qt_workspace_parent",
    "_build_qt_dock",
    "_delete_qt_dock",
    "open_dock",
    "_kill_ui_script_jobs",
    "_remove_legacy_shelf_button",
    "show_plugin_ui",
    "hide_plugin_ui",
    "install",
    "uninstall",
]
