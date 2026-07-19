"""materials action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _refresh_material_metadata():
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_material_metadata()


def _selected_material_metadata_item():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_material_metadata_item()
    return None


def _persist_selected_material_metadata():
    item = _selected_material_metadata_item()
    if not item:
        return None
    dock = _active_qt_dock()
    if dock is None:
        return None
    texture = _normalize_dayz_path(dock.material_texture_path())
    material = _normalize_dayz_path(dock.material_rvmat_path())
    changed = False
    all_targets = set(item["shading_groups"])
    if _node_exists(item["material_node"]):
        all_targets.add(item["material_node"])
        for sg in _valid_nodes(cmds.listConnections(item["material_node"], type="shadingEngine") or []):
            all_targets.add(sg)
    for target in all_targets:
        changed = _set_material_metadata_on_node(target, texture, material) or changed
    if not changed:
        cmds.warning("Material metadata target was deleted")
        return None
    item["texture"] = texture
    item["material"] = material
    from a3ob.ui.recent import remember_path
    remember_path("texture", texture)
    remember_path("rvmat", material)
    return item


def select_faces_with_material():
    """Select the faces the highlighted material is assigned to. Returns how many.

    The scope is read BEFORE selecting: this replaces the selection, and the panel rebuilds
    from whatever is selected, so computing the shapes afterwards would scope the result to
    its own output."""
    item = _selected_material_metadata_item()
    if not item:
        cmds.warning("Pick a material in the list first")
        return 0
    shapes = _mesh_shapes_from_selection()
    faces = faces_with_material(item["shading_groups"], shapes)
    if not faces:
        cmds.warning("%s is not assigned to any face of the selected mesh(es)"
                     % (item["material_node"] or "This material"))
        return 0
    cmds.select(faces, replace=True)
    return len(cmds.ls(faces, flatten=True) or [])


__all__ = [
    "_refresh_material_metadata",
    "_selected_material_metadata_item",
    "_persist_selected_material_metadata",
    "select_faces_with_material",
]
