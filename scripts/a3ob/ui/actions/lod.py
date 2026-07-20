"""lod action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
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


def _mark_selection_as_lod(definition, resolution):
    """Mark the selection as a LOD, leaving the node's own name alone.

    ``a3obCreateLOD`` honours the ``name`` flag only when it creates a brand-new node, so
    an empty LOD still comes out as "Resolution_1" instead of "transform1" while an
    existing mesh keeps whatever its author called it.

    Renaming the marked mesh to the LOD name was tried and removed: a mesh called "helmet"
    became "Resolution_1", the names the rigger chose were gone, and marking a second mesh
    of the same type collided into a suffix. A tidy outliner is not worth that.
    """
    result = cmds.a3obCreateLOD(lodType=definition["type"], resolution=resolution,
                                name=_lod_node_name(definition, resolution))
    return result[0] if isinstance(result, (list, tuple)) and result else result


def assign_lod_to_selection():
    load_plugin()
    if not cmds.ls(selection=True):
        cmds.warning("Select a transform, mesh, or component before assigning LOD metadata")
        return
    with _undo_chunk("Create LOD"):
        definition = _selected_lod_definition()
        resolution = _lod_resolution_value(definition)
        _mark_selection_as_lod(definition, resolution)
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


def create_lod_type(lod_type, resolution=0):
    """Create a new empty LOD of a specific type (for the LOD list's Add menu)."""
    load_plugin()
    definition = next((d for d in LOD_DEFINITIONS if d["type"] == lod_type), LOD_DEFINITIONS[0])
    res = resolution if definition["has_resolution"] else definition["default_resolution"]
    with _undo_chunk("Add LOD"):
        cmds.select(clear=True)
        node = _mark_selection_as_lod(definition, res)
        if node and cmds.objExists(node):
            cmds.select(node, replace=True)
    _refresh_context_ui()
    return node


__all__ = [
    "_selected_lod_definition",
    "_lod_resolution_value",
    "_lod_assignment_label",
    "_refresh_lod_assignment_ui",
    "_lod_node_name",
    "_mark_selection_as_lod",
    "create_lod_type",
    "assign_lod_to_selection",
    "LOD_ATTRS",
    "_remove_lod_from_selection",
]
