from maya import cmds
from maya import mel


from a3ob.ui.autolod.helpers import *  # noqa: F401,F403

def _generate_resolution_lods(source, settings, visuals):
    start_lod = 0 if settings["first_lod"] == "LOD0" else 1
    ratios = RESOLUTION_PRESETS.get(settings["preset"], RESOLUTION_PRESETS["QUADS"])
    generated = []
    source_snapshot = cmds.duplicate(source, returnRootsOnly=True)[0]

    # Decimate with a faithful Garland-Heckbert QEM edge-collapse (a3ob.ui.autolod.qem) —
    # the same algorithm as Blender's Decimate -> Collapse, giving the even, shape-
    # preserving triangles Maya's sliver-prone polyReduce cannot. One progressive pass
    # snapshots every LOD level at once; None means QEM is unavailable -> polyReduce.
    qem_snaps = _qem_chain_for_ratios(source_snapshot, ratios)

    for index, ratio in enumerate((1.0, *ratios)):
        resolution = start_lod + index
        name = "{0}{1}".format(settings["lod_prefix"], resolution)

        if index == 0:
            # Keep the rename result as a short name (like the duplicate branch below).
            # Converting to a full path here left a stale path after _parent() reparented
            # the node, so the full-resolution LOD was silently dropped from the returned
            # list (and the post-generation selection) even though it existed in the scene.
            duplicate = cmds.rename(source, name)
        else:
            duplicate = cmds.duplicate(source_snapshot, name=name, returnRootsOnly=True)[0]
        if ratio < 1.0:
            applied = False
            if qem_snaps is not None and ratio in qem_snaps:
                applied = _apply_qem_snapshot(duplicate, source_snapshot, qem_snaps[ratio])
            if not applied:
                # polyReduce fallback (QEM unavailable or failed on this mesh).
                try:
                    cmds.polyMergeVertex(duplicate, d=0.0001, constructionHistory=False)
                except RuntimeError:
                    pass
                before, after, reduced_ok = _reduce_mesh(duplicate, ratio)
                if not reduced_ok:
                    cmds.delete(duplicate)
                    raise RuntimeError("Auto LOD failed to reduce {0} at ratio {1}: faces {2} -> {3}. Clean or rebuild nonmanifold geometry before generating LODs.".format(name, ratio, before, after))
        # QUADS mode keeps quad-dominant LODs (its whole purpose); TRIS/CUSTOM triangulate.
        if settings["preset"] == "QUADS":
            _quadrangulate(duplicate)
        else:
            _triangulate(duplicate)
        _apply_weighted_normals(duplicate)
        _mark_lod(duplicate, 0, resolution)
        # Resolution (visual) LODs get no auto named properties: Blender's Auto LOD adds
        # none either (autocenter/lodnoshadow there are only autocomplete suggestions).
        # autocenter=0 in particular was a spurious Blender-port artifact — Object Builder
        # leaves autocenter at its default, so marking every resolution LOD with it is wrong.
        if index > 0 and generated:
            _propagate_named_selections(generated[0], duplicate, full_resolution=False)
        _parent(duplicate, visuals)
        duplicate = (cmds.ls(duplicate, long=True) or [duplicate])[0]
        generated.append(duplicate)

    cmds.delete(source_snapshot)
    return generated


def _generate_geometry_lod(source, settings, geometries):
    if settings["geometry_type"] == "NONE":
        node = cmds.group(empty=True, name=settings["geometry_name"])
        _mark_lod(node, 6, 0)
        _set_named_properties(node, (("lod", "1.000e+13"),))
        _parent(node, geometries)
        return node
    return _create_bbox_lod(source, settings["geometry_name"], 6, geometries, (("lod", "1.000e+13"),), True)


def _generate_view_geometry_lod(source, settings, geometries):
    return _create_bbox_lod(source, settings["view_geometry_name"], 14, geometries, (), True)


def _generate_fire_geometry_lod(source, settings, geometries):
    fire = _create_bbox_lod(source, "Fire Geometry", 15, geometries, (), False)
    _triangulate(fire)
    if int(settings.get("fire_quality", 2)) < 10:
        _reduce_mesh(fire, max(0.1, int(settings.get("fire_quality", 2)) / 10.0))
    try:
        cmds.select(fire, replace=True)
        cmds.a3obFindComponents()
    except RuntimeError as exc:
        cmds.warning(str(exc))
    return fire


def _generate_memory_lod(source, settings, point_clouds):
    bbox = _source_bbox(source)
    points = []
    memory = settings.get("memory_points", {})
    max_dimension = max(bbox["size"])
    if memory.get("invview", True):
        points.append(("invview", (bbox["center"][0], bbox["max"][1] + max_dimension * 0.5 + 250.0, bbox["center"][2])))
    if memory.get("bounding_box", True):
        points.append(("boundingbox_min", bbox["min"]))
        points.append(("boundingbox_max", bbox["max"]))
    if memory.get("radius", True):
        points.append(("ce_radius", bbox["max"]))
    if memory.get("center", True):
        points.append(("ce_center", bbox["center"]))
    if not points:
        cmds.warning("Auto LOD Memory has no enabled points")
        return ""
    transform = cmds.createNode("transform", name="Memory")
    mesh_shape = _create_memory_mesh(transform, points)
    transform = _mark_lod(transform, 9, 0)
    _parent(transform, point_clouds)
    shapes = cmds.listRelatives(transform, shapes=True, fullPath=True) or []
    mesh_shape = shapes[0] if shapes else mesh_shape
    for index, (name, _) in enumerate(points):
        _create_memory_set(mesh_shape, index, name)
    return transform


__all__ = [
    "_generate_resolution_lods",
    "_generate_geometry_lod",
    "_generate_view_geometry_lod",
    "_generate_fire_geometry_lod",
    "_generate_memory_lod",
]
