"""Transfer DayZ skin weights from the reference body onto a garment.

Binding a garment from scratch needs heavy cleanup: joints crease wrongly, pouches smear
across three bones, single vertices fly off to unrelated limbs. The DayZ body already carries
correct weights for the whole skeleton — twist and extra bones included — so the reliable
answer is to copy from it rather than recompute. A garment that follows the body's shape then
deforms with it, which is also what stops it clipping through in game.

Geometry that stands *away* from the body is the one case where copying by closest point
lies: the nearest body point to a thigh pouch is the thigh, but the pouch is a rigid object
and must move as one piece. Such shells are detected by distance and get a single averaged
weight set applied to all their vertices.

The reference mesh is never modified.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import skinweights as sw

MAX_INFLUENCES = sw.MAX_INFLUENCES
MIN_WEIGHT = sw.MIN_ENCODABLE_WEIGHT

# Scene units, measured on a real DayZ character rather than guessed. Median gap from the
# body, per garment: boots 0.009, trousers 0.019, jacket 0.024, helmet 0.025 — against a
# backpack at 0.102. Fitted cloth clusters below 0.03 but reaches 0.06 at the 90th percentile,
# so a threshold of 0.03 (the first guess) wrongly classified parts of the jacket as detached.
# 0.06 sits well above every fitted garment and well below the backpack.
DEFAULT_FAR_DISTANCE = 0.06


def skin_cluster_of(mesh_path):
    """The skinCluster deforming a mesh shape, as a node name, or ''."""
    history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    return skins[0] if skins else ""


def _shape_of(node_name):
    selection = om.MSelectionList()
    selection.add(node_name)
    dag_path = selection.getDagPath(0)
    if not dag_path.node().hasFn(om.MFn.kMesh):
        try:
            dag_path.extendToShape()
        except Exception:  # noqa: BLE001 - no shape under it
            return None
    return dag_path if dag_path.node().hasFn(om.MFn.kMesh) else None


def selected_mesh_shapes():
    """Mesh shapes in the current selection, de-duplicated, in selection order."""
    shapes = []
    seen = set()
    for name in cmds.ls(selection=True, long=True) or []:
        dag_path = _shape_of(name.split(".", 1)[0])
        if dag_path is None:
            continue
        key = dag_path.fullPathName()
        if key not in seen:
            seen.add(key)
            shapes.append(dag_path)
    return shapes


def find_reference(targets, explicit=""):
    """The skinned mesh to copy from: explicit if given, else the best candidate not selected.

    'Best' is the most influences — the DayZ body carries the whole skeleton (111 joints on the
    stock rig) and beats any garment, so this picks the body without the user naming it."""
    target_keys = {path.fullPathName() for path in targets}

    if explicit:
        dag_path = _shape_of(explicit)
        if dag_path is None:
            raise ValueError("reference '%s' is not a mesh" % explicit)
        if not skin_cluster_of(dag_path):
            raise ValueError("reference '%s' has no skinCluster" % explicit)
        return dag_path

    best = None
    best_count = -1
    for skin in cmds.ls(type="skinCluster") or []:
        for geometry in cmds.skinCluster(skin, query=True, geometry=True) or []:
            dag_path = _shape_of(geometry)
            if dag_path is None or dag_path.fullPathName() in target_keys:
                continue
            count = len(cmds.skinCluster(skin, query=True, influence=True) or [])
            if count > best_count:
                best, best_count = dag_path, count
    if best is None:
        raise ValueError("no skinned reference mesh found (is the DayZ body in the scene?)")
    return best


def ensure_reference(targets, explicit="", kind="male_body"):
    """The reference mesh to copy from, importing the saved asset if the scene has none.

    Returns ``(mesh_path, imported_nodes)``. A reference already present is used as-is
    and never touched, in which case ``imported_nodes`` is empty.

    What is imported STAYS in the scene, body and skeleton both. Removing it again is
    tempting — the scene would stay pristine — but the saved asset carries its own
    skeleton, the garment gets bound to exactly those joints, and deleting them takes
    the skinCluster (and therefore every transferred weight) with it. Keeping them is
    also what a rigger needs: editing weights, painting them and ``a3obTestPose`` all
    require the joints to be there. The convenience delivered here is not having to add
    the body by hand, not a scene that cleans itself up."""
    from a3ob.mayabridge import references

    try:
        return find_reference(targets, explicit), []
    except ValueError:
        pass  # nothing suitable in the scene — add the saved asset below

    if not references.reference_path(kind):
        raise ValueError(
            "no skinned reference in the scene and no %s reference saved — add the body, or "
            "save one with a3obReference" % references.KINDS[kind][1])

    imported = references.add_reference(kind)
    return find_reference(targets, explicit), imported


def _bounding_box(mesh_path):
    """World-space bounds of the MESH ONLY.

    Deliberately not ``exactWorldBoundingBox`` on the transform: that includes children, and a
    body transform usually parents the whole skeleton, which inflated the box to 100x the mesh
    and made a perfectly normal body look like a unit mismatch."""
    box = om.MFnDagNode(mesh_path).boundingBox
    matrix = mesh_path.inclusiveMatrix()
    corners = []
    for x in (box.min.x, box.max.x):
        for y in (box.min.y, box.max.y):
            for z in (box.min.z, box.max.z):
                corners.append(om.MPoint(x, y, z) * matrix)
    world = om.MBoundingBox()
    for corner in corners:
        world.expand(corner)
    return world


def _overlap_fraction(target_box, reference_box):
    """How much of the target's volume falls inside the reference's box, 0.0 to 1.0."""
    spans = []
    for axis in ("x", "y", "z"):
        low = max(getattr(target_box.min, axis), getattr(reference_box.min, axis))
        high = min(getattr(target_box.max, axis), getattr(reference_box.max, axis))
        spans.append(max(0.0, high - low))
    overlap = spans[0] * spans[1] * spans[2]

    extent = [max(getattr(target_box.max, axis) - getattr(target_box.min, axis), 1e-9)
              for axis in ("x", "y", "z")]
    return overlap / (extent[0] * extent[1] * extent[2])


def check_alignment(target_path, reference_path, scale_tolerance=100.0):
    """Report — never refuse — when the reference does not look lined up with the target.

    Copying by closest point is meaningless unless the two meshes occupy the same space, and a
    mismatch produces confident-looking garbage rather than an error. Seen for real: a DayZ
    body authored in centimetres (180 units tall) sitting in a scene where the garments are in
    metres (1.8 units) — 100x apart, so every 'closest' body point was the wrong one.

    Neither test can actually tell that case from a small accessory, which is why the result
    is advisory. Measured on a real outfit against a 2.30-unit body, every part correctly
    fitted and within 0.08 of the body surface: jacket ratio 1.63, helmet 5.0, headphone cup
    8.9, helmet patch 59.1 — and the pouches score 0.00 volume overlap because their boxes sit
    outside the body's. The old blocking thresholds (ratio 4, overlap 0.5) rejected most of a
    legitimate model. `scale_tolerance` is now set past the largest measured legitimate ratio,
    so it only catches an order-of-magnitude error.

    Returns an explanatory string when the pair looks odd, or '' when it looks fine."""
    target_box = _bounding_box(target_path)
    reference_box = _bounding_box(reference_path)

    target_size = om.MVector(target_box.max - target_box.min).length()
    reference_size = om.MVector(reference_box.max - reference_box.min).length()
    if target_size <= 0.0 or reference_size <= 0.0:
        return "one of the meshes is degenerate (zero-sized bounding box)"

    ratio = max(target_size, reference_size) / min(target_size, reference_size)
    if ratio > scale_tolerance:
        return ("reference '%s' is %.0fx the size of '%s' — check the units (a body authored "
                "in centimetres next to garments in metres looks like this). Transferring "
                "anyway; undo if the weights come out wrong."
                % (reference_path.partialPathName(), ratio, target_path.partialPathName()))

    # Volume overlap, not a plain intersects(): two boxes touching at a corner "intersect"
    # while sharing almost no space. Seen for real — a Z-up body next to Y-up garments, where
    # the boxes clipped by a few centimetres and the transfer would have been nonsense.
    fraction = _overlap_fraction(target_box, reference_box)
    if fraction < 0.5:
        return ("only %.0f%% of '%s' lies inside '%s' — normal for a pouch or a strap that "
                "hangs off the body, but it also looks like this when the orientation is "
                "wrong. Transferring anyway; undo if the weights come out wrong."
                % (fraction * 100.0, target_path.partialPathName(),
                   reference_path.partialPathName()))
    return ""


def bind_to_reference(target_path, reference_skin):
    """Bind the target to every joint of the reference, replacing any existing skinCluster.

    All joints on purpose: guessing the subset a garment needs is exactly what goes wrong, and
    the unused ones disappear at the pruning step anyway."""
    influences = cmds.skinCluster(reference_skin, query=True, influence=True) or []
    if not influences:
        raise ValueError("reference skinCluster has no influences")

    target = target_path.fullPathName()
    existing = skin_cluster_of(target_path)
    if existing:
        # Its joint set may differ from the reference; rebuilding is simpler than reconciling
        # and the whole command is one undo step.
        cmds.skinCluster(existing, edit=True, unbind=True)

    return cmds.skinCluster(influences, target,
                            toSelectedBones=True,
                            bindMethod=0,            # closest distance; weights get replaced below
                            skinMethod=0,            # classic linear — DayZ has no dual quaternion
                            normalizeWeights=1,
                            maximumInfluences=MAX_INFLUENCES,
                            obeyMaxInfluences=True,
                            removeUnusedInfluence=False)[0]


def transfer_weights(reference_skin, target_skin):
    """Copy weights from the reference onto the target.

    ``oneToOne`` first: the skeleton is shared, so joints must pair up by identity rather than
    by whichever joint happens to sit nearest."""
    cmds.copySkinWeights(sourceSkin=reference_skin, destinationSkin=target_skin,
                         noMirror=True,
                         surfaceAssociation="closestPoint",
                         influenceAssociation=["oneToOne", "closestJoint"])


def mesh_shells(mesh_path):
    """Connected vertex shells of a mesh, as a list of vertex-id lists."""
    from a3ob.mayabridge.commands.helpers.geometry import closed_face_islands
    mesh_fn = om.MFnMesh(mesh_path)
    shells = []
    for _faces, vertices, _closed in closed_face_islands(mesh_fn):
        if vertices:
            shells.append(sorted(vertices))
    return shells


def shell_distances(mesh_path, reference_path, shells):
    """Median distance from each shell's vertices to the reference surface.

    Median, not mean: a strap that touches the body at one end and stands off at the other
    should be judged by its bulk, not dragged either way by its extremes."""
    # The points must be in the REFERENCE mesh's object space. Passing world points together
    # with the mesh's matrix looks like the obvious call, but measured against a known-good
    # answer it returns nonsense: 1.009 where the true gap is 0.0186.
    intersector = om.MMeshIntersector()
    intersector.create(reference_path.node())
    to_reference_space = reference_path.inclusiveMatrix().inverse()
    points = [point * to_reference_space
              for point in om.MFnMesh(mesh_path).getPoints(om.MSpace.kWorld)]

    distances = []
    for vertices in shells:
        measured = []
        for vertex in vertices:
            point = points[vertex]
            try:
                hit = intersector.getClosestPoint(point)
            except Exception:  # noqa: BLE001 - no hit: treat as far away
                hit = None
            if hit is None:
                measured.append(float("inf"))
            else:
                measured.append((om.MPoint(hit.point) - point).length())
        measured.sort()
        distances.append(measured[len(measured) // 2] if measured else float("inf"))
    return distances


def rigidify_shell(skin, mesh_path, vertices, influences):
    """Give every vertex of a shell the shell's average weights, so it moves as one piece.

    The average (rather than the single nearest joint) keeps the transition to the body smooth
    — a backpack strap near the shoulder keeps its blend of Spine and shoulder instead of
    snapping to one of them."""
    shape = mesh_path.fullPathName()
    totals = [0.0] * len(influences)
    for vertex in vertices:
        values = cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex), query=True, value=True)
        for i, value in enumerate(values):
            totals[i] += value

    averaged = sw.prune_normalize([total / len(vertices) for total in totals],
                                  MAX_INFLUENCES, MIN_WEIGHT)
    if sum(averaged) <= 0.0:
        return False

    transform_value = list(zip(influences, averaged))
    for vertex in vertices:
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=transform_value, normalize=False)
    return True


def cap_influences(skin, mesh_path, influences):
    """Force every vertex down to at most MAX_INFLUENCES bones.

    ``maximumInfluences``/``maintainMaxInfluences`` only constrain FUTURE edits — they do not
    retroactively trim weights that copySkinWeights already wrote. Measured on real trousers:
    248 vertices came out of the transfer with 5+ influences, which DayZ cannot represent.

    Only the offending vertices are rewritten (a few hundred out of ~6000), so this stays fast
    and, going through skinPercent, stays undoable."""
    shape = mesh_path.fullPathName()
    fixed = 0
    for vertex in range(om.MFnMesh(mesh_path).numVertices):
        values = cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex), query=True, value=True)
        if sum(1 for value in values if value > 0.0) <= MAX_INFLUENCES:
            continue
        row = sw.prune_normalize(values, MAX_INFLUENCES, MIN_WEIGHT)
        if sum(row) <= 0.0:
            continue
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=list(zip(influences, row)), normalize=False)
        fixed += 1
    return fixed


def finish_for_dayz(skin, mesh_path):
    """Enforce the format's rules: <=4 influences, normalized, nothing below 1/254.

    Weights under 1/254 encode to a zero byte but still list the vertex in the bone's
    selection, which Object Builder paints as a stray member far from the bone."""
    shape = mesh_path.fullPathName()
    cmds.setAttr(skin + ".maxInfluences", MAX_INFLUENCES)
    cmds.setAttr(skin + ".maintainMaxInfluences", True)

    # Weight is never deleted, only moved: every vertex must sum to 1.0, so zeroing an
    # influence forces its weight onto the others. "Distance" (Maya's default) picks them
    # by proximity to the bone and ignores what the surrounding geometry actually uses —
    # measured on a sleeve whose neighbours are pure Elbow, zeroing Head gave Shoulder 0.76
    # / Elbow 0.24. "Neighbors" gave Elbow 1.0. That is the difference between a rigger
    # cleaning weights and a rigger watching head weight land on an arm.
    try:
        cmds.setAttr(skin + ".weightDistribution", 1)  # 1 = Neighbors
    except RuntimeError:  # noqa: BLE001 - locked or connected; not worth failing over
        pass
    cmds.skinPercent(skin, shape, pruneWeights=MIN_WEIGHT)
    cmds.setAttr(skin + ".normalizeWeights", 1)
    cmds.skinCluster(skin, edit=True, forceNormalizeWeights=True)

    # Drop joints that ended up carrying nothing. Binding to the reference's whole skeleton is
    # deliberate, but every influence left attached becomes its own named selection in the
    # exported p3d — 111 bone selections on a garment that genuinely uses 20.
    try:
        cmds.skinCluster(skin, edit=True, removeUnusedInfluence=True)
    except Exception:  # noqa: BLE001 - nothing to remove, or Maya refuses on a locked rig
        pass


def transfer_to_target(target_path, reference_path, far_distance=DEFAULT_FAR_DISTANCE):
    """Run the whole pipeline for one garment. Returns (vertex count, rigidified shells)."""
    reference_skin = skin_cluster_of(reference_path)
    if not reference_skin:
        raise ValueError("reference mesh has no skinCluster")

    # Advisory, not a gate. Refusing here blocked a legitimate model: a helmet patch is
    # 59x smaller than the body and a belt pouch overlaps its bounding box by 0%, and no
    # bounding-box test tells either from a real unit mismatch. A wrong transfer is visible
    # and undoes in one step; a refusal just stops the work.
    problem = check_alignment(target_path, reference_path)
    if problem:
        om.MGlobal.displayWarning("a3obTransferSkin: %s" % problem)

    target_skin = bind_to_reference(target_path, reference_skin)
    transfer_weights(reference_skin, target_skin)

    influences = cmds.skinCluster(target_skin, query=True, influence=True) or []
    shells = mesh_shells(target_path)
    rigidified = 0
    if shells:
        for vertices, distance in zip(shells, shell_distances(target_path, reference_path, shells)):
            if distance > far_distance and rigidify_shell(target_skin, target_path, vertices, influences):
                rigidified += 1

    finish_for_dayz(target_skin, target_path)
    cap_influences(target_skin, target_path,
                   cmds.skinCluster(target_skin, query=True, influence=True) or [])
    return om.MFnMesh(target_path).numVertices, rigidified


__all__ = [
    "DEFAULT_FAR_DISTANCE",
    "skin_cluster_of",
    "selected_mesh_shapes",
    "find_reference",
    "ensure_reference",
    "check_alignment",
    "bind_to_reference",
    "transfer_weights",
    "mesh_shells",
    "shell_distances",
    "rigidify_shell",
    "cap_influences",
    "finish_for_dayz",
    "transfer_to_target",
]
