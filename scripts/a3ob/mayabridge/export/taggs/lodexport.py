"""Per-LOD mesh export: assemble one LOD's vertices, faces and UVs from the Maya mesh
(triangulating n-gons) and attach its TAGGs."""

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.formats import p3d


from a3ob.mayabridge.export.parse import *  # noqa: F401,F403

from a3ob.mayabridge.export.taggs.data import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.memory import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs.skin import *  # noqa: F401,F403


def _lod_sort_key(lod_path):
    lod_node = lod_path.node()
    lod_type = attr.get_int(lod_node, A.LOD_TYPE, 0)
    resolution = attr.get_int(lod_node, A.RESOLUTION, 0)
    return attr.get_double(lod_node, A.RESOLUTION_SIGNATURE, p3d.LodResolution.encode(lod_type, resolution))


def _export_empty_lod(lod_path, lod_node, lod_type, lod, options):
    """A mesh-less LOD: Memory-LOD locators OR the stored source-vertex fallback.

    Property/Mass TAGGs are attached last so an empty geometry LOD still carries its named
    properties."""
    if lod_type == 9 and _collect_locators_from_memory_lod(lod_path, options, lod):
        _add_property_taggs(lod_node, lod)
        return
    lod.vertices = _split_vertex_values(attr.get_string(lod_node, A.SOURCE_VERTICES))
    if not lod.vertices:
        source_vertex_count = attr.get_int(lod_node, A.SOURCE_VERTEX_COUNT, 0)
        if source_vertex_count > 0:
            lod.vertices = [p3d.Vertex() for _ in range(source_vertex_count)]
    _add_property_taggs(lod_node, lod)
    _add_mass_tagg(lod_node, lod)


def _bake_points(mesh_path, options):
    """Baked object-space points and the matrix normals must be multiplied by.

    ``apply_transforms`` folds the LOD's world matrix into the point positions and returns
    the inverse-transpose for normal transformation. Otherwise both matrices are identity,
    the mesh exports in its own object space, and normals are written unmodified."""
    mesh_fn = om.MFnMesh(mesh_path)
    points = mesh_fn.getPoints(om.MSpace.kObject)
    if options.apply_transforms:
        bake_matrix = mesh_path.inclusiveMatrix()
        normal_matrix = bake_matrix.inverse().transpose()
    else:
        bake_matrix = om.MMatrix()
        normal_matrix = om.MMatrix()
    baked = [points[vertex_index] * bake_matrix for vertex_index in range(len(points))]
    return baked, normal_matrix


def _apply_stored_source_vertices(lod_node, baked, lod):
    """Fill ``lod.vertices`` from stored a3ob* source-vertex metadata when it lines up with
    the current Maya mesh; otherwise fall back to the baked positions in Maya order.

    Returns the ``vertex_source_indices`` list — empty (or of a mismatched length) means no
    remap is active. When active, corner emission below rewrites Maya vertex ids into the
    P3D-source ids the stored blob defines."""
    vertex_source_indices = _split_index_values(attr.get_string(lod_node, A.VERTEX_SOURCE_INDICES))
    source_vertices = _split_vertex_values(attr.get_string(lod_node, A.SOURCE_VERTICES))
    if len(vertex_source_indices) == len(baked) and source_vertices:
        lod.vertices = source_vertices
        for vertex_index in range(len(baked)):
            source_index = vertex_source_indices[vertex_index]
            if source_index < len(lod.vertices):
                lod.vertices[source_index].position = maya_to_core_point(baked[vertex_index])
    else:
        lod.vertices = [p3d.Vertex(maya_to_core_point(baked[vertex_index]), 0)
                        for vertex_index in range(len(baked))]
    return vertex_source_indices


def _read_extra_uv_sets(mesh_fn):
    """Bulk-read every UV set past the first: a set at a time, or none for a single-set mesh.

    Secondary sets are collected here (not after the face loop) so n-gon triangulation
    applies to them identically — reading them afterwards would misalign the UV corners
    with the face table the moment a face gets split."""
    extra_uv_sets = []
    for set_name in (mesh_fn.getUVSetNames() or [])[1:]:
        try:
            set_u, set_v = mesh_fn.getUVs(set_name)
            set_counts, set_ids = mesh_fn.getAssignedUVs(set_name)
            extra_uv_sets.append({
                "u": set_u, "v": set_v,
                "counts": list(set_counts), "ids": list(set_ids),
                "offset": 0, "corners": [],
            })
        except Exception:  # noqa: BLE001 - a broken UV set must not abort the export
            continue
    return extra_uv_sets


def _faces_from_mesh(mesh_path, lod, vertex_source_indices, normal_matrix, options):
    """Populate ``lod.faces`` / ``lod.normals`` from the Maya mesh, triangulating n-gons.

    Returns the extra UV-set corner arrays, parallel to the (triangulated) face corners.
    The corner-emit lambda captures the running offsets and the bulk arrays — extraction of
    the loop into a plain function would either move those closures too or turn every
    variable into a parameter and lose clarity."""
    mesh_fn = om.MFnMesh(mesh_path)
    material_pairs = _mesh_material_pairs(mesh_path.node())
    u_array, v_array = mesh_fn.getUVs()

    # Bulk reads instead of per-face-corner API calls. The old MItMeshPolygon loop called
    # getNormal() and getUVIndex() once per corner — on a 12k-face mesh that is ~120 000
    # round-trips into Maya. These five calls fetch the same data as flat arrays; everything
    # below is plain indexing.
    # list() on purpose: indexing an MIntArray from Python crosses into C++ on EVERY access,
    # which cancels out the benefit of fetching in bulk. Convert once, then index natively.
    face_vertex_counts = list(mesh_fn.getVertices()[0])
    face_vertex_list = list(mesh_fn.getVertices()[1])
    normals_table = mesh_fn.getNormals(om.MSpace.kObject)
    normal_ids = list(mesh_fn.getNormalIds()[1])
    _uv_counts, _uv_ids = mesh_fn.getAssignedUVs()
    uv_counts = list(_uv_counts)
    uv_ids = list(_uv_ids)

    extra_uv_sets = _read_extra_uv_sets(mesh_fn)

    _tri_counts, _tri_vertices = mesh_fn.getTriangles()
    triangle_counts = list(_tri_counts)
    triangle_vertices = list(_tri_vertices)

    remap_active = len(vertex_source_indices) == mesh_fn.numVertices
    corner_offset = 0   # running index into face_vertex_list / normal_ids
    uv_offset = 0       # running index into uv_ids — faces without UVs contribute nothing
    triangle_offset = 0

    for face_index in range(len(face_vertex_counts)):
        corner_count = face_vertex_counts[face_index]
        face_uv_count = uv_counts[face_index] if face_index < len(uv_counts) else 0
        vertex_ids = [face_vertex_list[corner_offset + corner_index]
                      for corner_index in range(corner_count)]

        face = p3d.Face()
        if 0 <= face_index < len(material_pairs):
            face.texture = material_pairs[face_index][0]
            face.material = material_pairs[face_index][1]

        def emit_face_corner(target_face, local_idx, maya_vertex_id):
            vertex_index = maya_vertex_id
            if remap_active and maya_vertex_id < len(vertex_source_indices):
                vertex_index = vertex_source_indices[maya_vertex_id]
            target_face.vertices.append(vertex_index)
            target_face.normals.append(len(lod.normals))

            normal_id = normal_ids[corner_offset + local_idx]
            if 0 <= normal_id < len(normals_table):
                source = normals_table[normal_id]
                normal = om.MVector(source.x, source.y, source.z)
            else:
                normal = om.MVector(0.0, 1.0, 0.0)
            if options.apply_transforms:
                normal = normal * normal_matrix
            lod.normals.append(maya_to_core_vector(normal))

            uv = None
            if len(u_array) > 0 and local_idx < face_uv_count:
                uv_id = uv_ids[uv_offset + local_idx]
                if 0 <= uv_id < len(u_array):
                    uv = p3d.Vec2(u_array[uv_id], v_array[uv_id])
            target_face.uvs.append(uv if uv is not None else p3d.Vec2(0.0, 0.0))

            for uv_set in extra_uv_sets:
                extra = None
                set_face_count = uv_set["counts"][face_index] if face_index < len(uv_set["counts"]) else 0
                if local_idx < set_face_count:
                    extra_id = uv_set["ids"][uv_set["offset"] + local_idx]
                    if 0 <= extra_id < len(uv_set["u"]):
                        extra = p3d.Vec2(uv_set["u"][extra_id], uv_set["v"][extra_id])
                uv_set["corners"].append(extra if extra is not None else p3d.Vec2(0.0, 0.0))

        if corner_count <= 4:
            for corner_index in range(corner_count):
                emit_face_corner(face, corner_index, vertex_ids[corner_index])
            lod.faces.append(face)
        else:
            local_of_vertex = {}
            for corner_index in range(corner_count - 1, -1, -1):
                # first occurrence wins, as before — walk from the end so lower indices overwrite
                local_of_vertex[vertex_ids[corner_index]] = corner_index
            for tri_index in range(triangle_counts[face_index]):
                base = (triangle_offset + tri_index) * 3
                tri_face = p3d.Face()
                tri_face.texture = face.texture
                tri_face.material = face.material
                for corner_index in range(3):
                    tri_vertex = triangle_vertices[base + corner_index]
                    emit_face_corner(tri_face, local_of_vertex.get(tri_vertex, 0), tri_vertex)
                lod.faces.append(tri_face)

        corner_offset += corner_count
        uv_offset += face_uv_count
        triangle_offset += triangle_counts[face_index]
        for uv_set in extra_uv_sets:
            if face_index < len(uv_set["counts"]):
                uv_set["offset"] += uv_set["counts"][face_index]

    return [uv_set["corners"] for uv_set in extra_uv_sets]


def _taggs_for_lod(lod_node, mesh_path, vertex_source_indices, lod, extra_uv_corners,
                   options, object_builder_sets):
    """Attach every TAGG to ``lod`` in the order the file format expects.

    Order matters: Property/Mass first, selections and flags next, then generated Component
    selections (opt-in), then #SharpEdges#, then #UVSet#. The live skinCluster wins over
    the baked-weights fallback; both are appended alongside selections."""
    _add_property_taggs(lod_node, lod)
    _add_mass_tagg(lod_node, lod)
    _add_selection_and_flag_data(mesh_path, vertex_source_indices, lod, object_builder_sets)
    # The live skinCluster wins; baked weights are the fallback for a scene whose skeleton
    # has been deleted (which removes the skinCluster and every weight with it).
    if _add_skin_weight_taggs(mesh_path, vertex_source_indices, lod) == 0:
        _add_baked_weight_taggs(lod_node, vertex_source_indices, lod)
    if getattr(options, "generate_components", False):
        lod_type = attr.get_int(lod_node, A.LOD_TYPE, 0)
        _add_generated_components(lod_type, mesh_path, vertex_source_indices, lod)
    _add_sharp_edges_tagg(lod_node, mesh_path, vertex_source_indices, lod)
    _add_uvset_taggs(lod_node, lod, extra_uv_corners)


def _export_mesh_lod(lod_path, options, object_builder_sets=None):
    lod_node = lod_path.node()
    lod_type = attr.get_int(lod_node, A.LOD_TYPE, 0)
    resolution = attr.get_int(lod_node, A.RESOLUTION, 0)
    signature = attr.get_double(lod_node, A.RESOLUTION_SIGNATURE, p3d.LodResolution.encode(lod_type, resolution))
    lod = p3d.LOD()
    lod.resolution = p3d.LodResolution.from_float(signature)

    mesh_path = _find_first_mesh_path(lod_path)
    if mesh_path is None:
        _export_empty_lod(lod_path, lod_node, lod_type, lod, options)
        return lod

    reset_face_vertex_cache()
    baked, normal_matrix = _bake_points(mesh_path, options)
    vertex_source_indices = _apply_stored_source_vertices(lod_node, baked, lod)
    extra_uv_corners = _faces_from_mesh(mesh_path, lod, vertex_source_indices, normal_matrix, options)
    _taggs_for_lod(lod_node, mesh_path, vertex_source_indices, lod, extra_uv_corners,
                   options, object_builder_sets)
    lod.renormalize_normals()
    return lod


# =============================================================================
# exporter
# =============================================================================


__all__ = [
    "_lod_sort_key",
    "_export_mesh_lod",
]
