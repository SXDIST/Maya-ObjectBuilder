"""Maya DAG/mesh -> P3D MLOD conversion (OpenMaya 2.0).

Port of ``src/maya/MayaMeshExport.cpp``. Two passes: collect LOD transforms (+ sort
keys) then export and stream-write each LOD one at a time. N-gons are triangulated
through Maya so Object Builder (tri/quad only) can save them. Memory LODs with no mesh
are reconstructed from locators.

Coordinate convention: Maya (Y-up) -> P3D (Z-up) point ``(x, y, z) -> (x, -z, y)``;
vectors are normalized first.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.formats import p3d



def maya_to_core_point(point):
    return p3d.Vec3(float(point.x), float(-point.z), float(point.y))


def maya_to_core_vector(vector):
    n = vector.normal()
    return p3d.Vec3(float(n.x), float(-n.z), float(n.y))


# =============================================================================
# stored-metadata parsing (inverse of mesh_import serialization)
# =============================================================================


def _split_semicolon(value):
    return [part for part in value.split(";") if part]


def _split_float_values(value):
    return [float(part) for part in _split_semicolon(value)]


def _split_index_values(value):
    return [int(part) for part in _split_semicolon(value)]


def _split_vertex_values(value):
    vertices = []
    for part in _split_semicolon(value):
        fields = part.split(",")
        if len(fields) != 4:
            continue
        vertex = p3d.Vertex(p3d.Vec3(float(fields[0]), float(fields[1]), float(fields[2])), int(fields[3]))
        vertices.append(vertex)
    return vertices


def _split_uvset_taggs(value):
    taggs = []
    for group in value.split("|"):
        if not group:
            continue
        fields = group.split(",")
        if not fields or (len(fields) - 1) % 2 != 0:
            continue
        data = p3d.UVSetTaggData()
        data.id = int(fields[0])
        i = 1
        while i + 1 < len(fields):
            data.uvs.append(p3d.Vec2(float(fields[i]), float(fields[i + 1])))
            i += 2
        taggs.append(data)
    return taggs


def _split_properties(value):
    result = []
    for part in _split_semicolon(value):
        sep = part.find("=")
        if sep == -1:
            continue
        result.append((part[:sep], part[sep + 1:]))
    return result


# =============================================================================
# DAG resolution
# =============================================================================


def _resolve_lod_path(dag_path):
    """The LOD ancestor of ``dag_path``, if any — the ``lod_path`` walk it stands for."""
    dag_node = dag_path.node()
    if dag_node.hasFn(om.MFn.kTransform) and attr.get_bool(dag_node, A.IS_LOD):
        return om.MDagPath(dag_path)
    walker = om.MDagPath(dag_path)
    if walker.hasFn(om.MFn.kMesh):
        walker.pop()
    while walker.length() > 0:
        if walker.node().hasFn(om.MFn.kTransform) and attr.get_bool(walker.node(), A.IS_LOD):
            return om.MDagPath(walker)
        walker.pop()
    return None


def _lod_paths_below(dag_path):
    """Every LOD transform under ``dag_path``, excluding ``dag_path`` itself."""
    root = om.MDagPath(dag_path)
    found = []
    iterator = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
    iterator.reset(root.node(), om.MItDag.kDepthFirst, om.MFn.kTransform)
    while not iterator.isDone():
        current = iterator.getPath()
        if (current.fullPathName() != root.fullPathName()
                and attr.get_bool(current.node(), A.IS_LOD)):
            found.append(om.MDagPath(current))
        iterator.next()
    return found


def resolve_lod_paths(dag_path):
    """The LODs a selected node stands for.

    Upward first: a mesh, or a component of one, means the LOD transform above it — picking
    one mesh must never drag in its siblings. Only when nothing upward is a LOD does this
    look DOWNWARD, so that selecting the folder holding a model's LODs exports that model.

    Without the downward half, a folder per model — the obvious way to keep several models
    bound for separate .p3d files apart in one scene — was the one arrangement that could
    not be exported at all."""
    resolved = _resolve_lod_path(dag_path)
    if resolved is not None:
        return [resolved]
    return _lod_paths_below(dag_path)


def _find_first_mesh_path(lod_path):
    lod_dag_fn = om.MFnDagNode(lod_path)
    for child_index in range(lod_dag_fn.childCount()):
        child = lod_dag_fn.child(child_index)
        if child.hasFn(om.MFn.kMesh):
            return om.MFnDagNode(child).getPath()
        if not child.hasFn(om.MFn.kTransform):
            continue
        child_fn = om.MFnDagNode(child)
        for grandchild_index in range(child_fn.childCount()):
            grandchild = child_fn.child(grandchild_index)
            if grandchild.hasFn(om.MFn.kMesh):
                return om.MFnDagNode(grandchild).getPath()
    return None


# =============================================================================
# material pairs
# =============================================================================


def _strip_drive(path):
    if len(path) >= 2 and path[1] == ":":
        path = path[2:]
        while path and path[0] == "\\":
            path = path[1:]
    return path


def _mesh_material_pairs(mesh):
    mesh_fn = om.MFnMesh(mesh)
    shaders, shader_indices = mesh_fn.getConnectedShaders(0)
    pairs = []
    for face_index in range(len(shader_indices)):
        shader_index = shader_indices[face_index]
        if 0 <= shader_index < len(shaders):
            tex = _strip_drive(attr.get_string(shaders[shader_index], A.TEXTURE).replace("/", "\\"))
            mat = _strip_drive(attr.get_string(shaders[shader_index], A.MATERIAL).replace("/", "\\"))
            pairs.append((tex, mat))
        else:
            pairs.append(("", ""))
    return pairs


# =============================================================================
# TAGG builders
# =============================================================================


def _parse_component_range(text):
    sep = text.find(":")
    if sep == -1:
        return [int(text)]
    first = int(text[:sep])
    last = int(text[sep + 1:])
    return list(range(first, last + 1))


def _read_set_components(set_obj, mesh_path):
    """Return (vertices set, faces set) selected by an objectSet on this mesh.

    Membership is listed with ``cmds.sets`` on purpose. ``MFnSet.getMembers()`` looks like the
    native answer, but it returns an MSelectionList, and that holds only ONE component type
    per DAG path: for a set containing both vertices and faces of the same mesh it hands back
    the vertices and drops every face. Measured on the character fixture, 1250 faces silently
    became 0.

    What IS fixed here is the ownership test. The old code compared member names against a
    guessed list of spellings (short name, full path, transform vs shape) and dropped anything
    matching none of them. Each distinct node name is now resolved once through the API and
    compared as a node, so namespaces and duplicated hierarchies cannot fool it."""
    vertices = set()
    faces = set()
    mesh_node = mesh_path.node()
    set_name = om.MFnDependencyNode(set_obj).name()
    members = cmds.sets(set_name, query=True) or []
    if not members:
        return vertices, faces

    resolved = {}  # node name -> is it this mesh? (a set usually references a single node)

    def belongs(node_name):
        hit = resolved.get(node_name)
        if hit is None:
            hit = False
            try:
                selection = om.MSelectionList()
                selection.add(node_name)
                dag_path = selection.getDagPath(0)
                if dag_path.node() == mesh_node:
                    hit = True
                else:
                    # Components may be stored against the transform ("Fire_Geometry.f[0:3]").
                    dag_path.extendToShape()
                    hit = dag_path.node() == mesh_node
            except Exception:  # noqa: BLE001 - gone, or not a DAG node
                hit = False
            resolved[node_name] = hit
        return hit

    for item in members:
        node_name, _, rest = item.partition(".")
        if not belongs(node_name):
            continue
        if rest.startswith("vtx["):
            vertices.update(_parse_component_range(rest[4:].rstrip("]")))
        elif rest.startswith("f["):
            faces.update(_parse_component_range(rest[2:].rstrip("]")))
        elif not rest:
            vertices.update(range(om.MFnMesh(mesh_path).numVertices))
    return vertices, faces


_FACE_VERTEX_CACHE = {}  # mesh node hash -> [tuple(vertex ids) per face]
_VERTEX_INCIDENT_CACHE = {}  # same key -> [list[face_index] per vertex]


def reset_face_vertex_cache():
    """Drop the cached tables. Called at the start of every LOD export.

    The caches must never outlive one export: an edit that keeps the polygon and vertex
    counts identical (a vertex reorder, say) would otherwise be served a stale table."""
    _FACE_VERTEX_CACHE.clear()
    _VERTEX_INCIDENT_CACHE.clear()


def _cache_key(mesh_path):
    mesh_fn = om.MFnMesh(mesh_path)
    return (om.MObjectHandle(mesh_path.node()).hashCode(), mesh_fn.numPolygons, mesh_fn.numVertices)


def _face_vertex_table(mesh_path):
    """Per-face vertex tuples, fetched once per mesh with a single bulk call.

    This used to be an MItMeshPolygon walk *per selection set*: on a 12k-face LOD with 40
    named selections that is half a million iterations, and it dominated export time (45% of
    the profile). MFnMesh.getVertices() returns the whole table in one call, and the result
    is reused for every set on the same mesh."""
    key = _cache_key(mesh_path)
    cached = _FACE_VERTEX_CACHE.get(key)
    if cached is not None:
        return cached

    mesh_fn = om.MFnMesh(mesh_path)
    counts, flat = mesh_fn.getVertices()
    counts = list(counts)
    flat = list(flat)
    table = []
    offset = 0
    for count in counts:
        table.append(tuple(flat[offset:offset + count]))
        offset += count
    _FACE_VERTEX_CACHE.clear()  # only ever need the mesh currently being exported
    _VERTEX_INCIDENT_CACHE.clear()
    _FACE_VERTEX_CACHE[key] = table
    return table


def _vertex_incident_table(mesh_path):
    """Per-vertex list of incident face ids, derived once per mesh from the face-vertex table.

    ``_derive_faces_from_vertices`` used to be O(faces * selections * corners): 12k faces x
    40 selections x 4 corners = ~2M superset ops per LOD. Inverting the walk — from face
    incidences of one member vertex — turns it into O(vertex_face_incidences_per_selection)
    with the same set semantics."""
    key = _cache_key(mesh_path)
    cached = _VERTEX_INCIDENT_CACHE.get(key)
    if cached is not None:
        return cached
    face_table = _face_vertex_table(mesh_path)
    table = [[] for _ in range(om.MFnMesh(mesh_path).numVertices)]
    for face_index, face_vertices in enumerate(face_table):
        for vertex in face_vertices:
            if 0 <= vertex < len(table):
                table[vertex].append(face_index)
    _VERTEX_INCIDENT_CACHE[key] = table
    return table


from a3ob.mayabridge.export.pure import derive_faces_pure  # re-exported below


def _derive_faces_from_vertices(mesh_path, vertices, faces):
    if not vertices:
        return
    derive_faces_pure(
        _face_vertex_table(mesh_path),
        _vertex_incident_table(mesh_path),
        vertices,
        faces,
    )


__all__ = [
    "maya_to_core_point",
    "maya_to_core_vector",
    "_split_semicolon",
    "_split_float_values",
    "_split_index_values",
    "_split_vertex_values",
    "_split_uvset_taggs",
    "_split_properties",
    "_resolve_lod_path",
    "resolve_lod_paths",
    "_find_first_mesh_path",
    "_strip_drive",
    "_mesh_material_pairs",
    "_parse_component_range",
    "_read_set_components",
    "_derive_faces_from_vertices",
    "derive_faces_pure",
    "reset_face_vertex_cache",
]
