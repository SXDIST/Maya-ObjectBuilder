"""metadata action wrappers."""

import maya.cmds as cmds

from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.actions._common import _undo_chunk  # noqa: F401


def apply_mass_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    value = dock.mass_value()
    mode = dock.mass_mode()
    with _undo_chunk("Set Mass"):
        cmds.a3obSetMass(value=value, selectedComponents=(mode == "Selected vertices"))


def clear_mass_from_ui():
    load_plugin()
    with _undo_chunk("Clear Mass"):
        cmds.a3obSetMass(clear=True)


def apply_flag_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    from a3ob.ui.dialogs import flag_dialog
    answer = flag_dialog(dock)
    if answer is None:
        return
    component, value, name = answer
    if not name:
        cmds.warning("Enter a flag set name")
        return
    with _undo_chunk("Set Flag"):
        cmds.a3obSetFlag(component=component, value=value, name=name)
    _refresh_context_ui()


def apply_flag_edit_from_ui():
    """Write the details-area flag editor onto the highlighted set.

    There is no a3obUpdateFlag command — a3obSetFlag only creates — so this writes the two
    attributes directly. That is safe where the proxy commands are not: this creates no
    objectSet, so it carries none of the orphan-set risk that makes a3obProxy and
    a3obUpdateProxy deliberately non-undoable. A plain cmds.setAttr undoes correctly."""
    dock = _active_qt_dock()
    if dock is None:
        return
    set_node = dock.selected_selection_set_node()
    if not set_node:
        cmds.warning("Select a flag set to edit")
        return
    # The Apply button only exists on a page shown for a flag row, so a mouse cannot reach
    # this with anything else highlighted — but the function is public, and without the
    # guard a Selection or Proxy row makes setAttr RAISE on the missing attribute instead
    # of warning. Same shape as the zero-value guard below.
    kind = selection_set_editable_fields(set_node).get("kind", "")
    if kind not in ("Vertex Flag", "Face Flag"):
        cmds.warning("Select a flag set to edit — %r is not one"
                     % (kind or set_node))
        return
    component, value = dock.flag_edit_values()
    if not component:
        cmds.warning("The flag editor is not available")
        return
    if value == 0:
        cmds.warning("A flag value of 0 is not exported — enter a non-zero value")
        return
    with _undo_chunk("Edit Flag"):
        cmds.setAttr(set_node + ".a3obFlagComponent", component, type="string")
        cmds.setAttr(set_node + ".a3obFlagValue", value)
    _refresh_context_ui()


def _validate_proxy_path(path):
    """Return (ok, warning_message) for a proxy path string.

    Absolute .p3d paths must exist on disk.  Relative paths are resolved against
    the texture root optionVar (MayaObjectBuilder_texture_root); a missing root
    counts as a failure.  The rule is stated explicitly in the warning so the user
    knows what to fix.
    """
    import os
    if not path.lower().endswith(".p3d"):
        return False, f"Proxy path must end in .p3d, got: {path!r}"
    if os.path.isabs(path):
        if os.path.isfile(path):
            return True, ""
        return False, f"Proxy path does not exist: {path!r}"
    # Relative path: resolve against the texture root optionVar.
    _var = "MayaObjectBuilder_texture_root"
    root = cmds.optionVar(query=_var) if cmds.optionVar(exists=_var) else ""
    if not root:
        return False, (
            f"Proxy path {path!r} is relative, but no texture root is configured — "
            "set one in the plugin options or provide an absolute path"
        )
    resolved = os.path.join(root, path.lstrip("\\/"))
    if os.path.isfile(resolved):
        return True, ""
    return False, (
        f"Proxy path {path!r} not found "
        f"(relative paths are resolved against the texture root {root!r})"
    )


def create_proxy_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    from a3ob.ui.dialogs import proxy_dialog, proxy_creation_mode
    answer = proxy_dialog(dock)
    if answer is None:
        return
    path, index = answer
    if not path:
        cmds.warning("Enter a proxy path")
        return
    ok, msg = _validate_proxy_path(path)
    if not ok:
        cmds.warning(msg)
        return
    from_selection = proxy_creation_mode() == "components"
    with _undo_chunk("Create Proxy"):
        cmds.a3obProxy(path=path, index=index, fromSelection=from_selection, update=True)
    from a3ob.ui.recent import remember_path
    remember_path("proxy", path)
    _refresh_context_ui()


def update_proxy_from_ui():
    """Point the highlighted proxy at a new path and index.

    a3obUpdateProxy takes no target node — it acts on whatever is SELECTED
    (selected_dependency_node_or_null in commands/update_proxy.py). So this selects the set,
    runs the command and restores the user's selection in a finally: clicking Update must not
    silently change what is selected in the viewport, and it must not leave the proxy set
    selected if the command raises.

    noExpand=True is load-bearing: selecting an objectSet by name ordinarily selects its
    MEMBERS (that is how "quick select sets" work), not the set node itself.
    a3obUpdateProxy needs the set node — the same reasoning already applied by
    tests/mayapy/proxy_update_keeps_pair.py when it selects a proxy set directly."""
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    set_node = dock.selected_selection_set_node()
    if not set_node:
        cmds.warning("Select a proxy in the list to update")
        return
    path, index = dock.proxy_edit_values()
    if not path:
        cmds.warning("Enter a proxy path")
        return
    ok, msg = _validate_proxy_path(path)
    if not ok:
        cmds.warning(msg)
        return
    previous = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(set_node, replace=True, noExpand=True)
        with _undo_chunk("Update Proxy"):
            cmds.a3obUpdateProxy(path=path, index=index)
    finally:
        if previous:
            cmds.select(previous, replace=True)
        else:
            cmds.select(clear=True)
    from a3ob.ui.recent import remember_path
    remember_path("proxy", path)
    _refresh_context_ui()


def _lod_mass_summary():
    """(total mass, vertex-value count) of the active LOD, or (None, 0) when none."""
    node = _selected_lod_transform()
    if not node:
        return None, 0
    raw = _safe_get_attr(node, "a3obMassValues", "") or ""
    values = []
    for token in raw.split(";"):
        token = token.strip()
        if not token:
            continue
        try:
            values.append(float(token))
        except ValueError:
            pass
    return sum(values), len(values)


def _lod_vertex_count(node):
    total = 0
    for shape in cmds.listRelatives(node, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []:
        try:
            total += cmds.polyEvaluate(shape, vertex=True)
        except RuntimeError:  # noqa: BLE001 - transient shape state (undo/scene-open); partial total is fine
            pass
    return total


def distribute_mass_evenly():
    load_plugin()
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD to distribute mass")
        return
    total, count = _lod_mass_summary()
    if not count or not total or total <= 0:
        cmds.warning("The LOD has no mass to distribute")
        return
    cmds.select(node, replace=True)
    with _undo_chunk("Distribute Mass Evenly"):
        cmds.a3obSetMass(value=total / count)
    _refresh_context_ui()


def mass_from_volume_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    density = dock.mass_density_field.value() if dock is not None and dock.mass_density_field is not None else 1000.0
    node = _selected_lod_transform()
    if not node:
        cmds.warning("Select a LOD")
        return
    count = _lod_vertex_count(node)
    if count <= 0:
        cmds.warning("The LOD has no vertices")
        return
    bbox = cmds.exactWorldBoundingBox(node)
    volume = max(0.0, bbox[3] - bbox[0]) * max(0.0, bbox[4] - bbox[1]) * max(0.0, bbox[5] - bbox[2])
    total = volume * density
    cmds.select(node, replace=True)
    with _undo_chunk("Mass From Volume"):
        cmds.a3obSetMass(value=total / count)
    _refresh_context_ui()


__all__ = [
    "apply_mass_from_ui",
    "clear_mass_from_ui",
    "apply_flag_from_ui",
    "apply_flag_edit_from_ui",
    "_validate_proxy_path",
    "create_proxy_from_ui",
    "update_proxy_from_ui",
    "distribute_mass_evenly",
    "mass_from_volume_from_ui",
]
