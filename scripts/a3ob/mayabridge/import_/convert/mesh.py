"""Transform creation, ``a3ob*`` LOD-metadata serialization, and UV/normal application
for P3D import — geometry-detail helpers used by ``importer.py`` (which builds the mesh)."""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A


from a3ob.mayabridge.import_.convert.names import *  # noqa: F401,F403


def _name_to_object(name):
    sel = om.MSelectionList()
    sel.add(name)
    return sel.getDependNode(0)


def _create_transform(parent_name, name):
    kwargs = {"name": name, "skipSelect": True}
    if parent_name:
        kwargs["parent"] = parent_name
    return cmds.createNode("transform", **kwargs)


# =============================================================================
# metadata
# =============================================================================


def _store_weight_selections(transform, lod, vertex_map):
    """Keep the file's bone selections on the transform as ``a3obBakedWeights``.

    The .p3d stores weights as named vertex selections and knows nothing about skeletons.
    Import also turns them into a skinCluster, but that dies with the joints — this copy
    does not, so a model opened without its rig still exports its weights. The live
    skinCluster continues to win on export; this is only the fallback.

    Indices are stored in MAYA space. ``vertex_map`` runs Maya index -> P3D source index,
    so it is inverted once here rather than scanned per weight: the character fixture has
    LODs with thousands of vertices and a per-weight scan is quadratic on them."""
    reverse = {source: maya for maya, source in enumerate(vertex_map or [])}

    bone_rows = []
    for tagg in lod.taggs:
        if tagg.data is None or tagg.data.kind != "Selection" or tagg.is_proxy():
            continue
        if not isinstance(tagg.name, str) or tagg.name.startswith("#"):
            continue
        pairs = []
        for source_index, weight in tagg.data.vertex_weights:
            mapped = reverse.get(source_index) if reverse else source_index
            if mapped is not None and weight > 0.0:
                pairs.append("%d=%s" % (mapped, repr(float(weight))))
        if pairs:
            bone_rows.append("%s:%s" % (tagg.name, ",".join(pairs)))

    if bone_rows:
        attr.set_string(transform, A.BAKED_WEIGHTS, ";".join(bone_rows))


def set_lod_metadata(transform, lod, vertex_map):
    attr.set_bool(transform, A.IS_LOD, True)
    attr.set_int(transform, A.LOD_TYPE, lod.resolution.lod)
    attr.set_int(transform, A.RESOLUTION, lod.resolution.resolution)
    attr.set_double(transform, A.RESOLUTION_SIGNATURE, lod.resolution.source)
    attr.set_int(transform, A.SOURCE_VERTEX_COUNT, len(lod.vertices))
    attr.set_int(transform, A.SOURCE_FACE_COUNT, len(lod.faces))
    if vertex_map:
        attr.set_string(transform, A.VERTEX_SOURCE_INDICES, index_values_string(vertex_map))
    if lod.vertices:
        attr.set_string(transform, A.SOURCE_VERTICES, vertex_values_string(lod.vertices))

    # NOTE: a3obTextures / a3obMaterials / a3obSelections / a3obProxies used to be written
    # here and were never read back by anything — every one of them is derivable from the
    # scene itself (shader attrs, objectSets with a3obSelectionName, proxy transforms). They
    # cost a full sweep over every face on import for nothing, so they are no longer written.
    properties = []
    has_mass = False
    has_sharp_edges = False
    sharp_edges = ""
    uv_set_count = 0
    uv_set_taggs = []
    mass_values = None
    for tagg in lod.taggs:
        if tagg.data is None:
            continue
        kind = tagg.data.kind
        if kind == "Property":
            properties.append("%s=%s" % (tagg.data.key, tagg.data.value))
        elif kind == "Mass":
            has_mass = True
            if mass_values is None:
                mass_values = tagg.data.masses
        elif kind == "SharpEdges":
            has_sharp_edges = True
            sharp_edges = sharp_edges_string(tagg.data)
        elif kind == "UVSet":
            uv_set_count += 1
            uv_set_taggs.append(tagg.data)

    attr.set_string(transform, A.PROPERTIES, ";".join(properties))
    _store_weight_selections(transform, lod, vertex_map)
    attr.set_bool(transform, A.HAS_MASS, has_mass)
    if mass_values is not None:
        attr.set_string(transform, A.MASS_VALUES, float_values_string(mass_values))
    attr.set_bool(transform, A.HAS_SHARP_EDGES, has_sharp_edges)
    if sharp_edges:
        attr.set_string(transform, A.SHARP_EDGES, sharp_edges)
    attr.set_int(transform, A.UVSET_TAGG_COUNT, uv_set_count)
    # a3obUVSetTaggs is deliberately NOT written any more: set 0 lives in the mesh's own UVs
    # and the extra sets become real Maya UV sets (apply_extra_uv_sets). The blob was ~1.4 MB
    # per LOD and, being replayed verbatim on export, discarded UV edits made in Maya.


# =============================================================================
# geometry detail application
# =============================================================================


def apply_uvs(mesh_fn, lod):
    u_values = om.MFloatArray()
    v_values = om.MFloatArray()
    uv_counts = om.MIntArray()
    uv_ids = om.MIntArray()
    uv_lookup = {}
    for face in lod.faces:
        uv_counts.append(len(face.uvs))
        for uv in face.uvs:
            key = (uv.u, uv.v)
            uv_id = uv_lookup.get(key)
            if uv_id is None:
                uv_id = len(u_values)
                uv_lookup[key] = uv_id
                u_values.append(uv.u)
                v_values.append(uv.v)
            uv_ids.append(uv_id)
    if len(u_values) == 0:
        return
    mesh_fn.setUVs(u_values, v_values)
    mesh_fn.assignUVs(uv_counts, uv_ids)


def apply_extra_uv_sets(mesh_fn, lod):
    """Create a real Maya UV set for each #UVSet# TAGG beyond the first.

    Set 0 is already on the mesh (apply_uvs). The rest used to survive only as a string blob
    on the transform, invisible and uneditable in Maya; as real UV sets they show up in the
    UV editor and are read straight back on export."""
    sets = [tagg.data for tagg in lod.taggs
            if tagg.data is not None and tagg.data.kind == "UVSet"]
    if len(sets) < 2:
        return 0

    corner_total = sum(len(face.uvs) for face in lod.faces)
    created = 0
    for order, data in enumerate(sorted(sets, key=lambda d: d.id)[1:], start=1):
        if len(data.uvs) != corner_total:
            continue  # does not line up with the face corners — skip rather than corrupt
        try:
            name = mesh_fn.createUVSet("uvSet%d" % order)
            u_values = om.MFloatArray()
            v_values = om.MFloatArray()
            uv_counts = om.MIntArray()
            uv_ids = om.MIntArray()
            cursor = 0
            for face in lod.faces:
                uv_counts.append(len(face.uvs))
                for _corner in face.uvs:
                    uv = data.uvs[cursor]
                    uv_ids.append(len(u_values))
                    u_values.append(uv.u)
                    v_values.append(uv.v)
                    cursor += 1
            mesh_fn.setUVs(u_values, v_values, name)
            mesh_fn.assignUVs(uv_counts, uv_ids, name)
            created += 1
        except Exception:  # noqa: BLE001 - never let an odd UV set abort the import
            continue
    return created


def apply_sharp_edges(mesh_fn, lod, vertex_remap):
    """Harden the edges listed in the #SharpEdges# TAGG on the Maya mesh.

    Import used to only stash them in ``a3obSharpEdges``, leaving every edge smooth in Maya.
    Export then had to replay that blob, which meant hardening or softening an edge in Maya
    never reached the P3D. Applying them here makes the live mesh the single source of truth
    for both directions."""
    pairs = []
    for tagg in lod.taggs:
        if getattr(tagg.data, "kind", "") == "SharpEdges":
            pairs.extend(tagg.data.edges)
    if not pairs:
        return 0

    wanted = set()
    for first, second in pairs:
        a = vertex_remap.get(first)
        b = vertex_remap.get(second)
        if a is not None and b is not None and a != b:
            wanted.add((min(a, b), max(a, b)))
    if not wanted:
        return 0

    edge_it = om.MItMeshEdge(mesh_fn.object())
    hardened = 0
    while not edge_it.isDone():
        key = (min(edge_it.vertexId(0), edge_it.vertexId(1)),
               max(edge_it.vertexId(0), edge_it.vertexId(1)))
        if key in wanted:
            mesh_fn.setEdgeSmoothing(edge_it.index(), False)
            hardened += 1
        edge_it.next()
    if hardened:
        mesh_fn.cleanupEdgeSmoothing()
    return hardened


def apply_normals(mesh_fn, lod, vertex_remap):
    normals = om.MVectorArray()
    face_ids = om.MIntArray()
    vertex_ids = om.MIntArray()
    for face_index, face in enumerate(lod.faces):
        for corner, source_vertex in enumerate(face.vertices):
            if corner >= len(face.normals):
                continue
            normal_index = face.normals[corner]
            if normal_index >= len(lod.normals):
                continue
            mapped = vertex_remap.get(source_vertex)
            if mapped is None:
                continue
            normals.append(core_to_maya_vector(lod.normals[normal_index]))
            face_ids.append(face_index)
            vertex_ids.append(mapped)
    if len(normals) == 0:
        return
    mesh_fn.setFaceVertexNormals(normals, face_ids, vertex_ids, om.MSpace.kObject)
    mesh_fn.updateSurface()


# =============================================================================
# object sets
# =============================================================================


MEMORY_LOCATOR_SCALE = 0.05  # small crosshair so memory points read as tidy dots, not scene-wide crosses


def _leaf(name):
    return name.rsplit("|", 1)[-1]


__all__ = [
    "_name_to_object",
    "_create_transform",
    "set_lod_metadata",
    "apply_uvs",
    "apply_normals",
    "apply_sharp_edges",
    "apply_extra_uv_sets",
    "MEMORY_LOCATOR_SCALE",
    "_leaf",
]
