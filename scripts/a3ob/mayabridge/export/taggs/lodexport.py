"""lodexport."""

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
from a3ob.formats.binary import BinaryWriter


from a3ob.mayabridge.export.parse import *  # noqa: F401,F403

from a3ob.mayabridge.export.taggs.data import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.memory import *  # noqa: F401,F403


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
    if getattr(options, "generate_components", False):
        _add_generated_components(lod_type, mesh_path, vertex_source_indices, lod)
    _add_sharp_edges_tagg(node, mesh_path, lod)
    _add_uvset_taggs(node, lod)

    lod.renormalize_normals()
    return lod


# =============================================================================
# exporter
# =============================================================================


__all__ = [
    "_lod_sort_key",
    "_export_mesh_lod",
]
