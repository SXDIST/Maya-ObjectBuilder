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

    textures = sorted({face.texture for face in lod.faces if face.texture})
    materials = sorted({face.material for face in lod.faces if face.material})

    properties = []
    selections = []
    proxies = []
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
        elif kind == "Selection":
            if tagg.is_proxy():
                proxies.append(tagg.name)
            else:
                selections.append(tagg.name)
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

    attr.set_string(transform, A.TEXTURES, ";".join(textures))
    attr.set_string(transform, A.MATERIALS, ";".join(materials))
    attr.set_string(transform, A.PROPERTIES, ";".join(properties))
    attr.set_string(transform, A.SELECTIONS, ";".join(selections))
    attr.set_string(transform, A.PROXIES, ";".join(proxies))
    attr.set_bool(transform, A.HAS_MASS, has_mass)
    if mass_values is not None:
        attr.set_string(transform, A.MASS_VALUES, float_values_string(mass_values))
    attr.set_bool(transform, A.HAS_SHARP_EDGES, has_sharp_edges)
    if sharp_edges:
        attr.set_string(transform, A.SHARP_EDGES, sharp_edges)
    attr.set_int(transform, A.UVSET_TAGG_COUNT, uv_set_count)
    if uv_set_taggs:
        attr.set_string(transform, A.UVSET_TAGGS, uv_set_taggs_string(uv_set_taggs))


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
    "MEMORY_LOCATOR_SCALE",
    "_leaf",
]
