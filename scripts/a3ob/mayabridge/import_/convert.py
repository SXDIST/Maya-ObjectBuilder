"""P3D MLOD -> Maya DAG/mesh conversion (OpenMaya 2.0).

Port of ``src/maya/MayaMeshImport.cpp``. Builds a root transform named after the file,
groups LODs by category, and for each LOD creates a mesh (shape directly under the LOD
transform), applies UVs/custom normals, materials, selection/flag sets, proxy
placeholders, Memory-LOD locators and the ``a3ob*`` round-trip metadata.

Coordinate convention: P3D (Z-up) -> Maya (Y-up) point ``(x, y, z) -> (x, z, -y)``.
"""

import os
import re

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A


NULL = om.MObject.kNullObj


_PROXY_PARSE_RE = re.compile(r"^proxy:(.*)\.(\d+)$")


_LOD_BASE_NAMES = {
    0: "Resolution", 1: "View - Gunner", 2: "View - Pilot", 3: "View - Cargo",
    4: "Shadow Volume", 5: "Edit", 6: "Geometry", 7: "Geometry Buoyancy",
    8: "Geometry PhysX", 9: "Memory", 10: "Land Contact", 11: "Roadway",
    12: "Paths", 13: "Hit-points", 14: "View Geometry", 15: "Fire Geometry",
    16: "View - Cargo Geometry", 17: "View - Cargo Fire Geometry", 18: "View - Commander",
    19: "View - Commander Geometry", 20: "View - Commander Fire Geometry",
    21: "View - Pilot Geometry", 22: "View - Pilot Fire Geometry",
    23: "View - Gunner Geometry", 24: "View - Gunner Fire Geometry", 25: "Sub Parts",
    26: "Shadow Volume - Cargo View", 27: "Shadow Volume - Pilot View",
    28: "Shadow Volume - Gunner View", 29: "Wreckage", 30: "Underground",
    31: "Groundlayer", 32: "Navigation",
}


_LOD_GROUPS = {
    0: "visuals", 1: "visuals", 2: "visuals", 3: "visuals", 18: "visuals",
    4: "shadows", 26: "shadows", 27: "shadows", 28: "shadows",
    6: "geometries", 7: "geometries", 8: "geometries", 14: "geometries",
    15: "geometries", 16: "geometries", 17: "geometries", 19: "geometries",
    20: "geometries", 21: "geometries", 22: "geometries", 23: "geometries",
    24: "geometries", 30: "geometries",
    9: "point_clouds", 10: "point_clouds", 13: "point_clouds",
}


_RESOLUTION_LODS = {0, 3, 4, 5, 16, 26}


# =============================================================================
# naming / serialization helpers
# =============================================================================


def core_to_maya_point(vec3):
    return om.MPoint(vec3.x, vec3.z, -vec3.y)


def core_to_maya_vector(vec3):
    return om.MVector(vec3.x, vec3.z, -vec3.y)


_ILLEGAL_NAME_RE = re.compile(r"[^A-Za-z0-9_]")


def sanitized_name(value):
    # Used only for Maya node names (never for P3D selection names, which come from the
    # TAGG directly). The C++ replaced only ". -:/\\" and relied on Maya to scrub the
    # rest; Maya raises on illegal names during File > Import, so scrub everything not
    # in [A-Za-z0-9_]. Node names are not part of the P3D export contract.
    if not value:
        return "P3D"
    return _ILLEGAL_NAME_RE.sub("_", value)


def lod_base_name(lod):
    return _LOD_BASE_NAMES.get(lod, "Unknown")


def lod_has_resolution(lod):
    return lod in _RESOLUTION_LODS


def lod_name(resolution):
    name = lod_base_name(resolution.lod)
    if lod_has_resolution(resolution.lod):
        name += " %d" % resolution.resolution
    return name


def lod_group_name(lod):
    return _LOD_GROUPS.get(lod, "misc")


def selection_set_name(selection_name):
    return "a3ob_SEL_" + sanitized_name(selection_name)


def proxy_transform_name(transform_name, proxy_path, proxy_index):
    return "%s_PROXY_%s_%d" % (transform_name, sanitized_name(proxy_path), proxy_index)


def material_node_name(texture, material):
    if not texture and not material:
        return "a3ob_MAT_no_material"
    return "a3ob_MAT_%s__%s" % (sanitized_name(texture), sanitized_name(material))


def flag_set_name(component_type, flag):
    return "a3ob_%sFLAG_%d" % (component_type, flag)


def _num(value):
    # Mirror C++ ostream default formatting: drop the ".0" from whole floats.
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def float_values_string(values):
    return ";".join(_num(v) for v in values)


def vertex_values_string(vertices):
    return ";".join("%s,%s,%s,%d" % (_num(v.position.x), _num(v.position.y), _num(v.position.z), v.flag) for v in vertices)


def index_values_string(values):
    return ";".join(str(v) for v in values)


def sharp_edges_string(edges_data):
    return ";".join("%d,%d" % (a, b) for a, b in edges_data.edges)


def uv_set_taggs_string(taggs):
    parts = []
    for tagg in taggs:
        piece = [str(tagg.id)]
        for uv in tagg.uvs:
            piece.append(_num(uv.u))
            piece.append(_num(uv.v))
        parts.append(",".join(piece))
    return "|".join(parts)


def parse_proxy_name(name):
    match = _PROXY_PARSE_RE.match(name)
    if not match:
        return None
    return match.group(1), int(match.group(2))


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
    for face in lod.faces:
        uv_counts.append(len(face.uvs))
        for uv in face.uvs:
            u_values.append(uv.u)
            v_values.append(uv.v)
            uv_ids.append(len(uv_ids))
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
    "NULL",
    "_PROXY_PARSE_RE",
    "_LOD_BASE_NAMES",
    "_LOD_GROUPS",
    "_RESOLUTION_LODS",
    "core_to_maya_point",
    "core_to_maya_vector",
    "_ILLEGAL_NAME_RE",
    "sanitized_name",
    "lod_base_name",
    "lod_has_resolution",
    "lod_name",
    "lod_group_name",
    "selection_set_name",
    "proxy_transform_name",
    "material_node_name",
    "flag_set_name",
    "_num",
    "float_values_string",
    "vertex_values_string",
    "index_values_string",
    "sharp_edges_string",
    "uv_set_taggs_string",
    "parse_proxy_name",
    "_name_to_object",
    "_create_transform",
    "set_lod_metadata",
    "apply_uvs",
    "apply_normals",
    "MEMORY_LOCATOR_SCALE",
    "_leaf",
]
