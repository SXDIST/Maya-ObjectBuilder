"""named action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


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


__all__ = [
    "_selected_named_property_lod",
    "_refresh_named_properties",
    "_set_named_property_value",
    "_commit_named_property_fields",
    "_remove_named_property",
]
