"""Scene helper: memory domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
from a3ob.ui.scene.attrs import *  # noqa: F401,F403
from a3ob.ui.scene.lods import *  # noqa: F401,F403


def _scene_memory_lods():
    return [n for n in _lod_transforms() if _safe_get_attr(n, "a3obLodType", -1) == MEMORY_LOD_TYPE]


def _memory_lod_parent(node):
    """Returns the Memory LOD if it is the direct parent of node, else None."""
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    if not parents:
        return None
    parent = parents[0]
    if _is_lod_transform(parent) and _safe_get_attr(parent, "a3obLodType", -1) == MEMORY_LOD_TYPE:
        return parent
    return None


def _is_group_container(node):
    """True if node is a named group container directly under a Memory LOD (no locator shape itself, but has locator-bearing children)."""
    if not _memory_lod_parent(node):
        return False
    if _is_lod_transform(node):
        return False
    if cmds.listRelatives(node, shapes=True, type="locator", fullPath=True):
        return False
    children = cmds.listRelatives(node, children=True, type="transform", fullPath=True) or []
    return any(cmds.listRelatives(c, shapes=True, type="locator", fullPath=True) for c in children)


__all__ = [
    "_scene_memory_lods",
    "_memory_lod_parent",
    "_is_group_container",
]
