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

from . import attributes as attr
from .attributes import A
from ..formats import p3d
from ..formats.binary import BinaryWriter


class ExportOptions:
    __slots__ = ("selected_only", "visible_only", "apply_transforms", "apply_modifiers")

    def __init__(self, selected_only=False, visible_only=True, apply_transforms=True, apply_modifiers=True):
        self.selected_only = selected_only
        self.visible_only = visible_only
        self.apply_transforms = apply_transforms
        self.apply_modifiers = apply_modifiers


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


def _split_sharp_edges(value):
    edges = []
    for part in _split_semicolon(value):
        sep = part.find(",")
        if sep == -1:
            continue
        edges.append((int(part[:sep]), int(part[sep + 1:])))
    return edges


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
def _resolve_lod_path(path):
    node = path.node()
    if node.hasFn(om.MFn.kTransform) and attr.get_bool(node, A.IS_LOD):
        return om.MDagPath(path)
    path = om.MDagPath(path)
    if path.hasFn(om.MFn.kMesh):
        path.pop()
    while path.length() > 0:
        if path.node().hasFn(om.MFn.kTransform) and attr.get_bool(path.node(), A.IS_LOD):
            return om.MDagPath(path)
        path.pop()
    return None


def _find_first_mesh_path(transform_path):
    transform_fn = om.MFnDagNode(transform_path)
    for i in range(transform_fn.childCount()):
        child = transform_fn.child(i)
        if child.hasFn(om.MFn.kMesh):
            return om.MFnDagNode(child).getPath()
        if not child.hasFn(om.MFn.kTransform):
            continue
        child_fn = om.MFnDagNode(child)
        for j in range(child_fn.childCount()):
            grandchild = child_fn.child(j)
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
def _add_property_taggs(transform, lod):
    for key, value in _split_properties(attr.get_string(transform, A.PROPERTIES)):
        tagg = p3d.Tagg()
        tagg.name = "#Property#"
        tagg.data = p3d.PropertyTaggData(key, value)
        lod.taggs.append(tagg)


def _add_mass_tagg(transform, lod):
    values = attr.get_string(transform, A.MASS_VALUES)
    if not values:
        return
    tagg = p3d.Tagg()
    tagg.name = "#Mass#"
    data = p3d.MassTaggData()
    data.masses = _split_float_values(values)
    if len(data.masses) != len(lod.vertices):
        if len(data.masses) < len(lod.vertices):
            data.masses.extend([0.0] * (len(lod.vertices) - len(data.masses)))
        else:
            data.masses = data.masses[:len(lod.vertices)]
    tagg.data = data
    lod.taggs.append(tagg)


def _parse_component_range(text):
    sep = text.find(":")
    if sep == -1:
        return [int(text)]
    first = int(text[:sep])
    last = int(text[sep + 1:])
    return list(range(first, last + 1))


def _read_set_components(set_name, mesh_path):
    """Return (vertices set, faces set) selected by an objectSet on this mesh."""
    vertices = set()
    faces = set()
    members = cmds.sets(set_name, query=True) or []

    aliases = set()
    for name in (mesh_path.fullPathName(), mesh_path.partialPathName()):
        aliases.add(name)
        aliases.add(name.rsplit("|", 1)[-1])
    transform_path = om.MDagPath(mesh_path)
    transform_path.pop()
    for name in (transform_path.fullPathName(), transform_path.partialPathName()):
        aliases.add(name)
        aliases.add(name.rsplit("|", 1)[-1])

    mesh_fn = om.MFnMesh(mesh_path)
    for item in members:
        if ".vtx[" in item:
            obj, rng = item.split(".vtx[", 1)
            if obj.rsplit("|", 1)[-1] in aliases or obj in aliases:
                vertices.update(_parse_component_range(rng.rstrip("]")))
        elif ".f[" in item:
            obj, rng = item.split(".f[", 1)
            if obj.rsplit("|", 1)[-1] in aliases or obj in aliases:
                faces.update(_parse_component_range(rng.rstrip("]")))
        elif item.rsplit("|", 1)[-1] in aliases or item in aliases:
            vertices.update(range(mesh_fn.numVertices))
    return vertices, faces


def _derive_faces_from_vertices(mesh_path, vertices, faces):
    if not vertices:
        return
    it = om.MItMeshPolygon(mesh_path.node())
    while not it.isDone():
        face_vertices = it.getVertices()
        selected = len(face_vertices) > 0 and all(v in vertices for v in face_vertices)
        if selected:
            faces.add(it.index())
        it.next()


def _add_selection_and_flag_data(mesh_path, vertex_source_indices, lod):
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        set_obj = it.thisNode()
        it.next()
        set_name = om.MFnDependencyNode(set_obj).name()
        vertices, faces = _read_set_components(set_name, mesh_path)
        if not vertices and not faces:
            continue

        selection_name = attr.get_string(set_obj, A.SELECTION_NAME)
        if selection_name:
            _derive_faces_from_vertices(mesh_path, vertices, faces)
            tagg = p3d.Tagg()
            tagg.name = selection_name
            data = p3d.SelectionTaggData()
            data.count_verts = len(lod.vertices)
            data.count_faces = len(lod.faces)
            for vertex in sorted(vertices):
                if vertex < 0:
                    continue
                source_index = vertex
                if vertex < len(vertex_source_indices):
                    source_index = vertex_source_indices[vertex]
                if source_index < len(lod.vertices):
                    data.vertex_weights.append((source_index, 1.0))
            for face in sorted(faces):
                if 0 <= face < len(lod.faces):
                    data.face_weights.append((face, 1.0))
            tagg.data = data
            lod.taggs.append(tagg)
            continue

        flag_value = attr.get_int(set_obj, A.FLAG_VALUE, 0)
        flag_component = attr.get_string(set_obj, A.FLAG_COMPONENT)
        if flag_value == 0 or not flag_component:
            continue
        if flag_component == "vertex":
            for vertex in vertices:
                if vertex < 0:
                    continue
                source_index = vertex
                if vertex < len(vertex_source_indices):
                    source_index = vertex_source_indices[vertex]
                if source_index < len(lod.vertices):
                    lod.vertices[source_index].flag = flag_value
        elif flag_component == "face":
            for face in faces:
                if 0 <= face < len(lod.faces):
                    lod.faces[face].flag = flag_value


def _add_sharp_edges_tagg(transform, mesh_path, lod):
    if not attr.get_bool(transform, A.HAS_SHARP_EDGES):
        return
    saved = _split_sharp_edges(attr.get_string(transform, A.SHARP_EDGES))
    if saved:
        tagg = p3d.Tagg()
        tagg.name = "#SharpEdges#"
        data = p3d.SharpEdgesTaggData()
        data.edges = saved
        tagg.data = data
        lod.taggs.append(tagg)
        return

    data = p3d.SharpEdgesTaggData()
    edge_it = om.MItMeshEdge(mesh_path)
    while not edge_it.isDone():
        if not edge_it.isSmooth:
            first = edge_it.vertexId(0)
            second = edge_it.vertexId(1)
            if 0 <= first < len(lod.vertices) and 0 <= second < len(lod.vertices):
                data.edges.append((first, second))
        edge_it.next()
    if not data.edges:
        return
    tagg = p3d.Tagg()
    tagg.name = "#SharpEdges#"
    tagg.data = data
    lod.taggs.append(tagg)


def _add_uvset_taggs(transform, lod):
    saved = _split_uvset_taggs(attr.get_string(transform, A.UVSET_TAGGS))
    if saved:
        for data in saved:
            tagg = p3d.Tagg()
            tagg.name = "#UVSet#"
            tagg.data = data
            lod.taggs.append(tagg)
        return

    count = max(1, attr.get_int(transform, A.UVSET_TAGG_COUNT, 0))
    uvs = []
    for face in lod.faces:
        uvs.extend(face.uvs)
    if not uvs:
        return
    for i in range(count):
        tagg = p3d.Tagg()
        tagg.name = "#UVSet#"
        data = p3d.UVSetTaggData()
        data.id = i
        data.uvs = [p3d.Vec2(uv.u, uv.v) for uv in uvs]
        tagg.data = data
        lod.taggs.append(tagg)


# =============================================================================
# Memory LOD locators
# =============================================================================
def _has_direct_locator_shape(dag_fn):
    for j in range(dag_fn.childCount()):
        if dag_fn.child(j).hasFn(om.MFn.kLocator):
            return True
    return False


def _collect_locators_from_memory_lod(transform_path, options, lod):
    lod_dag = om.MFnDagNode(transform_path)
    points = []  # (selection_name, vertex_index)

    def add_locator_vertex(loc_path, sel_name):
        if options.apply_transforms:
            bake = loc_path.inclusiveMatrix()
        else:
            bake = loc_path.inclusiveMatrix() * transform_path.inclusiveMatrix().inverse()
        world_pos = om.MPoint(0.0, 0.0, 0.0) * bake
        vertex_index = len(lod.vertices)
        lod.vertices.append(p3d.Vertex(maya_to_core_point(world_pos), 0))
        points.append((sel_name, vertex_index))

    for i in range(lod_dag.childCount()):
        child = lod_dag.child(i)
        if not child.hasFn(om.MFn.kTransform):
            continue
        if attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
            continue
        child_fn = om.MFnDagNode(child)
        if _has_direct_locator_shape(child_fn):
            sel_name = attr.get_string(child, A.SELECTION_NAME) or child_fn.name()
            add_locator_vertex(child_fn.getPath(), sel_name)
        else:
            group_sel_name = attr.get_string(child, A.SELECTION_NAME) or child_fn.name()
            for j in range(child_fn.childCount()):
                grandchild = child_fn.child(j)
                if not grandchild.hasFn(om.MFn.kTransform):
                    continue
                if attr.get_bool_any(grandchild, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
                    continue
                grandchild_fn = om.MFnDagNode(grandchild)
                if not _has_direct_locator_shape(grandchild_fn):
                    continue
                add_locator_vertex(grandchild_fn.getPath(), group_sel_name)

    if not points:
        return False

    ordered_names = []
    selection_vertices = {}
    for sel_name, vertex_index in points:
        if sel_name not in selection_vertices:
            ordered_names.append(sel_name)
            selection_vertices[sel_name] = []
        selection_vertices[sel_name].append(vertex_index)

    total_verts = len(lod.vertices)
    for name in ordered_names:
        tagg = p3d.Tagg()
        tagg.name = name
        data = p3d.SelectionTaggData()
        data.count_verts = total_verts
        data.count_faces = 0
        for idx in selection_vertices[name]:
            data.vertex_weights.append((idx, 1.0))
        tagg.data = data
        lod.taggs.append(tagg)
    return True


# =============================================================================
# per-LOD export
# =============================================================================
def _lod_sort_key(transform_path):
    node = transform_path.node()
    lod_type = attr.get_int(node, A.LOD_TYPE, 0)
    resolution = attr.get_int(node, A.RESOLUTION, 0)
    return attr.get_double(node, A.RESOLUTION_SIGNATURE, p3d.LodResolution.encode(lod_type, resolution))


def _export_mesh_lod(transform_path, options):
    node = transform_path.node()
    lod_type = attr.get_int(node, A.LOD_TYPE, 0)
    resolution = attr.get_int(node, A.RESOLUTION, 0)
    signature = attr.get_double(node, A.RESOLUTION_SIGNATURE, p3d.LodResolution.encode(lod_type, resolution))
    lod = p3d.LOD()
    lod.resolution = p3d.LodResolution.from_float(signature)

    mesh_path = _find_first_mesh_path(transform_path)
    if mesh_path is None:
        if lod_type == 9 and _collect_locators_from_memory_lod(transform_path, options, lod):
            _add_property_taggs(node, lod)
            return lod
        lod.vertices = _split_vertex_values(attr.get_string(node, A.SOURCE_VERTICES))
        if not lod.vertices:
            source_vertex_count = attr.get_int(node, A.SOURCE_VERTEX_COUNT, 0)
            if source_vertex_count > 0:
                lod.vertices = [p3d.Vertex() for _ in range(source_vertex_count)]
        _add_property_taggs(node, lod)
        _add_mass_tagg(node, lod)
        return lod

    mesh_fn = om.MFnMesh(mesh_path)
    points = mesh_fn.getPoints(om.MSpace.kObject)

    if options.apply_transforms:
        bake_matrix = mesh_path.inclusiveMatrix()
        normal_matrix = bake_matrix.inverse().transpose()
    else:
        bake_matrix = om.MMatrix()
        normal_matrix = om.MMatrix()
    baked = [points[i] * bake_matrix for i in range(len(points))]

    vertex_source_indices = _split_index_values(attr.get_string(node, A.VERTEX_SOURCE_INDICES))
    source_vertices = _split_vertex_values(attr.get_string(node, A.SOURCE_VERTICES))
    if len(vertex_source_indices) == len(baked) and source_vertices:
        lod.vertices = source_vertices
        for i in range(len(baked)):
            source_index = vertex_source_indices[i]
            if source_index < len(lod.vertices):
                lod.vertices[source_index].position = maya_to_core_point(baked[i])
    else:
        lod.vertices = [p3d.Vertex(maya_to_core_point(baked[i]), 0) for i in range(len(baked))]

    material_pairs = _mesh_material_pairs(mesh_path.node())
    u_array, v_array = mesh_fn.getUVs()

    polygon_it = om.MItMeshPolygon(mesh_path)
    while not polygon_it.isDone():
        vertex_ids = polygon_it.getVertices()
        face_index = polygon_it.index()
        face = p3d.Face()
        if 0 <= face_index < len(material_pairs):
            face.texture = material_pairs[face_index][0]
            face.material = material_pairs[face_index][1]

        def emit_face_corner(target_face, local_idx, maya_vertex_id):
            vertex_index = maya_vertex_id
            if len(vertex_source_indices) == len(baked) and maya_vertex_id < len(vertex_source_indices):
                vertex_index = vertex_source_indices[maya_vertex_id]
            target_face.vertices.append(vertex_index)
            target_face.normals.append(len(lod.normals))
            try:
                normal = polygon_it.getNormal(local_idx, om.MSpace.kObject)
            except Exception:
                normal = om.MVector(0.0, 1.0, 0.0)
            if options.apply_transforms:
                normal = normal * normal_matrix
            lod.normals.append(maya_to_core_vector(normal))
            uv = None
            if len(u_array) > 0:
                try:
                    uv_id = polygon_it.getUVIndex(local_idx)
                    if 0 <= uv_id < len(u_array):
                        uv = p3d.Vec2(u_array[uv_id], v_array[uv_id])
                except Exception:
                    uv = None
            target_face.uvs.append(uv if uv is not None else p3d.Vec2(0.0, 0.0))

        if len(vertex_ids) <= 4:
            for i in range(len(vertex_ids)):
                emit_face_corner(face, i, vertex_ids[i])
            lod.faces.append(face)
        else:
            num_tris = polygon_it.numTriangles()
            for tri_idx in range(num_tris):
                _tri_points, tri_vertices = polygon_it.getTriangle(tri_idx, om.MSpace.kObject)
                tri_face = p3d.Face()
                tri_face.texture = face.texture
                tri_face.material = face.material
                for j in range(len(tri_vertices)):
                    local_idx = 0
                    for k in range(len(vertex_ids)):
                        if vertex_ids[k] == tri_vertices[j]:
                            local_idx = k
                            break
                    emit_face_corner(tri_face, local_idx, tri_vertices[j])
                lod.faces.append(tri_face)
        polygon_it.next()

    _add_property_taggs(node, lod)
    _add_mass_tagg(node, lod)
    _add_selection_and_flag_data(mesh_path, vertex_source_indices, lod)
    _add_sharp_edges_tagg(node, mesh_path, lod)
    _add_uvset_taggs(node, lod)

    lod.renormalize_normals()
    return lod


# =============================================================================
# exporter
# =============================================================================
class MayaMeshExport:
    def export_mlod(self, path, options=None):
        if options is None:
            options = ExportOptions()

        lod_entries = []  # (sort_key, MDagPath)

        if options.selected_only:
            selection = om.MGlobal.getActiveSelectionList()
            exported_paths = set()
            selected_names = selection.getSelectionStrings() if hasattr(selection, "getSelectionStrings") else []
            for i in range(selection.length()):
                try:
                    selected_path = selection.getDagPath(i)
                except Exception:
                    continue
                lod_path = _resolve_lod_path(selected_path)
                if lod_path is None:
                    continue
                full_path = lod_path.fullPathName()
                if full_path in exported_paths:
                    continue
                exported_paths.add(full_path)
                lod_entries.append((_lod_sort_key(lod_path), lod_path))
            if not lod_entries and selected_names:
                om.MGlobal.displayError("P3D export failed: selection does not contain an Object Builder LOD, LOD mesh, or mesh component: " + ", ".join(selected_names))
                return False
        else:
            it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
            while not it.isDone():
                transform_path = it.getPath()
                node = transform_path.node()
                if attr.get_bool(node, A.IS_LOD):
                    if not (options.visible_only and not transform_path.isVisible()):
                        lod_entries.append((_lod_sort_key(transform_path), om.MDagPath(transform_path)))
                it.next()

        if not lod_entries:
            om.MGlobal.displayError(
                "P3D export failed: select an Object Builder LOD or its mesh"
                if options.selected_only else
                "P3D export failed: no transforms with a3obIsLOD found")
            return False

        lod_entries.sort(key=lambda entry: entry[0])

        mlod = p3d.MLOD()
        try:
            with BinaryWriter(path) as writer:
                mlod.begin_write(writer, len(lod_entries))
                for _sort_key, dag_path in lod_entries:
                    lod = _export_mesh_lod(dag_path, options)
                    mlod.write_lod(writer, lod)
        except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
            om.MGlobal.displayError("P3D export failed: %s" % error)
            return False

        om.MGlobal.displayInfo("Exported P3D MLOD LOD count: %d" % len(lod_entries))
        return True
