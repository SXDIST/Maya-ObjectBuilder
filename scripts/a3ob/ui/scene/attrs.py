"""Scene helper: attrs domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401


def _node_exists(node):
    return bool(node) and cmds.objExists(node)


def _attr_exists(node, attr):
    return _node_exists(node) and cmds.attributeQuery(attr, node=node, exists=True)


def _safe_get_attr(node, attr, default=None):
    if not _attr_exists(node, attr):
        return default
    value = cmds.getAttr(f"{node}.{attr}")
    return default if value is None else value


def _valid_nodes(nodes):
    return [node for node in nodes if _node_exists(node)]


def _ensure_string_attr(node, attr, short_name):
    if not _node_exists(node):
        return False
    if not _attr_exists(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, dataType="string")
    return True


def _normalize_dayz_path(path):
    path = (path or "").strip().replace("/", "\\")
    if len(path) >= 2 and path[1] == ":":
        path = path[2:].lstrip("\\")
    return re.sub(r"\\+", r"\\", path)


def _split_named_properties(raw):
    properties = []
    for part in (raw or "").split(";"):
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        properties.append((name.strip(), value.strip()))
    return properties


def _join_named_properties(properties):
    return ";".join(f"{name}={value}" for name, value in properties if name)


__all__ = [
    "_node_exists",
    "_attr_exists",
    "_safe_get_attr",
    "_valid_nodes",
    "_ensure_string_attr",
    "_normalize_dayz_path",
    "_split_named_properties",
    "_join_named_properties",
]
