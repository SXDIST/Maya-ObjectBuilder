from maya import cmds
import maya.api.OpenMaya as om


from a3ob.mayabridge.autolod.helpers import *  # noqa: F401,F403

def _generate_resolution_lods(source, settings, visuals):
    start_lod = 0 if settings["first_lod"] == "LOD0" else 1
    ratios = reduction_ladder(settings["reduction"])
    generated = []

    # No snapshot duplicate here anymore. It used to exist because index 0 renamed
    # `source` into LOD1 (cmds.rename), destroying the original — every later index, and
    # the QEM read below, needed an immutable stand-in once that had happened. `source` is
    # never renamed or written to by this function now (every index duplicates from it),
    # so it stays pristine for the whole loop and can be read directly.
    #
    # Decimate with a faithful Garland-Heckbert QEM edge-collapse (a3ob.mayabridge.autolod.qem) —
    # the same algorithm as Blender's Decimate -> Collapse, giving the even, shape-
    # preserving triangles Maya's sliver-prone polyReduce cannot. One progressive pass
    # snapshots every LOD level at once; None means QEM is unavailable -> polyReduce.
    #
    # Esc during the collapse raises AutoLodCancelled out of here. That happens before any
    # LOD duplicate exists and before a single decimated mesh is written back, so there is
    # nothing this function owes to clean up — the scene keeps the geometry the user started
    # with. Deliberately not a fall-through to polyReduce: cancel means stop.
    qem_snaps = _qem_chain_for_ratios(source, ratios)

    for index, ratio in enumerate((1.0, *ratios)):
        resolution = start_lod + index
        name = "{0}{1}".format(settings["lod_prefix"], resolution)

        duplicate = cmds.duplicate(source, name=name, returnRootsOnly=True)[0]
        if index == 0:
            # LOD1 used to BE the source (cmds.rename), which is why it needed nothing here.
            # It is a copy now, so the two things the rename gave it for free have to be
            # given explicitly: the source's selection sets, and its rig.
            _propagate_named_selections(source, duplicate, full_resolution=True)
            _rebind_like(source, duplicate)
        if ratio < 1.0:
            applied = False
            if qem_snaps is not None and ratio in qem_snaps:
                applied = _apply_qem_snapshot(duplicate, source, qem_snaps[ratio])
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
        # "quads" output keeps quad-dominant LODs; "triangles" triangulates.
        if settings["output"] == "quads":
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

    return generated


def _rebind_like(source, target):
    """Bind ``target`` to ``source``'s influences and copy the weight array verbatim.

    ``target`` is a duplicate of ``source``, so vertex order is identical and index i maps
    to index i — no surface association is needed, and none may be used. Measured on a real
    garment (6892 verts, 25 influences): writing the array through
    ``MFnSkinCluster.setWeights`` deviates by 0.0, while ``cmds.copySkinWeights`` with
    closestPoint/oneToOne deviates by 0.1027 on that same identical geometry, putting five
    vertices past the 1/254 step the P3D format can even encode. Coincident points make the
    association pick arbitrarily; there is nothing to tune."""
    import maya.api.OpenMayaAnim as oma

    source_shape = cmds.listRelatives(source, shapes=True, noIntermediate=True, fullPath=True)
    if not source_shape:
        return None
    source_skin = cmds.ls(cmds.listHistory(source_shape[0], pruneDagObjects=True) or [],
                          type="skinCluster")
    if not source_skin:
        return None  # unrigged source: nothing to carry across

    influences = cmds.skinCluster(source_skin[0], query=True, influence=True) or []
    if not influences:
        return None

    def _fn_and_component(mesh):
        shape = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True)[0]
        skins = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
        selection = om.MSelectionList()
        selection.add(skins[0])
        fn = oma.MFnSkinCluster(selection.getDependNode(0))
        paths = om.MSelectionList()
        paths.add(shape)
        component = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
        om.MFnSingleIndexedComponent(component).setCompleteData(
            cmds.polyEvaluate(mesh, vertex=True))
        return fn, paths.getDagPath(0), component

    source_fn, source_path, source_component = _fn_and_component(source)
    weights, influence_count = source_fn.getWeights(source_path, source_component)

    cmds.skinCluster(influences, target, toSelectedBones=True, bindMethod=0,
                     skinMethod=0, normalizeWeights=1)
    target_fn, target_path, target_component = _fn_and_component(target)
    target_fn.setWeights(target_path, target_component,
                         om.MIntArray(range(influence_count)), weights, False)
    return target


def _generate_geometry_lod(source, settings, geometries):
    # No named properties. `1.000e+13` is the Geometry LOD's RESOLUTION SIGNATURE — the
    # float in the LOD's resolution field that encodes its type, written by _mark_lod. The
    # Blender add-on this was ported from mentions the string once, as a key in its
    # signature -> LOD type table; it is not a property, and porting it into one put a junk
    # "lod" row in Object Builder's Named Properties on every generated Geometry LOD. Same
    # mistake as the autocenter=0 artifact above.
    if settings["geometry_type"] == "NONE":
        node = cmds.group(empty=True, name=settings["geometry_name"])
        _mark_lod(node, 6, 0)
        _parent(node, geometries)
        return node
    return _create_bbox_lod(source, settings["geometry_name"], 6, geometries, (), True)


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
