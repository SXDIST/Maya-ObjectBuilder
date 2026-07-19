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


def _object_builder_set_objects():
    """Every objectSet carrying a3ob metadata, in DG order.

    The export used to read the MEMBERS of every set in the scene — shading engines, render
    layers, deformer sets included — once per LOD, only to discover it was not ours. The
    attribute check below is a plug lookup and settles that far more cheaply.

    DG iteration order is kept on purpose: it decides the order the selection TAGGs land in
    the file. Listing by attribute (cmds.ls("*.a3obSelectionName")) is faster still, but it
    reorders them, and there is no reason to churn the output format for that."""
    found = []
    it = om.MItDependencyNodes(om.MFn.kSet)
    while not it.isDone():
        set_obj = it.thisNode()
        it.next()
        dep = om.MFnDependencyNode(set_obj)
        if dep.hasAttribute(A.SELECTION_NAME[0]) or dep.hasAttribute(A.FLAG_COMPONENT[0]):
            found.append(set_obj)
    return found


def _add_selection_and_flag_data(mesh_path, vertex_source_indices, lod):
    for set_obj in _object_builder_set_objects():
        vertices, faces = _read_set_components(set_obj, mesh_path)
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


def _add_sharp_edges_tagg(transform, mesh_path, vertex_source_indices, lod):
    """Write #SharpEdges# from the LIVE mesh; the stored blob is only a fallback.

    Import now hardens these edges on the Maya mesh (``apply_sharp_edges``), so the mesh is
    authoritative. Replaying the stored blob instead meant hardening or softening an edge in
    Maya never reached the P3D."""
    def to_source(vertex):
        # Edge ids come from the Maya mesh; the TAGG indexes P3D source vertices.
        if 0 <= vertex < len(vertex_source_indices):
            return vertex_source_indices[vertex]
        return vertex

    data = p3d.SharpEdgesTaggData()
    edge_it = om.MItMeshEdge(mesh_path)
    while not edge_it.isDone():
        if not edge_it.isSmooth:
            first = to_source(edge_it.vertexId(0))
            second = to_source(edge_it.vertexId(1))
            if 0 <= first < len(lod.vertices) and 0 <= second < len(lod.vertices):
                data.edges.append((first, second))
        edge_it.next()
    if not data.edges:
        return
    tagg = p3d.Tagg()
    tagg.name = "#SharpEdges#"
    tagg.data = data
    lod.taggs.append(tagg)


def _append_uvset_tagg(lod, data):
    tagg = p3d.Tagg()
    tagg.name = "#UVSet#"
    tagg.data = data
    lod.taggs.append(tagg)


def _add_uvset_taggs(transform, lod, extra_uv_corners=None):
    """Write the #UVSet# TAGGs from the LIVE Maya mesh.

    Every set now comes from the mesh itself: set 0 from the exported face corners, further
    sets from real Maya UV sets (collected in the export loop so triangulation applies to
    them too). Import creates those UV sets, so nothing has to be stashed on the transform —
    the old ``a3obUVSetTaggs`` blob cost ~1.4 MB per LOD and, being replayed verbatim, threw
    away any UV edit made in Maya.

    The stored blob is still READ so scenes saved by older versions keep their extra sets."""
    live = []
    for face in lod.faces:
        live.extend(face.uvs)

    if not live:
        # Mesh-less LOD: nothing to rebuild from, so a stored blob is all there is.
        for data in _split_uvset_taggs(attr.get_string(transform, A.UVSET_TAGGS)):
            _append_uvset_tagg(lod, data)
        return

    primary = p3d.UVSetTaggData()
    primary.id = 0
    primary.uvs = [p3d.Vec2(uv.u, uv.v) for uv in live]
    _append_uvset_tagg(lod, primary)

    next_id = 1
    for corners in (extra_uv_corners or []):
        if len(corners) != len(live):
            continue  # a set that does not cover every corner would misalign with the faces
        data = p3d.UVSetTaggData()
        data.id = next_id
        data.uvs = [p3d.Vec2(uv.u, uv.v) for uv in corners]
        _append_uvset_tagg(lod, data)
        next_id += 1

    if next_id > 1:
        return

    # Legacy scenes: extra sets were never applied to the mesh, so fall back to the blob.
    for data in _split_uvset_taggs(attr.get_string(transform, A.UVSET_TAGGS)):
        if getattr(data, "id", 0) == 0 or len(data.uvs) != len(live):
            continue
        data.id = next_id
        _append_uvset_tagg(lod, data)
        next_id += 1


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
