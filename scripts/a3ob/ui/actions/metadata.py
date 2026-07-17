"""metadata action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


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
    from a3ob.ui.recent import remember_path
    remember_path("proxy", path)


__all__ = [
    "apply_mass_from_ui",
    "clear_mass_from_ui",
    "apply_flag_from_ui",
    "create_proxy_from_ui",
]
