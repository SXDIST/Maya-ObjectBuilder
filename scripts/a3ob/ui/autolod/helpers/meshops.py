"""meshops."""

from maya import cmds
from maya import mel



from a3ob.ui.autolod.helpers.settings import *  # noqa: F401,F403


def _selected_source_transform():
    for item in cmds.ls(selection=True, long=True) or []:
        node = item.split(".", 1)[0]
        if cmds.objectType(node, isType="mesh"):
            parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
            if parents:
                return parents[0]
        shapes = cmds.listRelatives(node, shapes=True, type="mesh", fullPath=True) or []
        if shapes:
            return node
        descendants = cmds.listRelatives(node, allDescendents=True, type="mesh", fullPath=True) or []
        if descendants:
            parents = cmds.listRelatives(descendants[0], parent=True, fullPath=True) or []
            if parents:
                return parents[0]
    return ""


def _short_name(node):
    return node.split("|")[-1].split(":")[-1]


def _canonical_group_name(name):
    return name.lower().replace(" ", "_")


def _group(name):
    name = _canonical_group_name(name)
    matches = [node for node in cmds.ls(type="transform", long=True) or [] if _short_name(node).lower() == name]
    if not matches:
        return cmds.group(empty=True, name=name)

    root_matches = [node for node in matches if not (cmds.listRelatives(node, parent=True, fullPath=True) or [])]
    exact = [node for node in root_matches or matches if _short_name(node) == name]
    keep = sorted(exact or root_matches or matches, key=lambda item: (item.count("|"), item))[0]
    for duplicate in list(matches):
        if duplicate == keep or not cmds.objExists(duplicate):
            continue
        children = cmds.listRelatives(duplicate, children=True, fullPath=True) or []
        for child in children:
            cmds.parent(child, keep)
        if not (cmds.listRelatives(duplicate, children=True, fullPath=True) or []):
            cmds.delete(duplicate)
    if _short_name(keep) != name:
        renamed = cmds.rename(keep, name)
        keep = (cmds.ls(renamed, long=True) or [renamed])[0]
    return keep


def _mesh_shapes(transform):
    return cmds.listRelatives(transform, shapes=True, type="mesh", fullPath=True) or []


def _face_count(transform):
    return sum(cmds.polyEvaluate(shape, face=True) for shape in _mesh_shapes(transform))


def _poly_info(transform, **kwargs):
    try:
        return cmds.polyInfo(transform, **kwargs) or []
    except RuntimeError:
        return []


def _has_reduce_blockers(transform):
    blockers = []
    if _poly_info(transform, nonManifoldVertices=True):
        blockers.append("nonmanifold vertices")
    if _poly_info(transform, nonManifoldEdges=True):
        blockers.append("nonmanifold edges")
    if _poly_info(transform, laminaFaces=True):
        blockers.append("lamina faces")
    return blockers


def _cleanup_for_reduce(transform):
    before = _has_reduce_blockers(transform)
    cmds.select(transform, replace=True)
    try:
        mel.eval('string $cleanupArgs[] = {"0","1","1","0","0","0","0","0","0","1e-05","0","1e-05","0","1e-05","0","1","0","0"}; polyCleanupArgList 4 $cleanupArgs;')
    except RuntimeError as exc:
        cmds.warning("Auto LOD cleanup failed on {0}: {1}".format(transform, exc))
    remaining_vertices = _poly_info(transform, nonManifoldVertices=True)
    if remaining_vertices:
        try:
            cmds.select(remaining_vertices, replace=True)
            cmds.polySplitVertex(constructionHistory=False)
        except RuntimeError as exc:
            cmds.warning("Auto LOD nonmanifold vertex split failed on {0}: {1}".format(transform, exc))
    try:
        cmds.delete(transform, constructionHistory=True)
    except RuntimeError:
        pass
    after = _has_reduce_blockers(transform)
    if before and after:
        cmds.warning("Auto LOD cleanup left blockers on {0}: {1}".format(transform, ", ".join(after)))
    return before, after


def _parent(node, parent):
    if not node or not parent:
        return
    current = cmds.listRelatives(node, parent=True, fullPath=True) or []
    parent_path = (cmds.ls(parent, long=True) or [parent])[0]
    if current and current[0] == parent_path:
        return
    cmds.parent(node, parent)


def _mark_lod(transform, lod_type, resolution=0):
    cmds.select(transform, replace=True)
    result = cmds.a3obCreateLOD(lodType=lod_type, resolution=resolution, name=transform)
    if isinstance(result, (list, tuple)):
        result = result[0] if result else None
    return result or transform


def _mark_technical_set(node):
    if not node or not cmds.objExists(node):
        return
    if not cmds.attributeQuery("a3obTechnicalSet", node=node, exists=True):
        cmds.addAttr(node, longName="a3obTechnicalSet", attributeType="bool")
    cmds.setAttr(node + ".a3obTechnicalSet", True)
    if cmds.attributeQuery("hiddenInOutliner", node=node, exists=True):
        cmds.setAttr(node + ".hiddenInOutliner", True)


def _set_named_properties(lod, properties):
    if not properties:
        return
    cmds.select(lod, replace=True)
    for name, value in properties:
        # The a3obNamedProperty -set flag takes a single "key=value" string
        # (OpenMaya 2.0 flags accept only one argument; long alias is -setproperty).
        cmds.a3obNamedProperty(s="%s=%s" % (name, value))


def _source_bbox(source):
    bbox = cmds.exactWorldBoundingBox(source)
    return {
        "min": (bbox[0], bbox[1], bbox[2]),
        "max": (bbox[3], bbox[4], bbox[5]),
        "center": ((bbox[0] + bbox[3]) * 0.5, (bbox[1] + bbox[4]) * 0.5, (bbox[2] + bbox[5]) * 0.5),
        "size": (max(bbox[3] - bbox[0], 0.001), max(bbox[4] - bbox[1], 0.001), max(bbox[5] - bbox[2], 0.001)),
    }


def _create_bbox_lod(source, name, lod_type, parent, named_properties=(), find_components=False):
    bbox = _source_bbox(source)
    cube = cmds.polyCube(name=name, width=bbox["size"][0], height=bbox["size"][1], depth=bbox["size"][2])[0]
    cmds.xform(cube, worldSpace=True, translation=bbox["center"])
    _mark_lod(cube, lod_type, 0)
    _set_named_properties(cube, named_properties)
    _parent(cube, parent)
    if find_components:
        try:
            cmds.select(cube, replace=True)
            cmds.a3obFindComponents()
        except RuntimeError as exc:
            cmds.warning(str(exc))
    return cube


def _extract_triangles(transform):
    """Return (points Nx3 float array, triangle-index Mx3 array) for the transform's
    first mesh, or ``None`` when unavailable (no mesh / numpy missing)."""
    try:
        import numpy as np
        import maya.api.OpenMaya as om
    except Exception:
        return None
    shapes = _mesh_shapes(transform)
    if not shapes:
        return None
    sel = om.MSelectionList()
    sel.add(shapes[0])
    fn = om.MFnMesh(sel.getDagPath(0))
    pts = np.array([[p.x, p.y, p.z] for p in fn.getPoints(om.MSpace.kObject)])
    _counts, tri_verts = fn.getTriangles()
    faces = np.asarray(tri_verts, dtype=np.int64).reshape(-1, 3)
    return pts, faces


def _qem_chain_for_ratios(source, ratios):
    """Decimate ``source`` once and snapshot at every ratio via the Blender-style QEM
    collapse (``a3ob.ui.autolod.qem``). Returns ``{ratio: (points, faces)}`` or ``None``
    if QEM is unavailable (numpy missing / headless) so callers fall back to polyReduce."""
    ratios = [r for r in ratios if r < 1.0]
    if not ratios:
        return {}
    data = _extract_triangles(source)
    if data is None:
        return None
    try:
        from a3ob.ui.autolod import qem
    except Exception:
        return None
    points, faces = data
    base = len(faces)
    if base <= 4:
        return None
    ratio_target = {r: max(4, int(round(base * r))) for r in ratios}
    try:
        snaps = qem.decimate_chain(points, faces, ratio_target.values())
    except Exception as exc:
        cmds.warning("Auto LOD QEM decimation failed: {0} — using polyReduce".format(exc))
        return None
    return {r: snaps[t] for r, t in ratio_target.items() if t in snaps}


def _triangle_shading_groups(shape):
    """(shading-group names, per-triangle group-index list) for a mesh shape, so the
    decimated LOD can be re-assigned the same materials face-by-face. (None, None) when
    unavailable."""
    try:
        import maya.api.OpenMaya as om
    except Exception:
        return None, None
    sel = om.MSelectionList()
    sel.add(shape)
    dag = sel.getDagPath(0)
    fn = om.MFnMesh(dag)
    counts, _tv = fn.getTriangles()
    try:
        shaders, poly_shader = fn.getConnectedShaders(dag.instanceNumber())
    except Exception:
        return None, None
    sg_names = [om.MFnDependencyNode(s).name() for s in shaders]
    tri_sg = []
    for polygon, count in enumerate(counts):
        idx = poly_shader[polygon] if polygon < len(poly_shader) else -1
        tri_sg.extend([idx] * count)
    return sg_names, tri_sg


def _assign_qem_materials(new_shape, orig_faces, sg_names, tri_sg):
    """Re-assign the decimated faces to the source's shading groups using each survivor's
    original face index. Falls back to initialShadingGroup so a rebuilt mesh is never left
    materialless (which shows as a green 'no shader' mesh and breaks material export)."""
    from collections import defaultdict
    groups = defaultdict(list)
    if sg_names and tri_sg is not None:
        for new_index, orig in enumerate(orig_faces):
            idx = tri_sg[orig] if 0 <= orig < len(tri_sg) else -1
            if 0 <= idx < len(sg_names):
                groups[sg_names[idx]].append(new_index)
    assigned = False
    for sg, face_ids in groups.items():
        if not cmds.objExists(sg):
            continue
        try:
            cmds.sets(["{0}.f[{1}]".format(new_shape, i) for i in face_ids], forceElement=sg)
            assigned = True
        except Exception:
            pass
    if not assigned:
        try:
            cmds.sets(new_shape, forceElement="initialShadingGroup")
        except Exception:
            pass


def _apply_qem_snapshot(transform, uv_source, snapshot):
    """Replace ``transform``'s mesh with the decimated ``snapshot`` (points, faces,
    orig_face_index), re-assign the source materials face-by-face, and re-project UVs from
    the full-res ``uv_source``. Returns False on any failure so the caller can fall back to
    polyReduce."""
    try:
        import maya.api.OpenMaya as om
    except Exception:
        return False
    points, faces, orig_faces = snapshot
    if len(faces) <= 0:
        return False
    old_shapes = _mesh_shapes(transform)
    sg_names, tri_sg = (_triangle_shading_groups(old_shapes[0]) if old_shapes else (None, None))
    try:
        tsel = om.MSelectionList()
        tsel.add(transform)
        transform_obj = tsel.getDependNode(0)
        for shape in old_shapes:
            cmds.delete(shape)
        mesh_fn = om.MFnMesh()
        mpoints = [om.MPoint(float(p[0]), float(p[1]), float(p[2])) for p in points]
        connects = [int(i) for f in faces for i in f]
        mesh_fn.create(mpoints, [3] * len(faces), connects, parent=transform_obj)
    except Exception as exc:
        cmds.warning("Auto LOD QEM rebuild failed on {0}: {1}".format(transform, exc))
        return False
    new_shapes = _mesh_shapes(transform)
    if new_shapes:
        _assign_qem_materials(new_shapes[0], orig_faces, sg_names, tri_sg)
    # QEM decimates geometry only; project the UVs back from the full-res source so
    # textured LODs keep their mapping (Blender's collapse carries UVs the same way).
    if uv_source and cmds.objExists(uv_source):
        try:
            cmds.transferAttributes(uv_source, transform, transferUVs=2, sampleSpace=0, searchMethod=3)
            cmds.delete(transform, constructionHistory=True)
        except RuntimeError as exc:
            cmds.warning("Auto LOD UV transfer failed on {0}: {1}".format(transform, exc))
    return True


def _reduce_mesh(transform, keep_ratio):
    before = _face_count(transform)
    reduction = max(0.0, min(100.0, (1.0 - keep_ratio) * 100.0))
    if reduction <= 0.0 or before <= 0:
        return before, before, True
    if _has_reduce_blockers(transform):
        _cleanup_for_reduce(transform)
    try:
        # Clean decimate: the mesh is already triangulated, so keepQuadsWeight is moot.
        # Protect only the open silhouette (keepBorder) and UV seams (keepMapBorder) so
        # LODs don't grow holes or tear textures; let everything else collapse uniformly
        # (hard/crease/colour/face-group constraints only made the reduction lumpy — the
        # 60-degree normal pass reconstructs shading afterwards anyway).
        cmds.polyReduce(transform, version=1, termination=0, percentage=reduction, keepQuadsWeight=0.0, keepBorder=True, keepMapBorder=True, keepColorBorder=False, keepFaceGroupBorder=False, keepHardEdge=False, keepCreaseEdge=False, keepBorderWeight=0.5, keepMapBorderWeight=0.5, cachingReduce=False, constructionHistory=False)
    except RuntimeError as exc:
        cmds.warning("Auto LOD polyReduce failed on {0}: {1}".format(transform, exc))
    after = _face_count(transform)
    if after >= before and before > 4:
        _cleanup_for_reduce(transform)
        try:
            cmds.polyReduce(transform, version=1, termination=0, percentage=reduction, keepQuadsWeight=0.0, keepBorder=False, keepMapBorder=False, keepColorBorder=False, keepFaceGroupBorder=False, keepHardEdge=False, keepCreaseEdge=False, cachingReduce=False, constructionHistory=False)
            after = _face_count(transform)
        except RuntimeError as exc:
            cmds.warning("Auto LOD fallback polyReduce failed on {0}: {1}".format(transform, exc))
    reduced_ok = before <= 4 or after < before
    if not reduced_ok:
        cmds.warning("Auto LOD polyReduce did not reduce {0}: faces {1} -> {2}".format(transform, before, after))
    return before, after, reduced_ok


def _triangulate(transform):
    try:
        cmds.polyTriangulate(transform, constructionHistory=False)
    except RuntimeError as exc:
        cmds.warning("Auto LOD triangulate failed on {0}: {1}".format(transform, exc))


def _quadrangulate(transform):
    # QUADS mode: merge the decimated triangles back into quads so the LOD stays
    # quad-dominant (P3D supports quad faces; that is the whole point of QUADS mode).
    try:
        cmds.polyQuad(transform, angle=30, constructionHistory=False)
    except RuntimeError as exc:
        cmds.warning("Auto LOD quadrangulate failed on {0}: {1}".format(transform, exc))


def _apply_weighted_normals(transform):
    try:
        cmds.polySetToFaceNormal(transform, setUserNormal=True)
        cmds.polySoftEdge(transform, angle=60, constructionHistory=False)
        cmds.polyNormalPerVertex(transform, freezeNormal=False)
    except RuntimeError as exc:
        cmds.warning("Auto LOD normal pass failed on {0}: {1}".format(transform, exc))


def _propagate_named_selections(source, target, full_resolution=True):
    """Copy named selections from source to target mesh.

    For object-level sets: adds target to any set containing source.
    For component-level sets: only adds equivalent components if full_resolution=True.
    """
    source_short = _short_name(source)
    sets_with_selections = []
    for obj_set in cmds.ls(type="objectSet") or []:
        if not cmds.attributeQuery("a3obSelectionName", node=obj_set, exists=True):
            continue
        set_members = cmds.sets(obj_set, query=True) or []
        sets_with_selections.append((obj_set, set_members))

    for obj_set, set_members in sets_with_selections:
        has_source_object = source_short in set_members
        has_source_components = any(isinstance(m, str) and m.startswith(source_short + ".") for m in set_members)

        if has_source_object:
            cmds.sets(target, addElement=obj_set)
        elif has_source_components and full_resolution:
            for member in set_members:
                if isinstance(member, str) and member.startswith(source_short + "."):
                    component = member[len(source_short):]
                    cmds.sets(target + component, addElement=obj_set)


def _create_memory_mesh(transform, points):
    import maya.api.OpenMaya as om

    selection = om.MSelectionList()
    selection.add(transform)
    parent = selection.getDependNode(0)
    vertices = []
    face_counts = []
    face_connects = []
    marker_size = 0.01
    for _, point in points:
        x, y, z = point
        start = len(vertices)
        vertices.extend([
            om.MPoint(x, y, z),
            om.MPoint(x + marker_size, y, z),
            om.MPoint(x, y + marker_size, z),
        ])
        face_counts.append(3)
        face_connects.extend([start, start + 1, start + 2])
    mesh_fn = om.MFnMesh()
    mesh_fn.create(vertices, face_counts, face_connects, parent=parent)
    mesh_fn.setName("MemoryShape")
    return mesh_fn.fullPathName()


def _create_memory_set(mesh_shape, index, name):
    member = "{0}.vtx[{1}]".format(mesh_shape, index * 3)
    cmds.select(member, replace=True)
    set_name = "a3ob_SEL_{0}".format(name)
    if cmds.objExists(set_name):
        cmds.delete(set_name)
    set_node = cmds.sets(member, name=set_name)
    if not cmds.attributeQuery("a3obSelectionName", node=set_node, exists=True):
        cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", name, type="string")
    _mark_technical_set(set_node)


__all__ = [
    "_selected_source_transform",
    "_short_name",
    "_canonical_group_name",
    "_group",
    "_mesh_shapes",
    "_face_count",
    "_poly_info",
    "_has_reduce_blockers",
    "_cleanup_for_reduce",
    "_parent",
    "_extract_triangles",
    "_qem_chain_for_ratios",
    "_triangle_shading_groups",
    "_assign_qem_materials",
    "_apply_qem_snapshot",
    "_mark_lod",
    "_mark_technical_set",
    "_set_named_properties",
    "_source_bbox",
    "_create_bbox_lod",
    "_reduce_mesh",
    "_triangulate",
    "_quadrangulate",
    "_apply_weighted_normals",
    "_propagate_named_selections",
    "_create_memory_mesh",
    "_create_memory_set",
]
