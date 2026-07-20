"""Plugin/menu entry points, dock lifecycle and the module singletons."""

import sys
from pathlib import Path

import maya.cmds as cmds
import maya.mel as mel

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui._undo import _undo_suspended
# No cycle: a3ob.ui.scene.lods only reaches maya.cmds + a3ob.ui.constants + attrs.
from a3ob.ui.scene.lods import _selected_lod_transform  # noqa: F401


# scripts/ dir (…/scripts/a3ob/ui/entry.py -> parents[2] = scripts/), so the .mel
# option box and the sibling plug-ins/ folder resolve the same as the old monolith.
SCRIPT_PATH = Path(__file__).resolve().parents[2] / "objectBuilderMenu.py"


MENU_NAME = "MayaObjectBuilderMenu"


PLUGIN_NAME = "MayaObjectBuilder"


TRANSLATOR_NAME = "Arma P3D"


DOCK_NAME = "MayaObjectBuilderWorkspaceControl"


_ui_script_jobs = {}  # event_name -> scriptJob id


_context_refresh_timer = None  # debounce for SelectionChanged


_last_context_key = None  # LOD the dock was last rebuilt for


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
    # Pre-select "Arma P3D" in the dialog's "Files of type" (Maya's native Import dialog
    # otherwise defaults to the last-used type, e.g. Maya Binary/FBX).
    cmds.optionVar(stringValue=("defaultFileImportType", TRANSLATOR_NAME))
    mel.eval('mayaObjectBuilderP3DSetFileAction("Import")')
    mel.eval("Import")
    _refresh_context_ui()


def export_p3d():
    # Open Maya's native File > Export All dialog (Export runtime command ->
    # `projectViewer ExportAll`). Native export writes the chosen path WITHOUT renaming
    # the current scene or switching the project — unlike the old file(rename=...) flow,
    # which left the scene named ".p3d" so the next Ctrl+S clobbered the exported model.
    load_plugin()
    # Pre-select "Arma P3D" in the Export All dialog's "Files of type".
    cmds.optionVar(stringValue=("defaultFileExportAllType", TRANSLATOR_NAME))
    mel.eval('mayaObjectBuilderP3DSetFileAction("Export")')
    mel.eval("Export")


def _validate_scene_no_flush():
    load_plugin()
    with _undo_suspended():
        cmds.a3obValidate()


def _run_validation(selection_only):
    """Run a3obValidate and return its issue rows ("severity|node|message") for the panel."""
    load_plugin()
    with _undo_suspended():
        return cmds.a3obValidate(selectionOnly=selection_only) or []


def _run_skin_weights():
    """Select skin-weight outlier vertices; returns how many were found."""
    load_plugin()
    result = cmds.a3obSkinWeights()
    # MPxCommand.setResult comes back as a 1-element list under mayapy.
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _transfer_skin(distance):
    """Copy DayZ weights from the reference body onto the selected garments."""
    load_plugin()
    result = cmds.a3obTransferSkin(distance=distance)
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _test_pose():
    """Bend the rig and select vertices that deform unlike their neighbours."""
    load_plugin()
    result = cmds.a3obTestPose()
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _list_influences():
    """Influence names of the selected mesh's skinCluster."""
    load_plugin()
    result = cmds.a3obInfluence(listInfluences=True)
    if result is None:
        return []
    if isinstance(result, str):
        return [result]
    return list(result)


def _remove_influences(names):
    """Remove the named influences from the selected mesh. Returns how many went."""
    load_plugin()
    if not names:
        return 0
    result = cmds.a3obInfluence(removeInfluences=",".join(names))
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _paint_influence(name):
    """Point Paint Skin Weights at one bone, so clicking the dock list matches clicking
    the tool's own list. Silently does nothing when the paint tool is not active."""
    load_plugin()
    try:
        from a3ob.mayabridge.commands.influence import set_paint_influence
        return bool(set_paint_influence(name))
    except Exception:  # noqa: BLE001 - a highlight must never break the panel
        return False


def _select_influence_vertices(name):
    """Select the vertices one influence drives. Returns how many."""
    load_plugin()
    result = cmds.a3obInfluence(selectVertices=name)
    if isinstance(result, (list, tuple)):
        result = result[0] if result else 0
    return int(result or 0)


def _add_reference_asset(kind):
    load_plugin()
    cmds.a3obReference(kind=kind)


def _save_reference_asset(kind):
    load_plugin()
    cmds.a3obReference(kind=kind, store="1")


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
        with _undo_suspended():
            cmds.a3obExportModelCfg(path=selected_path)


def set_texture_root_from_ui():
    """Prompt for the .paa texture root (P-drive / mod folder), store it, and texture any
    already-imported materials that were waiting for it."""
    from a3ob.mayabridge import paatex
    current = paatex.texture_root()
    kwargs = {"fileMode": 3, "caption": "Select the .paa texture root (P-drive / mod folder)"}
    if current:
        kwargs["startingDirectory"] = current
    selected = cmds.fileDialog2(**kwargs)
    if not selected:
        return
    paatex.set_texture_root(selected[0])
    count = paatex.assign_pending_textures()
    mel.eval('print "MayaObjectBuilder: texture root set — textured %d material(s)\\n"' % count)


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


def _context_key():
    """What the dock actually shows: the selected LOD transform AND the selected object.

    Most panels are rebuilt from the LOD alone, so picking components *inside* a LOD cannot
    change them — and `objectsOnly` collapses every component of one mesh down to that mesh,
    so a marquee drag across vertices leaves the key untouched and still costs no rebuild.

    The object belongs in the key because the Influences panel follows the selected MESH,
    not the LOD. Two garments parented under one LOD carry different bones, and keying on
    the LOD alone left that panel showing the previous mesh's list — or nothing at all until
    the user typed into the filter box and cleared it again, which was the only thing that
    called the refresh directly."""
    try:
        lod = _selected_lod_transform() or ""
    except Exception:  # noqa: BLE001 - a refresh must never break selection
        lod = ""
    try:
        objects = cmds.ls(selection=True, objectsOnly=True, long=True) or []
        node = objects[0] if objects else ""
        # Selecting a transform yields the transform; selecting its components yields the
        # SHAPE. Collapsing the shape to its parent makes those two the same key, which is
        # what keeps component picking at zero rebuilds — the object here is only meant to
        # distinguish one mesh from another, never one component pick from the next.
        if node and cmds.nodeType(node) != "transform":
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            node = parents[0] if parents else node
    except Exception:  # noqa: BLE001 - same
        node = ""
    return (lod, node)


def _refresh_context_ui(force=True):
    """Rebuild the dock panels. ``force=False`` skips the work when the shown LOD has not
    changed — this is what makes component selection cheap (see _schedule_context_refresh)."""
    global _last_context_key
    dock = _active_qt_dock()
    if dock is None:
        return
    key = _context_key()
    if not force and key == _last_context_key:
        return
    _last_context_key = key
    dock.refresh_lod_list()
    dock.refresh_lod_assignment()
    dock.refresh_named_properties()
    dock.refresh_material_metadata()
    dock.refresh_selection_manager(True)
    dock.refresh_mass_summary()
    dock.refresh_influences()


def _schedule_context_refresh():
    """Coalesce SelectionChanged into one deferred refresh.

    Maya fires SelectionChanged for every step of a marquee drag, and a full rebuild scans
    every objectSet in the scene — so reacting per event made component selection on a dense
    mesh crawl. Debounce, then let the ``force=False`` key check drop it entirely when the
    LOD did not change (the usual case while picking verts)."""
    global _context_refresh_timer
    if not QT_AVAILABLE or qt_core is None:
        _refresh_context_ui(False)
        return
    if _context_refresh_timer is None:
        _context_refresh_timer = qt_core.QTimer()
        _context_refresh_timer.setSingleShot(True)
        _context_refresh_timer.setInterval(150)
        _context_refresh_timer.timeout.connect(lambda: _refresh_context_ui(False))
    _context_refresh_timer.start()


def _install_context_refresh_job(parent):
    global _ui_script_jobs
    _ui_script_jobs = {ev: jid for ev, jid in _ui_script_jobs.items()
                       if cmds.scriptJob(exists=jid)}
    # Selection is debounced and key-checked; the rest change data outright, so they force.
    handlers = {
        "SelectionChanged": _schedule_context_refresh,
        "Undo": _refresh_context_ui,
        "Redo": _refresh_context_ui,
        "SceneOpened": _refresh_context_ui,
        "NewSceneOpened": _refresh_context_ui,
    }
    for event, handler in handlers.items():
        if event in _ui_script_jobs:
            continue
        job = cmds.scriptJob(event=[event, handler], parent=parent, protected=True)
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
    # KEEP lazy: dock imports from actions which imports from entry → cycle if moved to top.
    from a3ob.ui.dock import MayaObjectBuilderDock
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
        # Remove the Maya callbacks BEFORE the widget dies. One that outlives it would fire
        # into freed Python objects — this is the exit-time crash class.
        teardown = getattr(widget, "teardown", None)
        if callable(teardown):
            teardown()
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
        cmds.menuItem(divider=True, parent=menu)
        cmds.menuItem(label="Import model.cfg Skeleton", parent=menu, command=lambda *_: import_model_cfg())
        cmds.menuItem(label="Export model.cfg Skeleton", parent=menu, command=lambda *_: export_model_cfg())
        cmds.menuItem(divider=True, parent=menu)
        cmds.menuItem(label="Set Texture Root (.paa)…", parent=menu, command=lambda *_: set_texture_root_from_ui())
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
    "load_plugin",
    "import_p3d",
    "export_p3d",
    "_validate_scene_no_flush",
    "_run_validation",
    "_run_skin_weights",
    "_transfer_skin",
    "_test_pose",
    "_list_influences",
    "_remove_influences",
    "_select_influence_vertices",
    "_paint_influence",
    "_add_reference_asset",
    "_save_reference_asset",
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
