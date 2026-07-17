"""Skin-weight export: a mesh's ``skinCluster`` -> one weighted named selection per bone.

DayZ stores rigging as named vertex selections (one per skeleton bone, matching the
``model.cfg`` bone names) where each selected vertex carries a 0..1 weight. This reads the
Maya skinCluster, enforces the engine's rules (<=4 influences per vertex, normalized), and
emits a ``SelectionTaggData`` per influencing joint — named after the joint's short name.
No-op when the mesh has no skinCluster (static LODs export unchanged).
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from a3ob.formats import p3d

_MAX_INFLUENCES = 4       # DayZ blends at most 4 bones per vertex
_WEIGHT_EPSILON = 1e-4    # ignore negligible weights (noise below Maya's prune threshold)


def _find_skincluster(mesh_path):
    """The skinCluster deforming ``mesh_path`` (an MDagPath to the mesh shape), or None."""
    history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    if not skins:
        return None
    selection = om.MSelectionList()
    selection.add(skins[0])
    return selection.getDependNode(0)


def _influence_names(skin_fn):
    """Short (bone) name for each influence, in the column order of getWeights()."""
    names = []
    for path in skin_fn.influenceObjects():
        leaf = path.partialPathName().split("|")[-1].split(":")[-1]
        names.append(leaf)
    return names


def _complete_vertex_component(mesh_path):
    comp_fn = om.MFnSingleIndexedComponent()
    component = comp_fn.create(om.MFn.kMeshVertComponent)
    comp_fn.setCompleteData(om.MFnMesh(mesh_path).numVertices)
    return component


def _add_skin_weight_taggs(mesh_path, vertex_source_indices, lod):
    """Emit one weighted ``SelectionTaggData`` per influencing bone from the mesh's
    skinCluster. Vertices are capped to the top ``_MAX_INFLUENCES`` bones and renormalized so
    the export always satisfies DayZ regardless of the Maya skinCluster's own limit."""
    skin_obj = _find_skincluster(mesh_path)
    if skin_obj is None:
        return 0

    skin_fn = oma.MFnSkinCluster(skin_obj)
    names = _influence_names(skin_fn)
    influence_count = len(names)
    if influence_count == 0:
        return 0

    weights, returned_count = skin_fn.getWeights(mesh_path, _complete_vertex_component(mesh_path))
    if returned_count != influence_count:  # defensive: getWeights column count must match
        influence_count = returned_count
    vertex_count = len(weights) // influence_count if influence_count else 0

    existing = {t.name for t in lod.taggs if isinstance(t.name, str)}
    # bone index -> list of (p3d_vertex_index, weight)
    bone_vertices = [[] for _ in range(influence_count)]

    for vertex in range(vertex_count):
        base = vertex * influence_count
        pairs = [(i, weights[base + i]) for i in range(influence_count) if weights[base + i] > _WEIGHT_EPSILON]
        if not pairs:
            continue
        pairs.sort(key=lambda pair: pair[1], reverse=True)
        pairs = pairs[:_MAX_INFLUENCES]
        total = sum(weight for _i, weight in pairs)
        if total <= 0.0:
            continue
        source_index = vertex_source_indices[vertex] if vertex < len(vertex_source_indices) else vertex
        if source_index >= len(lod.vertices):
            continue
        for influence, weight in pairs:
            bone_vertices[influence].append((source_index, weight / total))

    added = 0
    for influence in range(influence_count):
        rows = bone_vertices[influence]
        name = names[influence]
        if not rows or name in existing:
            continue
        tagg = p3d.Tagg()
        tagg.name = name
        data = p3d.SelectionTaggData()
        data.count_verts = len(lod.vertices)
        data.count_faces = len(lod.faces)
        data.vertex_weights = sorted(rows)
        tagg.data = data
        lod.taggs.append(tagg)
        existing.add(name)
        added += 1
    return added


__all__ = [
    "_add_skin_weight_taggs",
]
