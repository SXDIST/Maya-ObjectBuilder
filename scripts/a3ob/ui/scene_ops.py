"""Maya-scene business logic for the MayaObjectBuilder UI (no Qt/dock deps)."""

import re

import maya.cmds as cmds

from a3ob.ui.constants import (
    LOD_TYPE_NAMES,
    RESOLUTION_LOD_TYPE,
    MEMORY_LOD_TYPE,
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


def _normalize_dayz_path(path):
    path = (path or "").strip().replace("/", "\\")
    if len(path) >= 2 and path[1] == ":":
        path = path[2:].lstrip("\\")
    return re.sub(r"\\+", r"\\", path)


def _ensure_string_attr(node, attr, short_name):
    if not _node_exists(node):
        return False
    if not _attr_exists(node, attr):
        cmds.addAttr(node, longName=attr, shortName=short_name, dataType="string")
    return True


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


def _lod_name_from_transform(lod_node):
    lod_type = _safe_get_attr(lod_node, "a3obLodType", 0)
    resolution = _safe_get_attr(lod_node, "a3obResolution", 0)
    name = LOD_TYPE_NAMES.get(lod_type, "LOD")
    suffix = f" {resolution}" if lod_type == RESOLUTION_LOD_TYPE else ""
    return f"{name}{suffix}"


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


def _live_set_members(set_node):
    if not _node_exists(set_node):
        return []
    members = cmds.sets(set_node, query=True) or []
    live_members = []
    for member in members:
        expanded = cmds.ls(member, flatten=True) or []
        live_members.extend(item for item in expanded if _node_exists(item.split(".", 1)[0]))
    return live_members


def _set_member_count(set_node):
    if not _node_exists(set_node):
        return 0
    try:
        return cmds.sets(set_node, query=True, size=True) or 0
    except RuntimeError:
        return 0


def _mesh_shapes_for_item(item):
    node = item.split(".", 1)[0]
    if not _node_exists(node):
        return []
    if cmds.objectType(node, isType="mesh"):
        return [node]
    return cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []


def _canonical_selection_components(selection=None):
    selection = selection or (cmds.ls(selection=True, flatten=True, long=True) or [])
    components = []
    seen = set()
    for item in selection:
        if ".vtx[" in item:
            expanded = cmds.ls(item, flatten=True, long=True) or []
        elif ".f[" in item:
            expanded = cmds.polyListComponentConversion(item, fromFace=True, toVertex=True) or []
            expanded = cmds.ls(expanded, flatten=True, long=True) or []
        else:
            expanded = []
            for shape in _mesh_shapes_for_item(item):
                count = cmds.polyEvaluate(shape, vertex=True)
                if count:
                    expanded.extend(cmds.ls(f"{shape}.vtx[0:{count - 1}]", flatten=True, long=True) or [])
        for component in expanded:
            if component not in seen and _node_exists(component.split(".", 1)[0]):
                seen.add(component)
                components.append(component)
    return components


def _is_object_builder_set(node):
    return _attr_exists(node, "a3obSelectionName") or _attr_exists(node, "a3obIsProxySelection") or _attr_exists(node, "a3obFlagComponent")


def _set_bool_attr(node, attr, value):
    if not _node_exists(node):
        return
    if not _attr_exists(node, attr):
        cmds.addAttr(node, longName=attr, attributeType="bool")
    cmds.setAttr(f"{node}.{attr}", bool(value))


def _hide_object_builder_set(node):
    if not _is_object_builder_set(node):
        return
    _set_bool_attr(node, "a3obTechnicalSet", True)
    if _attr_exists(node, "hiddenInOutliner"):
        cmds.setAttr(f"{node}.hiddenInOutliner", True)


def _normalize_object_builder_sets():
    cmds.undoInfo(stateWithoutFlush=False)
    try:
        for node in cmds.ls(type="objectSet") or []:
            if _is_object_builder_set(node):
                _hide_object_builder_set(node)
    finally:
        cmds.undoInfo(stateWithoutFlush=True)


def _selection_sets():
    _normalize_object_builder_sets()
    sets = []
    for node in cmds.ls(type="objectSet") or []:
        if not _is_object_builder_set(node) or not _attr_exists(node, "a3obSelectionName"):
            continue
        name = _safe_get_attr(node, "a3obSelectionName", "") or ""
        is_proxy = bool(_safe_get_attr(node, "a3obIsProxySelection", False))
        flag_component = _safe_get_attr(node, "a3obFlagComponent", "") or ""
        lod = _set_lod_label(node)
        sets.append({"node": node, "name": name, "kind": _set_kind(is_proxy, flag_component), "lod": lod})
    return sorted(sets, key=lambda item: (item["lod"].lower(), item["kind"], item["name"].lower(), item["node"].lower()))


def _selection_set_details(set_node):
    count = _set_member_count(set_node)
    name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
    flag_component = _safe_get_attr(set_node, "a3obFlagComponent", "") or ""
    is_proxy = bool(_safe_get_attr(set_node, "a3obIsProxySelection", False))
    return f"LOD: {_set_lod_label(set_node)}    Type: {_set_kind(is_proxy, flag_component)}    OB name: {name}    Members: {count}\nMaya set: {set_node}"


def _lod_label(node):
    if _attr_exists(node, "a3obLodType"):
        return f"{_lod_name_from_transform(node)}  |  {node}"
    return node


def _is_lod_transform(node):
    return bool(node) and cmds.objExists(node) and cmds.attributeQuery("a3obIsLOD", node=node, exists=True)


def _lod_transforms():
    return [node for node in cmds.ls(type="transform") or [] if _is_lod_transform(node)]


def _selected_lod_transform():
    for node in cmds.ls(selection=True, long=True) or []:
        current = node
        while current:
            if _is_lod_transform(current):
                return current
            parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
            current = parents[0] if parents else ""
    return None


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


def _mesh_shapes_from_selection():
    shapes = []
    seen = set()
    for item in cmds.ls(selection=True, flatten=True, long=True) or []:
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
