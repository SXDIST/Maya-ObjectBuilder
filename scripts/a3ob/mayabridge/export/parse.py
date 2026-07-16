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


__all__ = [
    "maya_to_core_point",
    "maya_to_core_vector",
    "_split_semicolon",
    "_split_float_values",
    "_split_index_values",
    "_split_vertex_values",
    "_split_sharp_edges",
    "_split_uvset_taggs",
    "_split_properties",
    "_resolve_lod_path",
    "_find_first_mesh_path",
    "_strip_drive",
    "_mesh_material_pairs",
    "_parse_component_range",
    "_read_set_components",
    "_derive_faces_from_vertices",
]
