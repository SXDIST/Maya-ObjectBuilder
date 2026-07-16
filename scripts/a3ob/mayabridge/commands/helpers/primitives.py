"""commands helper: primitives."""

"""The ``a3ob*`` Maya commands (OpenMaya 2.0 MPxCommand).

Port of ``src/commands/StubCommands.cpp``. Command names, flags and the resulting
``a3ob*`` attribute schema are preserved exactly — this is the contract the Python UI
and the ``tests/mayapy`` workflows depend on.

First-cut note: these commands are functional but not yet wired for undo. The C++
versions accumulated ``MDGModifier``/``MDagModifier`` operations; here operations are
applied directly. Undo support can be layered on later without changing the surface.
"""

import re

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A



NULL = om.MObject.kNullObj


_PROXY_SELECTION_RE = re.compile(r"^proxy:.*\.\d+$")


_COMPONENT_RE = re.compile(r"^[Cc]omponent\d+$")


# =============================================================================
# string / value helpers
# =============================================================================


def split_semicolon(value):
    return [part for part in value.split(";") if part]


def split_properties(value):
    result = []
    for part in split_semicolon(value):
        sep = part.find("=")
        if sep == -1:
            result.append((part, ""))
        else:
            result.append((part[:sep], part[sep + 1:]))
    return result


def properties_string(properties):
    pieces = []
    for key, value in properties:
        if not key:
            continue
        pieces.append("%s=%s" % (key, value))
    return ";".join(pieces)


def _format_number(value):
    # Mirrors MString += double / int: integers print without a trailing ".0".
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def mass_values_string(values):
    return ";".join(_format_number(v) for v in values)


def repeated_mass_values(count, value):
    return ";".join(_format_number(value) for _ in range(count))


def is_ascii(value):
    return all(ord(ch) <= 127 for ch in value)


def is_proxy_selection_name(value):
    return _PROXY_SELECTION_RE.match(value) is not None


def is_component_selection_name(value):
    return _COMPONENT_RE.match(value) is not None


def proxy_selection_name(path, index):
    return "proxy:%s.%d" % (path, index)


# =============================================================================
# DAG / selection helpers
# =============================================================================


def normalize_dayz_path(value):
    path = value.strip()
    path = path.replace("/", "\\")
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        path = path[2:]
        while path and path[0] == "\\":
            path = path[1:]
    normalized = []
    previous_slash = False
    for ch in path:
        if ch == "\\":
            if not previous_slash:
                normalized.append(ch)
            previous_slash = True
        else:
            normalized.append(ch)
            previous_slash = False
    return "".join(normalized)


def named_property_result(lod):
    return ["%s=%s" % (key, value) for key, value in split_properties(attr.get_string(lod, A.PROPERTIES))]


# =============================================================================
# Commands
# =============================================================================


__all__ = [
    "NULL",
    "_PROXY_SELECTION_RE",
    "_COMPONENT_RE",
    "split_semicolon",
    "split_properties",
    "properties_string",
    "_format_number",
    "mass_values_string",
    "repeated_mass_values",
    "is_ascii",
    "is_proxy_selection_name",
    "is_component_selection_name",
    "proxy_selection_name",
    "normalize_dayz_path",
    "named_property_result",
]
