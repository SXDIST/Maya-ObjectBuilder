"""Recent-value history backed by Maya string-array optionVars.

Feeds the editable path comboboxes (proxy paths, material texture/rvmat paths) so the
user picks a recently-used path instead of retyping it. There is no authoritative DayZ
path catalogue, so history is the pragmatic source.
"""

import maya.cmds as cmds

LIMIT = 12


def _var(key):
    return "MayaObjectBuilder_recent_" + key


def recent_paths(key):
    var = _var(key)
    if not cmds.optionVar(exists=var):
        return []
    value = cmds.optionVar(query=var)
    if isinstance(value, list):
        return [v for v in value if v]
    return [value] if value else []


def remember_path(key, value):
    value = (value or "").strip()
    if not value:
        return
    items = [value] + [p for p in recent_paths(key) if p != value]
    items = items[:LIMIT]
    var = _var(key)
    if cmds.optionVar(exists=var):
        cmds.optionVar(remove=var)
    for item in items:
        cmds.optionVar(stringValueAppend=(var, item))


__all__ = ["recent_paths", "remember_path"]
