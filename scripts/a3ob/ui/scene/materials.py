"""Scene helper: materials domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
from a3ob.ui.scene.attrs import *  # noqa: F401,F403


def _mesh_shapes_from_selection():
    shapes = []
    seen = set()
    # NOT flatten=True: it expands "shape.vtx[0:5953]" into 5954 separate strings and this
    # loop then hits Maya once per vertex — 743 ms for one whole-mesh selection, on every
    # dock refresh. Unflattened, the same selection is a single entry (0.7 ms) and the
    # ".split()" below resolves it to exactly the same shapes.
    for item in cmds.ls(selection=True, long=True) or []:
        node = item.split(".", 1)[0]
        if not cmds.objExists(node):
            continue
        candidates = []
        if cmds.objectType(node, isType="mesh"):
            candidates.append(node)
        else:
            candidates.extend(cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or [])
            descendants = cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []
            candidates.extend(descendants)
        for shape in candidates:
            if shape not in seen:
                seen.add(shape)
                shapes.append(shape)
    return shapes


def _material_feeding_shading_group(shading_group):
    """The material (shader) node feeding ``shading_group``'s surfaceShader, if any."""
    if not _node_exists(shading_group):
        return ""
    materials = _valid_nodes(cmds.ls(
        cmds.listConnections(shading_group + ".surfaceShader") or [], materials=True) or [])
    return materials[0] if materials else ""


def faces_with_material(shading_groups, shapes):
    """The face components ``shading_groups`` are assigned to, within ``shapes``.

    A shading group's members come in two shapes and only one of them is components: assign
    a material to a whole mesh — the normal case for a single-material LOD — and the member
    is the SHAPE, so reading `cmds.sets(...)` alone answers "no faces" for the common case of
    a whole-mesh material assignment. Those get expanded to the mesh's full face range.

    Scoped to ``shapes`` (the caller's LOD, e.g. the DayZ Material section of the Attribute
    Editor) rather than the whole scene, so picking a helmet's material does not also select
    the body sharing that material."""
    wanted = set()
    for shape in shapes or []:
        wanted.update(cmds.ls(shape, long=True) or [])
    if not wanted:
        return []

    faces = []
    for group in _valid_nodes(list(shading_groups or [])):
        for member in cmds.sets(group, query=True) or []:
            node, _, component = member.partition(".")
            for resolved in _shape_paths(node):
                if resolved not in wanted:
                    continue
                if component:
                    faces.append(resolved + "." + component)
                else:
                    total = cmds.polyEvaluate(resolved, face=True)
                    if isinstance(total, int) and total > 0:
                        faces.append("%s.f[0:%d]" % (resolved, total - 1))
    return faces


def _shape_paths(node):
    """Every mesh shape ``node`` stands for — it may be a shape or its transform.

    Intermediate shapes are dropped. A skinned mesh keeps a hidden `...ShapeOrig`, and
    shading-group members name the TRANSFORM (`jacket.f[11143:13603]`), so resolving one to
    "its mesh shapes" hands back the orig shape too — measured, that selected 4922 faces on
    a 2461-face garment, every face twice, on components nothing can pick or export."""
    if not node or not cmds.objExists(node):
        return []
    if cmds.objectType(node, isType="mesh"):
        found = cmds.ls(node, long=True) or []
    else:
        found = cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []
    return [shape for shape in found if not _is_intermediate(shape)]


def _is_intermediate(shape):
    try:
        return bool(cmds.getAttr(shape + ".intermediateObject"))
    except (RuntimeError, ValueError):
        return False


def _set_material_metadata_on_node(node, texture, material):
    if not _node_exists(node):
        return False
    if not _ensure_string_attr(node, "a3obTexture", "a3tx") or not _ensure_string_attr(node, "a3obMaterial", "a3mt"):
        return False
    cmds.setAttr(node + ".a3obTexture", texture, type="string")
    cmds.setAttr(node + ".a3obMaterial", material, type="string")
    return True


__all__ = [
    "_mesh_shapes_from_selection",
    "_material_feeding_shading_group",
    "faces_with_material",
    "_set_material_metadata_on_node",
]
