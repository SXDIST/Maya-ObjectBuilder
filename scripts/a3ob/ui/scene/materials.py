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


def _material_nodes_for_selection():
    nodes = []
    seen = set()
    for shape in _mesh_shapes_from_selection():
        shading_groups = _valid_nodes(cmds.listConnections(shape, type="shadingEngine") or [])
        for shading_group in shading_groups:
            if shading_group in {"initialShadingGroup", "initialParticleSE"} or shading_group in seen:
                continue
            seen.add(shading_group)
            materials = _valid_nodes(cmds.ls(cmds.listConnections(shading_group + ".surfaceShader") or [], materials=True) or [])
            material_node = materials[0] if materials else ""
            texture = ""
            material = ""
            for candidate in _valid_nodes([shading_group, material_node]):
                if not texture:
                    texture = _safe_get_attr(candidate, "a3obTexture", "") or ""
                if not material:
                    material = _safe_get_attr(candidate, "a3obMaterial", "") or ""
            nodes.append({"material_node": material_node, "shading_groups": [shading_group], "texture": texture, "material": material})
    return sorted(nodes, key=lambda item: ((item["material_node"] or "").lower(), item["shading_groups"][0].lower()))


def _material_metadata_label(item):
    name = item["material_node"] or "No material"
    marker = "●" if (item["texture"] or item["material"]) else "○"
    return f"{marker}  {name}"


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
    "_material_nodes_for_selection",
    "_material_metadata_label",
    "_set_material_metadata_on_node",
]
