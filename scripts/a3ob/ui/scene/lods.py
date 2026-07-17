"""Scene helper: lods domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
from a3ob.ui.scene.attrs import *  # noqa: F401,F403


def _is_lod_transform(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery("a3obIsLOD", node=node, exists=True)


def _lod_transforms():
    return [node for node in cmds.ls(type="transform") or [] if _is_lod_transform(node)]


def _selected_lod_transform():
    for node in cmds.ls(selection=True, long=True) or []:
        current = node.split(".", 1)[0]  # component (mesh.f[..]/.vtx[..]) -> its shape/transform
        while current:
            if _is_lod_transform(current):
                return current
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            current = parents[0] if parents else ""
    return None


def _lod_name_from_transform(lod_node):
    lod_type = _safe_get_attr(lod_node, "a3obLodType", 0)
    resolution = _safe_get_attr(lod_node, "a3obResolution", 0)
    name = LOD_TYPE_NAMES.get(lod_type, "LOD")
    suffix = f" {resolution}" if lod_type == RESOLUTION_LOD_TYPE else ""
    return f"{name}{suffix}"


def _lod_label(node):
    if _attr_exists(node, "a3obLodType"):
        return f"{_lod_name_from_transform(node)}  |  {node}"
    return node


def _lod_name_for_set(set_node):
    try:
        members = cmds.sets(set_node, query=True) or []
        for member in members:
            current = member.split(".", 1)[0]
            while current:
                if _is_lod_transform(current):
                    return _lod_name_from_transform(current)
                parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
                current = parents[0] if parents else ""
    except Exception:
        pass
    return ""


def _set_lod_label(node):
    lod = _lod_name_for_set(node)
    if lod:
        return lod
    raw = node.split(":")[-1]
    for marker in ("_SEL_", "_VERTEX_FLAG_", "_FACE_FLAG_"):
        if marker in raw:
            base = raw.split(marker)[0]
            if base.startswith("Resolution_"):
                return "Resolution " + base.rsplit("_", 1)[-1]
            return base.replace("_", " ")
    return "Other"


def _set_kind(is_proxy, flag_component):
    if is_proxy:
        return "Proxy"
    if flag_component == "vertex":
        return "Vertex Flag"
    if flag_component == "face":
        return "Face Flag"
    return "Selection"


__all__ = [
    "_is_lod_transform",
    "_lod_transforms",
    "_selected_lod_transform",
    "_lod_name_from_transform",
    "_lod_label",
    "_lod_name_for_set",
    "_set_lod_label",
    "_set_kind",
]
