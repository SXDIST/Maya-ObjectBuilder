"""lod action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _selected_lod_definition():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_lod_definition()
    return LOD_DEFINITIONS[0]


def _lod_resolution_value(definition):
    if not definition["has_resolution"]:
        return definition["default_resolution"]
    dock = _active_qt_dock()
    if dock is not None:
        return dock.lod_resolution_value()
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


def _lod_node_name(definition, resolution):
    label = _lod_assignment_label(definition, resolution)
    return label.replace(" ", "_").replace("/", "_")


def assign_lod_to_selection():
    load_plugin()
    if not cmds.ls(selection=True):
        cmds.warning("Select a transform, mesh, or component before assigning LOD metadata")
        return
    with _undo_chunk("Create LOD"):
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


LOD_ATTRS = (
    "a3obIsLOD", "a3obLodType", "a3obResolution",
    "a3obResolutionSignature", "a3obSourceVertexCount", "a3obSourceFaceCount",
)


def _remove_lod_from_selection():
    load_plugin()
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD transform to remove LOD status")
        return
    for attr in LOD_ATTRS:
        if cmds.attributeQuery(attr, node=node, exists=True):
            cmds.deleteAttr(node, attribute=attr)
    _refresh_context_ui()


def generate_auto_lods_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    generated = _auto_lod_module().generate_auto_lods(dock.auto_lod_settings())
    if generated:
        _refresh_context_ui()


__all__ = [
    "_selected_lod_definition",
    "_lod_resolution_value",
    "_lod_assignment_label",
    "_refresh_lod_assignment_ui",
    "_lod_node_name",
    "assign_lod_to_selection",
    "create_empty_lod",
    "LOD_ATTRS",
    "_remove_lod_from_selection",
    "generate_auto_lods_from_ui",
]
