"""Scene helper: attrs domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
# One home for these two. ui/ already depends on mayabridge/, so the import goes that way;
# the reverse would be a new cycle.
from a3ob.mayabridge.commands.helpers.primitives import (  # noqa: F401
    normalize_dayz_path as _normalize_dayz_path,
    properties_string as _join_named_properties,
)


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


def _ensure_attr(node, attr, short_name=None, **kind):
    """Add ``attr`` to ``node`` if it is missing. False when there is no such node.

    ``kind`` is passed straight to ``cmds.addAttr`` (``dataType=`` or ``attributeType=``)."""
    if not _node_exists(node):
        return False
    if not _attr_exists(node, attr):
        if short_name:
            kind["shortName"] = short_name
        cmds.addAttr(node, longName=attr, **kind)
    return True


def _ensure_string_attr(node, attr, short_name):
    return _ensure_attr(node, attr, short_name, dataType="string")


def _set_bool_attr(node, attr, value):
    if not _ensure_attr(node, attr, attributeType="bool"):
        return
    cmds.setAttr(f"{node}.{attr}", bool(value))


def _split_named_properties(raw):
    """Parse the a3obProperties string as the dock's table wants it.

    Deliberately NOT shared with ``primitives.split_properties``, which is not the same
    function: it keeps a token with no "=" as ``(token, "")`` and does not strip, while the
    panel drops bare tokens and trims whitespace around what the user typed. The join half
    IS identical and is imported above."""
    properties = []
    for part in (raw or "").split(";"):
        if not part or "=" not in part:
            continue
        name, value = part.split("=", 1)
        properties.append((name.strip(), value.strip()))
    return properties


__all__ = [
    "_node_exists",
    "_attr_exists",
    "_safe_get_attr",
    "_valid_nodes",
    "_ensure_attr",
    "_ensure_string_attr",
    "_set_bool_attr",
    "_normalize_dayz_path",
    "_split_named_properties",
    "_join_named_properties",
]
