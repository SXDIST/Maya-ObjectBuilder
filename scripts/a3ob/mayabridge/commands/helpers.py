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
def _iter_selection(sel):
    for i in range(sel.length()):
        try:
            dag_path, component = sel.getComponent(i)
        except Exception:
            continue
        if not dag_path.isValid():
            continue
        yield dag_path, component


def first_mesh_child(transform):
    if transform.isNull():
        return NULL
    dag = om.MFnDagNode(transform)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            return child
    return NULL


def selected_transform_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kTransform):
            return node
        if node.hasFn(om.MFn.kMesh):
            return om.MFnDagNode(node).parent(0)
    return NULL


def lod_transform_for_path(dag_path):
    node = dag_path.node()
    while not node.isNull():
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            return node
        dag = om.MFnDagNode(node)
        if dag.parentCount() == 0:
            break
        node = dag.parent(0)
    return NULL


def selected_lod_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        lod = lod_transform_for_path(dag_path)
        if not lod.isNull():
            return lod
    return NULL


def lod_transforms(selection_only):
    lods = []
    if selection_only:
        sel = om.MGlobal.getActiveSelectionList()
        for dag_path, _component in _iter_selection(sel):
            node = dag_path.node()
            if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
                lods.append(node)
        return lods

    it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
    while not it.isDone():
        node = it.currentItem()
        if attr.get_bool(node, A.IS_LOD):
            lods.append(node)
        it.next()
    return lods


def node_name(node):
    if node.isNull():
        return ""
    return om.MFnDependencyNode(node).name()


def same_node(a, b):
    return not a.isNull() and not b.isNull() and a == b


# =============================================================================
# LOD metadata
# =============================================================================
def set_lod_attributes(transform, lod_type, resolution):
    from a3ob.formats.p3d import LodResolution
    signature = LodResolution.encode(lod_type, resolution)
    attr.set_bool(transform, A.IS_LOD, True)
    attr.set_int(transform, A.LOD_TYPE, lod_type)
    attr.set_int(transform, A.RESOLUTION, resolution)
    attr.set_double(transform, A.RESOLUTION_SIGNATURE, signature)
    attr.set_int(transform, A.SOURCE_VERTEX_COUNT, 0)
    attr.set_int(transform, A.SOURCE_FACE_COUNT, 0)


def vertex_count_for_lod(transform):
    mesh = first_mesh_child(transform)
    if not mesh.isNull():
        return om.MFnMesh(mesh).numVertices
    return attr.get_int(transform, A.SOURCE_VERTEX_COUNT, 0)


# =============================================================================
# proxy / set helpers
# =============================================================================
def proxy_placeholder(lod, selection_name):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if (child.hasFn(om.MFn.kTransform)
                and attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT)
                and attr.get_string(child, A.PROXY_SELECTION) == selection_name):
            return child
    return NULL


def proxy_selection_set_exists(selection_name):
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        node = it.thisNode()
        if attr.get_bool(node, A.IS_PROXY_SELECTION) and attr.get_string(node, A.SELECTION_NAME) == selection_name:
            return True
        it.next()
    return False


def set_contains_mesh(set_obj, mesh):
    set_fn = om.MFnSet(set_obj)
    members = set_fn.getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if dag_path.node() == mesh:
            return True
    return False


def metadata_set_has_live_members(set_obj):
    members = om.MFnSet(set_obj).getMembers(True)
    return members.length() > 0


def is_object_builder_metadata_set(set_obj):
    return (bool(attr.get_string(set_obj, A.SELECTION_NAME))
            or bool(attr.get_string(set_obj, A.FLAG_COMPONENT))
            or attr.get_bool(set_obj, A.IS_PROXY_SELECTION))


# =============================================================================
# geometry analysis
# =============================================================================
def polygon_has_repeated_vertices(vertices):
    seen = set()
    for v in vertices:
        if v in seen:
            return True
        seen.add(v)
    return False


def polygon_has_near_zero_area(points):
    if len(points) < 3:
        return True
    origin = points[0]
    area = 0.0
    for i in range(1, len(points) - 1):
        a = points[i] - origin
        b = points[i + 1] - origin
        area += (a ^ b).length() * 0.5
    return area < 1.0e-10


EdgeKey = lambda a, b: (a, b) if a < b else (b, a)  # noqa: E731


def closed_face_islands(mesh_fn):
    it = om.MItMeshPolygon(mesh_fn.object())
    num_polygons = mesh_fn.numPolygons
    edge_faces = {}
    face_edges = [[] for _ in range(num_polygons)]
    while not it.isDone():
        vertices = it.getVertices()
        face_index = it.index()
        n = len(vertices)
        for i in range(n):
            key = EdgeKey(vertices[i], vertices[(i + 1) % n])
            edge_faces.setdefault(key, []).append(face_index)
            face_edges[face_index].append(key)
        it.next()

    adjacency = [[] for _ in range(num_polygons)]
    for key, faces in edge_faces.items():
        if len(faces) == 2:
            adjacency[faces[0]].append(faces[1])
            adjacency[faces[1]].append(faces[0])

    visited = [False] * num_polygons
    islands = []
    for start in range(num_polygons):
        if visited[start]:
            continue
        island_faces = set()
        island_vertices = set()
        closed = True
        queue = [start]
        visited[start] = True
        while queue:
            face = queue.pop(0)
            island_faces.add(face)
            for key in face_edges[face]:
                island_vertices.add(key[0])
                island_vertices.add(key[1])
            for nxt in adjacency[face]:
                if not visited[nxt]:
                    visited[nxt] = True
                    queue.append(nxt)
        for face in island_faces:
            for key in face_edges[face]:
                count = sum(1 for ef in edge_faces[key] if ef in island_faces)
                if count != 2:
                    closed = False
        islands.append((island_faces, island_vertices, closed))
    return islands


# =============================================================================
# component selection collection
# =============================================================================
def selected_components():
    """Return (MSelectionList members, lod MObject) for selected mesh components."""
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    lod = NULL
    for dag_path, component in _iter_selection(sel):
        if component.isNull():
            continue
        candidate = lod_transform_for_path(dag_path)
        if candidate.isNull():
            continue
        if lod.isNull():
            lod = candidate
        members.add((dag_path, component))
    return members, lod


def mass_values_for_lod(transform, default_value):
    count = max(vertex_count_for_lod(transform), 0)
    values = [default_value] * count
    existing = split_semicolon(attr.get_string(transform, A.MASS_VALUES))
    for i in range(min(len(existing), len(values))):
        values[i] = float(existing[i])
    return values


def set_selected_mass_values(lod, value):
    members, selected_lod = selected_components()
    if members.length() == 0:
        return False
    if lod.isNull():
        lod = selected_lod

    masses = mass_values_for_lod(lod, 0.0)
    for i in range(members.length()):
        try:
            dag_path, component = members.getComponent(i)
        except Exception:
            continue
        if component.isNull() or not component.hasFn(om.MFn.kMeshVertComponent):
            continue
        elements = om.MFnSingleIndexedComponent(component).getElements()
        for index in elements:
            if 0 <= index < len(masses):
                masses[index] = value

    attr.set_bool(lod, A.HAS_MASS, True)
    attr.set_string(lod, A.MASS_VALUES, mass_values_string(masses))
    return True


# =============================================================================
# set creation
# =============================================================================
def _create_set_from_members(members, name, restriction=None):
    set_fn = om.MFnSet()
    if restriction is None:
        restriction = om.MFnSet.kNone
    set_obj = set_fn.create(members, restriction)
    set_fn.setName(name)
    return set_obj


def create_metadata_set(set_name, component, value):
    members, _lod = selected_components()
    if members.length() == 0:
        return NULL
    set_obj = _create_set_from_members(members, set_name)
    attr.set_string(set_obj, A.SELECTION_NAME, set_name)
    attr.set_string(set_obj, A.FLAG_COMPONENT, component)
    attr.set_int(set_obj, A.FLAG_VALUE, value)
    attr.mark_technical_set(set_obj)
    return set_obj


def _sanitized_set_name(selection_name):
    name = "a3ob_" + selection_name
    for ch in (":", "/", "\\", "."):
        name = name.replace(ch, "_")
    return name


def create_proxy_selection_set(selection_name):
    members = om.MSelectionList()
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, component in _iter_selection(sel):
        if dag_path.node().hasFn(om.MFn.kMesh) and not component.isNull():
            members.add((dag_path, component))
    if members.length() == 0:
        return
    set_obj = _create_set_from_members(members, _sanitized_set_name(selection_name))
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)


# =============================================================================
# component (find components) sets
# =============================================================================
class MeshTarget:
    __slots__ = ("mesh_path", "lod")

    def __init__(self, mesh_path, lod):
        self.mesh_path = mesh_path
        self.lod = lod


def _add_mesh_target(mesh_path, lod, targets):
    if mesh_path.isValid() and mesh_path.node().hasFn(om.MFn.kMesh):
        for target in targets:
            if target.mesh_path.node() == mesh_path.node() and (target.lod == lod or same_node(target.lod, lod)):
                return
        targets.append(MeshTarget(mesh_path, lod))


def _add_child_mesh_targets(lod, targets):
    dag = om.MFnDagNode(lod)
    for i in range(dag.childCount()):
        child = dag.child(i)
        if child.hasFn(om.MFn.kMesh):
            _add_mesh_target(om.MFnDagNode(child).getPath(), lod, targets)
        elif child.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(child)
            if not mesh.isNull():
                _add_mesh_target(om.MFnDagNode(mesh).getPath(), lod, targets)


def selected_mesh_targets():
    targets = []
    sel = om.MGlobal.getActiveSelectionList()
    for dag_path, _component in _iter_selection(sel):
        node = dag_path.node()
        if node.hasFn(om.MFn.kMesh):
            _add_mesh_target(dag_path, lod_transform_for_path(dag_path), targets)
            continue
        if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
            _add_child_mesh_targets(node, targets)
            continue
        if node.hasFn(om.MFn.kTransform):
            mesh = first_mesh_child(node)
            if not mesh.isNull():
                mesh_path = om.MFnDagNode(mesh).getPath()
                _add_mesh_target(mesh_path, lod_transform_for_path(mesh_path), targets)
    return targets


def _component_set_belongs_to_target(set_obj, lod, mesh_path):
    members = om.MFnSet(set_obj).getMembers(True)
    for dag_path, _component in _iter_selection(members):
        if not lod.isNull() and same_node(lod_transform_for_path(dag_path), lod):
            return True
        if lod.isNull() and dag_path.node() == mesh_path.node():
            return True
    return False


def _delete_existing_component_sets(lod, mesh_path):
    to_delete = []
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        set_obj = it.thisNode()
        selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
        if is_component_selection_name(selection_name) and _component_set_belongs_to_target(set_obj, lod, mesh_path):
            to_delete.append(om.MFnDependencyNode(set_obj).name())
        it.next()
    if to_delete:
        import maya.cmds as cmds
        cmds.delete(to_delete)


# =============================================================================
# material nodes
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


def create_material_nodes(texture, material):
    import maya.cmds as cmds
    normalized_texture = normalize_dayz_path(texture)
    normalized_material = normalize_dayz_path(material)
    shader = cmds.createNode("lambert", name="a3ob_material#")
    shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=shader + "SG")
    cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader", force=True)

    sel = om.MSelectionList()
    sel.add(shader)
    sel.add(shading_group)
    shader_obj = sel.getDependNode(0)
    sg_obj = sel.getDependNode(1)
    attr.set_string(shader_obj, A.TEXTURE, normalized_texture)
    attr.set_string(shader_obj, A.MATERIAL, normalized_material)
    attr.set_string(sg_obj, A.SG_TEXTURE, normalized_texture)
    attr.set_string(sg_obj, A.SG_MATERIAL, normalized_material)
    return shading_group


# =============================================================================
# proxy update helpers
# =============================================================================
def selected_dependency_node_or_null():
    sel = om.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        node = sel.getDependNode(i)
        if not node.isNull():
            return node
    return NULL


def update_proxy_selection_set(set_obj, path, index):
    import maya.cmds as cmds
    selection_name = proxy_selection_name(path, index)
    attr.set_string(set_obj, A.SELECTION_NAME, selection_name)
    attr.set_bool(set_obj, A.IS_PROXY_SELECTION, True)
    attr.mark_technical_set(set_obj)
    cmds.rename(om.MFnDependencyNode(set_obj).name(), _sanitized_set_name(selection_name))


def update_proxy_placeholder(proxy, path, index):
    selection_name = proxy_selection_name(path, index)
    attr.set_bool(proxy, A.IS_PROXY, True)
    attr.set_string(proxy, A.PROXY_PATH, path)
    attr.set_int(proxy, A.PROXY_INDEX, index)
    attr.set_string(proxy, A.PROXY_SELECTION, selection_name)


def named_property_result(lod):
    return ["%s=%s" % (key, value) for key, value in split_properties(attr.get_string(lod, A.PROPERTIES))]


# =============================================================================
# Commands
# =============================================================================
class _Base(om.MPxCommand):
    def isUndoable(self):
        return False




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
    "_iter_selection",
    "first_mesh_child",
    "selected_transform_or_null",
    "lod_transform_for_path",
    "selected_lod_or_null",
    "lod_transforms",
    "node_name",
    "same_node",
    "set_lod_attributes",
    "vertex_count_for_lod",
    "proxy_placeholder",
    "proxy_selection_set_exists",
    "set_contains_mesh",
    "metadata_set_has_live_members",
    "is_object_builder_metadata_set",
    "polygon_has_repeated_vertices",
    "polygon_has_near_zero_area",
    "EdgeKey",
    "closed_face_islands",
    "selected_components",
    "mass_values_for_lod",
    "set_selected_mass_values",
    "_create_set_from_members",
    "create_metadata_set",
    "_sanitized_set_name",
    "create_proxy_selection_set",
    "MeshTarget",
    "_add_mesh_target",
    "_add_child_mesh_targets",
    "selected_mesh_targets",
    "_component_set_belongs_to_target",
    "_delete_existing_component_sets",
    "normalize_dayz_path",
    "create_material_nodes",
    "selected_dependency_node_or_null",
    "update_proxy_selection_set",
    "update_proxy_placeholder",
    "named_property_result",
    "_Base",
]
