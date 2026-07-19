"""Scene helper: lods domain (no Qt/dock deps)."""

import re  # noqa: F401

import maya.cmds as cmds
import maya.api.OpenMaya as om

from a3ob.ui.constants import LOD_TYPE_NAMES, RESOLUTION_LOD_TYPE, MEMORY_LOD_TYPE  # noqa: F401
from a3ob.ui.scene.attrs import *  # noqa: F401,F403


def _is_lod_transform(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery("a3obIsLOD", node=node, exists=True)


def _lod_transforms():
    # Let Maya filter by attribute instead of walking every transform in the scene and
    # calling attributeQuery on each: 27 ms -> 0.6 ms on a 183-transform character scene.
    return cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []


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


def _lod_node_for_set(set_node):
    """The LOD transform a selection set's members live under, as a full DAG path.

    This — not the label — is a LOD's identity. A scene routinely holds several LODs that
    share a label: a helmet and two body resolutions all came back as "Resolution 1", so
    anything keyed on the label folds them into one."""
    try:
        members = cmds.sets(set_node, query=True) or []
        for member in members:
            current = member.split(".", 1)[0]
            while current:
                if _is_lod_transform(current):
                    return cmds.ls(current, long=True)[0]
                parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
                current = parents[0] if parents else ""
    except RuntimeError:  # noqa: BLE001 - set or its members may be stale during scene edit; "" means "Other" bucket
        pass
    return ""


def _lod_name_for_set(set_node):
    node = _lod_node_for_set(set_node)
    return _lod_name_from_transform(node) if node else ""


def _transform_of(node):
    """``node``'s own transform — itself if it is one, its parent if it is a shape."""
    if not node or not cmds.objExists(node):
        return ""
    if cmds.objectType(node, isAType="transform"):
        return (cmds.ls(node, long=True) or [""])[0]
    parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
    return parents[0] if parents else ""


def _owner_node_for_set(set_node):
    """The node a selection set belongs to: its LOD if it has one, else its own mesh.

    Selections are useful before a mesh is marked as a LOD — that is the order people
    actually work in, modelling and naming parts first. Keying strictly on the LOD meant a
    set created on an unmarked mesh existed in the scene but appeared in no panel."""
    lod = _lod_node_for_set(set_node)
    if lod:
        return lod
    for member in cmds.sets(set_node, query=True) or []:
        owner = _transform_of(member.split(".", 1)[0])
        if owner:
            return owner
    return ""


def _selected_selection_owner():
    """What the Selections panel should be showing: the selected LOD, else the mesh."""
    lod = _selected_lod_transform()
    if lod:
        return lod
    for node in cmds.ls(selection=True, long=True) or []:
        owner = _transform_of(node.split(".", 1)[0])
        if owner:
            return owner
    return None


def _lod_list_target(active, previous):
    """Which LOD the list should highlight: the scene's, falling back to its own row.

    The other way round looks harmless and breaks the panel outright — once the user has
    clicked any row, ``previous`` is always set, so selecting a LOD in the viewport could
    never move the highlight again."""
    return active or previous


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


def lod_geometry_key():
    """Cheap fingerprint of every LOD mesh, for the dock's poll timer.

    ``polyEvaluate(triangle=True)`` re-triangulates the mesh on every call (4.6 ms per shape,
    every 500 ms while the LOD panel is open). MFnMesh's cached counts answer in 0.01 ms and
    still change whenever the geometry does, which is all a change detector needs — the real
    triangle count is computed only when the panel actually redraws."""
    key = []
    for node in _lod_transforms():
        for shape in cmds.listRelatives(node, allDescendents=True, type="mesh",
                                        fullPath=True, noIntermediate=True) or []:
            try:
                selection = om.MSelectionList()
                selection.add(shape)
                mesh_fn = om.MFnMesh(selection.getDagPath(0))
                key.append((shape, mesh_fn.numPolygons, mesh_fn.numVertices))
            except Exception:  # noqa: BLE001 - transient state during undo/scene open
                key.append((shape, -1, -1))
    return tuple(key)


def _lod_triangle_count(node):
    total = 0
    for shape in cmds.listRelatives(node, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []:
        try:
            total += cmds.polyEvaluate(shape, triangle=True)
        except RuntimeError:  # noqa: BLE001 - transient shape state (undo/scene-open); partial total is fine
            pass
    return total


def lod_overview():
    """Every LOD in the scene as dicts (node, label, type, resolution, tris, selections),
    sorted by type then resolution — data for the central LOD list panel."""
    selection_counts = {}
    # Maya's attribute filter instead of probing every objectSet in the scene. Counted per
    # LOD NODE: keyed by label, three same-labelled LODs each showed the other two's sets.
    for node in cmds.ls("*.a3obSelectionName", objectsOnly=True) or []:
        owner = _lod_node_for_set(node)
        if owner:
            selection_counts[owner] = selection_counts.get(owner, 0) + 1
    rows = []
    for node in _lod_transforms():
        label = _lod_name_from_transform(node)
        rows.append({
            "node": node,
            "label": label,
            "type": _safe_get_attr(node, "a3obLodType", 0),
            "resolution": _safe_get_attr(node, "a3obResolution", 0),
            "tris": _lod_triangle_count(node),
            "selections": selection_counts.get(node, 0),
        })
    rows.sort(key=lambda row: (row["type"], row["resolution"], row["label"]))
    return rows


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
    "_lod_node_for_set",
    "_lod_list_target",
    "_transform_of",
    "_owner_node_for_set",
    "_selected_selection_owner",
    "_set_lod_label",
    "_lod_triangle_count",
    "lod_geometry_key",
    "lod_overview",
    "_set_kind",
]
