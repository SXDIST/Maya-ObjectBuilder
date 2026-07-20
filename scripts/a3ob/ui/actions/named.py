"""named action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
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


def _selected_lod_transforms_all():
    """Every distinct LOD transform in the current selection (for batch operations)."""
    lods = []
    for node in cmds.ls(selection=True, long=True) or []:
        current = node.split(".", 1)[0]
        while current:
            if _is_lod_transform(current):
                if current not in lods:
                    lods.append(current)
                break
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            current = parents[0] if parents else ""
    return lods


def _apply_named_property_to_lod(lod, name, value):
    if not _ensure_string_attr(lod, "a3obProperties", "a3prop"):
        return False
    existing = _split_named_properties(_safe_get_attr(lod, "a3obProperties", "") or "")
    properties = [(key, val) for key, val in existing if key != name]
    properties.append((name, value))
    cmds.setAttr(lod + ".a3obProperties", _join_named_properties(properties), type="string")
    return True


def _set_named_property_value(name, value, batch=False):
    name = name.strip()
    value = value.strip()
    if not name:
        return False
    if batch:
        lods = _selected_lod_transforms_all()
    else:
        active = _selected_named_property_lod()
        lods = [active] if active else []
    if not lods:
        cmds.warning("Import a P3D or select a live Object Builder LOD")
        _refresh_named_properties(True)
        return False
    changed = 0
    with _undo_chunk("Set Named Property"):
        for lod in lods:
            if _apply_named_property_to_lod(lod, name, value):
                changed += 1
    if not changed:
        cmds.warning("Object Builder LOD was deleted")
    _refresh_named_properties()
    return changed > 0


def _commit_named_property_fields(*_):
    dock = _active_qt_dock()
    if dock is None:
        return
    batch = bool(getattr(dock, "named_batch_enabled", lambda: False)())
    _set_named_property_value(dock.named_property_name(), dock.named_property_value(), batch=batch)


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
