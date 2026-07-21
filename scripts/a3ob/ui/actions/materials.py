"""materials action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def _connected_material(shading_group):
    """The material (shader) node feeding ``shading_group``'s surfaceShader, if any.

    Thin wrapper over the scene-layer helper of the same shape (`_material_nodes_for_
    selection` in `a3ob.ui.scene.materials` needs the identical lookup) — kept as its own
    name here since callers in this module already refer to it that way.
    """
    return _material_feeding_shading_group(shading_group)


def write_material_metadata(node, texture, material):
    """Write the DayZ texture/rvmat paths onto ``node``'s shading network. No dock involved.

    ``node`` is whichever half of the shading network the caller has in hand — a shading
    engine or the material (shader) node feeding it — not necessarily a shading engine
    despite the parameter's original working-title name: the two are connected through
    ``surfaceShader``, and Maya's connections are traversed both ways by ``listConnections``,
    so starting from either one reaches the identical fan-out: the node itself, the material
    it resolves to (or that it already is), and every other shading engine sharing that same
    material. This reproduces the retired dock panel's old target set exactly when it is
    still a valid target set (see `_persist_selected_material_metadata`, removed in Phase 3d
    Task 5, for the one case where a future item shape could narrow it).

    Returns the set of node names actually written to, empty when every target was deleted.
    """
    texture = _normalize_dayz_path(texture)
    material = _normalize_dayz_path(material)
    all_targets = set()
    if _node_exists(node):
        if cmds.objectType(node, isType="shadingEngine"):
            all_targets.add(node)
            material_node = _connected_material(node)
        elif cmds.ls(node, materials=True):
            all_targets.add(node)
            material_node = node
        else:
            cmds.warning("%s is neither a shading engine nor a material" % (node,))
            material_node = None
        if _node_exists(material_node):
            all_targets.add(material_node)
            for sg in _valid_nodes(cmds.listConnections(material_node, type="shadingEngine") or []):
                all_targets.add(sg)
    written = set()
    for target in all_targets:
        if _set_material_metadata_on_node(target, texture, material):
            written.add(target)
    if written:
        from a3ob.ui.recent import remember_path
        remember_path("texture", texture)
        remember_path("rvmat", material)
    return written


def select_faces_for_shading_group(shading_group):
    """Select the faces ``shading_group`` is assigned to, on the currently selected mesh(es).
    Returns how many.

    The scope is read BEFORE selecting: this replaces the selection, and the panel rebuilds
    from whatever is selected, so computing the shapes afterwards would scope the result to
    its own output."""
    shapes = _mesh_shapes_from_selection()
    faces = faces_with_material([shading_group], shapes)
    if not faces:
        cmds.warning("%s is not assigned to any face of the selected mesh(es)"
                     % (_connected_material(shading_group) or "This material"))
        return 0
    cmds.select(faces, replace=True)
    return len(cmds.ls(faces, flatten=True) or [])


__all__ = [
    "_connected_material",
    "write_material_metadata",
    "select_faces_for_shading_group",
]
