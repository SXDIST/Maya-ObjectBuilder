"""Memory-LOD export: reconstruct single-vertex named selections from the Maya locators
parented under a face-less Memory LOD (one vertex + one SelectionTaggData per locator)."""

import maya.api.OpenMaya as om

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.formats import p3d


from a3ob.mayabridge.export.parse import *  # noqa: F401,F403



def _has_direct_locator_shape(dag_fn):
    for j in range(dag_fn.childCount()):
        if dag_fn.child(j).hasFn(om.MFn.kLocator):
            return True
    return False


def _collect_locators_from_memory_lod(transform_path, options, lod):
    lod_dag = om.MFnDagNode(transform_path)
    points = []  # (selection_name, vertex_index)

    def add_locator_vertex(loc_path, sel_name):
        if options.apply_transforms:
            bake = loc_path.inclusiveMatrix()
        else:
            bake = loc_path.inclusiveMatrix() * transform_path.inclusiveMatrix().inverse()
        world_pos = om.MPoint(0.0, 0.0, 0.0) * bake
        vertex_index = len(lod.vertices)
        lod.vertices.append(p3d.Vertex(maya_to_core_point(world_pos), 0))
        points.append((sel_name, vertex_index))

    for i in range(lod_dag.childCount()):
        child = lod_dag.child(i)
        if not child.hasFn(om.MFn.kTransform):
            continue
        if attr.get_bool_any(child, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
            continue
        child_fn = om.MFnDagNode(child)
        if _has_direct_locator_shape(child_fn):
            sel_name = attr.get_string(child, A.SELECTION_NAME) or child_fn.name()
            add_locator_vertex(child_fn.getPath(), sel_name)
        else:
            group_sel_name = attr.get_string(child, A.SELECTION_NAME) or child_fn.name()
            for j in range(child_fn.childCount()):
                grandchild = child_fn.child(j)
                if not grandchild.hasFn(om.MFn.kTransform):
                    continue
                if attr.get_bool_any(grandchild, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
                    continue
                grandchild_fn = om.MFnDagNode(grandchild)
                if not _has_direct_locator_shape(grandchild_fn):
                    continue
                add_locator_vertex(grandchild_fn.getPath(), group_sel_name)

    if not points:
        return False

    ordered_names = []
    selection_vertices = {}
    for sel_name, vertex_index in points:
        if sel_name not in selection_vertices:
            ordered_names.append(sel_name)
            selection_vertices[sel_name] = []
        selection_vertices[sel_name].append(vertex_index)

    total_verts = len(lod.vertices)
    for name in ordered_names:
        tagg = p3d.Tagg()
        tagg.name = name
        data = p3d.SelectionTaggData()
        data.count_verts = total_verts
        data.count_faces = 0
        for idx in selection_vertices[name]:
            data.vertex_weights.append((idx, 1.0))
        tagg.data = data
        lod.taggs.append(tagg)
    return True


# =============================================================================
# per-LOD export
# =============================================================================


__all__ = [
    "_has_direct_locator_shape",
    "_collect_locators_from_memory_lod",
]
