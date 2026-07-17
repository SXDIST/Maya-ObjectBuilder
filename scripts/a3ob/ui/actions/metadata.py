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


def _lod_mass_summary():
    """(total mass, vertex-value count) of the active LOD, or (None, 0) when none."""
    node = _selected_lod_transform()
    if not node:
        return None, 0
    raw = _safe_get_attr(node, "a3obMassValues", "") or ""
    values = []
    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            pass
    return sum(values), len(values)


def _lod_vertex_count(node):
    total = 0
    for shape in cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []:
        try:
            total += cmds.polyEvaluate(shape, vertex=True)
        except Exception:
            pass
    return total


def distribute_mass_evenly():
    load_plugin()
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD to distribute mass")
        return
    total, count = _lod_mass_summary()
    if not count or not total or total <= 0:
        cmds.warning("The LOD has no mass to distribute")
        return
    cmds.select(node, replace=True)
    with _undo_chunk("Distribute Mass Evenly"):
        cmds.a3obSetMass(value=total / count)
    _refresh_context_ui()


def mass_from_volume_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    density = dock.mass_density_field.value() if dock is not None and dock.mass_density_field is not None else 1000.0
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD")
        return
    count = _lod_vertex_count(node)
    if count <= 0:
        cmds.warning("The LOD has no vertices")
        return
    bbox = cmds.exactWorldBoundingBox(node)
    volume = max(0.0, bbox[3] - bbox[0]) * max(0.0, bbox[4] - bbox[1]) * max(0.0, bbox[5] - bbox[2])
    total = volume * density
    cmds.select(node, replace=True)
    with _undo_chunk("Mass From Volume"):
        cmds.a3obSetMass(value=total / count)
    _refresh_context_ui()


__all__ = [
    "apply_mass_from_ui",
    "clear_mass_from_ui",
    "apply_flag_from_ui",
    "create_proxy_from_ui",
    "distribute_mass_evenly",
    "mass_from_volume_from_ui",
]
