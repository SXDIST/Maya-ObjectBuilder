"""P3D TAGG builders for export: property, mass, selection, flag, sharp-edge and UVSet
TAGG assembly from the Maya scene's ``a3ob*`` data."""

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.formats import p3d


from a3ob.mayabridge.export.parse import *  # noqa: F401,F403



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


_GEOMETRY_COMPONENT_TYPES = frozenset((6, 7, 8, 14, 15))


def _add_generated_components(lod_type, mesh_path, vertex_source_indices, lod):
    """Synthesize Component## vertex selections for a geometry LOD straight into the P3D
    data — from the mesh's closed face islands, WITHOUT creating any scene sets. Skipped
    unless the LOD is a geometry type and has no Component selection yet, so manually made
    components are never touched (the user's #5.2 concern)."""
    if lod_type not in _GEOMETRY_COMPONENT_TYPES:
        return
    for tagg in lod.taggs:
        if isinstance(tagg.name, str) and tagg.name.lower().startswith("component"):
            return
    from a3ob.mayabridge.commands.helpers.geometry import closed_face_islands
    mesh_fn = om.MFnMesh(mesh_path)
    index = 0
    for island_faces, island_vertices, closed in closed_face_islands(mesh_fn):
        if not closed or not island_vertices:
            continue
        index += 1
        faces = set(island_faces)
        _derive_faces_from_vertices(mesh_path, set(island_vertices), faces)
        tagg = p3d.Tagg()
        tagg.name = "Component%02d" % index
        data = p3d.SelectionTaggData()
        data.count_verts = len(lod.vertices)
        data.count_faces = len(lod.faces)
        for vertex in sorted(island_vertices):
            if vertex < 0:
                continue
            source_index = vertex_source_indices[vertex] if vertex < len(vertex_source_indices) else vertex
            if source_index < len(lod.vertices):
                data.vertex_weights.append((source_index, 1.0))
        for face in sorted(faces):
            if 0 <= face < len(lod.faces):
                data.face_weights.append((face, 1.0))
        tagg.data = data
        lod.taggs.append(tagg)


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


__all__ = [
    "_add_property_taggs",
    "_add_mass_tagg",
    "_add_selection_and_flag_data",
    "_add_generated_components",
    "_add_sharp_edges_tagg",
    "_add_uvset_taggs",
]
