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


def _shading_group_from_selection():
    """The shading engine implied by the CURRENT selection: a selected ``shadingEngine``
    itself, or the one a selected material feeds. ``""`` when neither is present.

    Reads the selection fresh on every call - this is the whole point of the resolver, since
    a node stored once (the retired in-AE approach) goes stale the instant the user selects
    something else, while re-reading the selection at call time never can."""
    selected = _valid_nodes(cmds.ls(selection=True, long=True) or [])
    for node in selected:
        if cmds.objectType(node, isType="shadingEngine"):
            return node
    for node in selected:
        if cmds.ls(node, materials=True):
            groups = _valid_nodes(cmds.listConnections(node, type="shadingEngine") or [])
            if groups:
                return groups[0]
    return ""


def select_faces_for_selected_material():
    """Select the faces the shading engine implied by the current selection is assigned to.
    Returns how many; 0 and a warning when the selection names no material, or when it names
    more than one and cannot be resolved without guessing.

    Menu replacement for the Select Faces button the AE section lost: ``editorTemplate
    -addControl`` renders only attribute fields, so this cannot live in that hook any more.

    Two selection shapes resolve, and they scope differently:

    * A selected shading engine, or a material feeding one - Hypershade's domain, and
      Hypershade can select objects by a material but never faces, so nothing upstream can be
      relied on to already have the right mesh(es) selected. The scope is rebuilt from the
      shading group's own members (whatever it is painted onto) before delegating to
      ``select_faces_for_shading_group``.
    * A selected mesh, transform, or face component - the most natural gesture there is:
      selecting the geometry you can see. Here the user's selection already IS the intended
      scope, so it is used as-is, never rebuilt - widening it to every object sharing the
      material would silently return more than was asked for. A mesh can carry more than one
      shading engine, so this case refuses to guess: several candidates warn (naming them)
      and select nothing rather than pick one arbitrarily."""
    shading_group = _shading_group_from_selection()
    if shading_group:
        transforms = []
        seen = set()
        for member in cmds.sets(shading_group, query=True) or []:
            node = member.partition(".")[0]
            if node and node not in seen and _node_exists(node):
                seen.add(node)
                transforms.append(node)
        if transforms:
            # noExpand: a plain mesh transform is unaffected, but `cmds.select` expands a SET
            # passed to it into its members rather than selecting the set node itself - the
            # mistake that bit twice in Phase 3b, once in production code.
            cmds.select(transforms, replace=True, noExpand=True)
        return select_faces_for_shading_group(shading_group)

    groups = _shading_groups_assigned_to_selection()
    if len(groups) == 1:
        # The selection IS the scope here - do NOT rebuild it from the shading group's other
        # members, unlike the branch above. That rebuild is correct when nothing upstream had
        # the right geometry selected; here the user already pointed at exactly the geometry
        # they meant.
        return select_faces_for_shading_group(groups[0])
    if len(groups) > 1:
        names = sorted(_connected_material(group) or group for group in groups)
        cmds.warning(
            "Selection carries more than one material (%s) - select a face of the one you "
            "want, or select the material itself" % ", ".join(names))
        return 0

    cmds.warning("Select a DayZ shading engine, or a material feeding one, first")
    return 0


__all__ = [
    "_connected_material",
    "write_material_metadata",
    "select_faces_for_shading_group",
    "select_faces_for_selected_material",
]
