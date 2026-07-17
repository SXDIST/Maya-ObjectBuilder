"""names."""

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


_TEXTURE_SUFFIX_RE = re.compile(r"_(co|ca|nohq|smdi|as|mca|dt|sm|mc|detail)$", re.IGNORECASE)


def _material_name_stem(path):
    # Just the file name without folders or extension — the node name is not part of the
    # P3D contract (the full path is kept on a3obTexture/a3obMaterial), so keep it readable.
    if not path:
        return ""
    base = os.path.splitext(os.path.basename(path.replace("\\", "/")))[0]
    return sanitized_name(base) if base else ""


def material_node_name(texture, material):
    # Prefer the .rvmat base (the real material name); else the texture name with its
    # _co/_ca/_nohq channel suffix stripped. No verbose prefix — the a3ob* attributes
    # identify Object Builder materials, and name clashes get auto-numbered by Maya.
    material_stem = _material_name_stem(material)
    if material_stem:
        return material_stem
    texture_stem = _material_name_stem(texture)
    if texture_stem:
        return _TEXTURE_SUFFIX_RE.sub("", texture_stem) or texture_stem
    return "no_material"


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
]
