"""lod action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.constants import _lod_definition_for_type  # noqa: F401
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _lod_assignment_label(definition, resolution):
    if definition["has_resolution"]:
        return f"{definition['label']} {resolution}"
    return definition["label"]


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


def _mark_node_as_lod(node, definition, resolution):
    """Mark a SPECIFIC node as a LOD, never the current selection.

    ``a3obCreateLOD`` (what ``_mark_selection_as_lod`` calls) has no node-targeting flag —
    it always acts on whatever is selected. Per-row editors in the LOD list must write to
    the node of their OWN row, captured when the editor was built, never to
    ``_selected_lod_transform()``: a measured scene had ``|helmet``,
    ``|group1|body|Resolution_2`` and ``|group1|body|Resolution_1`` all reading
    "Resolution 1", so "the selected LOD" stopped being a safe target the moment more than
    one row can be edited. The current selection is saved and restored around the call so
    this is invisible to the user and to anything reacting to SelectionChanged.
    """
    if not node or not cmds.objExists(node):
        return None
    original = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(node, replace=True)
        return _mark_selection_as_lod(definition, resolution)
    finally:
        if original:
            cmds.select(original, replace=True)
        else:
            cmds.select(clear=True)


def assign_lod_to_selection(lod_type=RESOLUTION_LOD_TYPE, resolution=None):
    """Mark the current selection as a LOD — the "Mark Selection as LOD" button.

    Defaults to a plain Resolution LOD: the button that triggers this has no
    type/resolution picker of its own (that lives on the tree's rows now), so this is
    the common case of "just mark this mesh". A caller that knows the type explicitly
    (none today, but kept for symmetry with create_lod_type) can still pass one.
    """
    load_plugin()
    if not cmds.ls(selection=True):
        cmds.warning("Select a transform, mesh, or component before assigning LOD metadata")
        return
    definition = _lod_definition_for_type(lod_type)
    res = resolution if resolution is not None else definition["default_resolution"]
    with _undo_chunk("Create LOD"):
        _mark_selection_as_lod(definition, res)
        _refresh_context_ui()


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
    definition = _lod_definition_for_type(lod_type)
    res = resolution if definition["has_resolution"] else definition["default_resolution"]
    with _undo_chunk("Add LOD"):
        cmds.select(clear=True)
        node = _mark_selection_as_lod(definition, res)
        if node and cmds.objExists(node):
            cmds.select(node, replace=True)
    _refresh_context_ui()
    return node


__all__ = [
    "_lod_assignment_label",
    "_lod_node_name",
    "_mark_selection_as_lod",
    "_mark_node_as_lod",
    "create_lod_type",
    "assign_lod_to_selection",
    "LOD_ATTRS",
    "_remove_lod_from_selection",
]
