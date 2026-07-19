"""``a3obSkinWeights`` — select skin-weight outliers so Maya's own tools can fix them.

Weight transfer occasionally binds a lone vertex to a bone from a different body part; the
artefact is invisible in bind pose but Object Builder paints selection membership, so it
shows up as a stray weighted vertex far from its bone.

This command only *finds and selects* them. Fixing is left to `Skin > Smooth Skin Weights`
and `Skin > Prune Small Weights`, which already do it correctly, stay undoable and are what
a rigger expects — an exporter plugin has no business rewriting a rig with its own
heuristic. The detection math lives in ``a3ob.mayabridge.skinweights`` (Maya-free,
unit-tested); this module supplies the Maya plumbing.
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from a3ob.mayabridge import skinweights as sw

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403


def skin_cluster_for_mesh(mesh_path):
    """The skinCluster deforming ``mesh_path``, as an MObject, or None."""
    history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    if not skins:
        return None
    selection = om.MSelectionList()
    selection.add(skins[0])
    return selection.getDependNode(0)


def _complete_vertex_component(mesh_path):
    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.setCompleteData(om.MFnMesh(mesh_path).numVertices)
    return component


def _vertex_neighbours(mesh_path):
    """Connected-vertex ids per vertex."""
    neighbours = [[] for _ in range(om.MFnMesh(mesh_path).numVertices)]
    vertex_it = om.MItMeshVertex(mesh_path)
    while not vertex_it.isDone():
        neighbours[vertex_it.index()] = list(vertex_it.getConnectedVertices())
        vertex_it.next()
    return neighbours


def read_skin(mesh_path):
    """``(skin_fn, weights, influence_count, neighbours)`` for a skinned mesh, or None."""
    skin_obj = skin_cluster_for_mesh(mesh_path)
    if skin_obj is None:
        return None
    skin_fn = oma.MFnSkinCluster(skin_obj)
    if not skin_fn.influenceObjects():
        return None
    weights, influence_count = skin_fn.getWeights(mesh_path, _complete_vertex_component(mesh_path))
    if influence_count <= 0:
        return None
    return skin_fn, list(weights), influence_count, _vertex_neighbours(mesh_path)


def outliers_for_mesh(mesh_path, threshold=sw.DEFAULT_OUTLIER_THRESHOLD):
    """Confirmed ``(vertex, clean_neighbours)`` pairs (empty without a skinCluster)."""
    skin = read_skin(mesh_path)
    if skin is None:
        return []
    _skin_fn, weights, influence_count, neighbours = skin
    return sw.find_outliers(weights, influence_count, neighbours, threshold)


def _skinned_mesh_paths(selection_only):
    """Mesh shape paths of the targeted LODs that actually carry a skinCluster."""
    paths = []
    for lod in lod_transforms(selection_only):
        mesh = first_mesh_child(lod)
        if mesh.isNull():
            continue
        paths.append(om.MFnDagNode(mesh).getPath())
    return paths


class SkinWeightsCommand(_Base):
    kName = "a3obSkinWeights"

    @staticmethod
    def creator():
        return SkinWeightsCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-so", "-selectionOnly")
        s.addFlag("-t", "-threshold", om.MSyntax.kDouble)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)
        selection_only = argdb.isFlagSet("-so")
        threshold = argdb.flagArgumentDouble("-t", 0) if argdb.isFlagSet("-t") else sw.DEFAULT_OUTLIER_THRESHOLD

        mesh_paths = _skinned_mesh_paths(selection_only)
        if not mesh_paths:
            om.MGlobal.displayError("a3obSkinWeights: no LOD meshes found")
            self.setResult(0)
            return

        total = 0
        skinned = 0
        to_select = om.MSelectionList()
        for mesh_path in mesh_paths:
            skin = read_skin(mesh_path)
            if skin is None:
                continue
            skinned += 1
            _skin_fn, weights, influence_count, neighbours = skin
            outliers = sw.find_outliers(weights, influence_count, neighbours, threshold)
            if not outliers:
                continue
            total += len(outliers)
            component_fn = om.MFnSingleIndexedComponent()
            component = component_fn.create(om.MFn.kMeshVertComponent)
            component_fn.addElements([vertex for vertex, _clean in outliers])
            to_select.add((mesh_path, component))

        if skinned == 0:
            om.MGlobal.displayWarning("a3obSkinWeights: none of the targeted LODs has a skinCluster")
        elif total == 0:
            om.MGlobal.displayInfo("a3obSkinWeights: no weight outliers in %d skinned LOD(s)" % skinned)
        else:
            om.MGlobal.setActiveSelectionList(to_select, om.MGlobal.kReplaceList)
            om.MGlobal.displayWarning(
                "a3obSkinWeights: selected %d outlier vertex(es) in %d skinned LOD(s) — "
                "fix with Skin > Smooth Skin Weights" % (total, skinned))

        self.setResult(total)


__all__ = [
    "SkinWeightsCommand",
    "TransferSkinCommand",
    "TestPoseCommand",
    "ReferenceAssetCommand",
    "BakeSkinCommand",
    "skin_cluster_for_mesh",
    "read_skin",
    "outliers_for_mesh",
]


class TransferSkinCommand(_Base):
    """``a3obTransferSkin`` — copy DayZ weights from the reference body onto the selection."""

    kName = "a3obTransferSkin"

    @staticmethod
    def creator():
        return TransferSkinCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-rf", "-referenceMesh", om.MSyntax.kString)
        s.addFlag("-d", "-distance", om.MSyntax.kDouble)
        return s

    def doIt(self, args):
        from a3ob.mayabridge import skintransfer

        argdb = om.MArgDatabase(self.syntax(), args)
        explicit = argdb.flagArgumentString("-rf", 0) if argdb.isFlagSet("-rf") else ""
        distance = (argdb.flagArgumentDouble("-d", 0) if argdb.isFlagSet("-d")
                    else skintransfer.DEFAULT_FAR_DISTANCE)

        targets = skintransfer.selected_mesh_shapes()
        if not targets:
            om.MGlobal.displayError("a3obTransferSkin: select the garment mesh (or meshes)")
            self.setResult(0)
            return

        try:
            reference, imported = skintransfer.ensure_reference(targets, explicit)
        except ValueError as error:
            om.MGlobal.displayError("a3obTransferSkin: %s" % error)
            self.setResult(0)
            return

        if imported:
            # The scene just gained a body and a skeleton; say so rather than letting the
            # user wonder where they came from.
            om.MGlobal.displayInfo(
                "a3obTransferSkin: no body in the scene — added the saved reference "
                "(%d top-level node(s)); it stays, the rig needs its joints" % len(imported))

        reference_key = reference.fullPathName()
        done = 0
        # One Ctrl+Z must undo the whole transfer, not each internal cmds call.
        with undo_chunk():
            for target in targets:
                if target.fullPathName() == reference_key:
                    continue  # never rewrite the reference body itself
                try:
                    count, rigid = skintransfer.transfer_to_target(target, reference, distance)
                except ValueError as error:
                    om.MGlobal.displayError("a3obTransferSkin: %s" % error)
                    continue
                done += 1
                om.MGlobal.displayInfo(
                    "a3obTransferSkin: %s <- %s (%d verts, %d rigid shell(s))"
                    % (target.partialPathName(), reference.partialPathName(), count, rigid))

        if done == 0:
            om.MGlobal.displayError("a3obTransferSkin: nothing was transferred")
        self.setResult(done)


class TestPoseCommand(_Base):
    """``a3obTestPose`` — bend the rig, report vertices that move unlike their neighbours."""

    kName = "a3obTestPose"

    @staticmethod
    def creator():
        return TestPoseCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-tol", "-tolerance", om.MSyntax.kDouble)
        return s

    def doIt(self, args):
        from a3ob.mayabridge import posetest
        from a3ob.mayabridge import skintransfer

        argdb = om.MArgDatabase(self.syntax(), args)
        tolerance = (argdb.flagArgumentDouble("-tol", 0) if argdb.isFlagSet("-tol")
                     else posetest.DEFAULT_SPIKE_TOLERANCE)

        targets = skintransfer.selected_mesh_shapes()
        if not targets:
            om.MGlobal.displayError("a3obTestPose: select a skinned mesh to test")
            self.setResult(0)
            return

        total = 0
        to_select = om.MSelectionList()
        for mesh_path in targets:
            if not skin_cluster_for_mesh(mesh_path):
                continue
            spikes, moved = posetest.find_spikes(mesh_path, tolerance=tolerance)
            if moved == 0:
                om.MGlobal.displayWarning(
                    "a3obTestPose: no test joints found on this rig — nothing was bent")
                continue
            total += len(spikes)
            if spikes:
                component_fn = om.MFnSingleIndexedComponent()
                component = component_fn.create(om.MFn.kMeshVertComponent)
                component_fn.addElements([vertex for vertex, _m, _a in spikes])
                to_select.add((mesh_path, component))
            om.MGlobal.displayInfo("a3obTestPose: %s — %d joints bent, %d spike(s)"
                                   % (mesh_path.partialPathName(), moved, len(spikes)))

        if total:
            om.MGlobal.setActiveSelectionList(to_select, om.MGlobal.kReplaceList)
            om.MGlobal.displayWarning(
                "a3obTestPose: selected %d vertex(es) that deform unlike their neighbours — "
                "fix with Skin > Smooth Skin Weights" % total)
        else:
            om.MGlobal.displayInfo("a3obTestPose: no deformation spikes found")
        self.setResult(total)


class ReferenceAssetCommand(_Base):
    """``a3obReference`` — add or save the DayZ body / skeleton reference assets."""

    kName = "a3obReference"

    @staticmethod
    def creator():
        return ReferenceAssetCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-k", "-kind", om.MSyntax.kString)
        s.addFlag("-sv", "-store", om.MSyntax.kString)   # "save": store the selection instead
        return s

    def doIt(self, args):
        from a3ob.mayabridge import references

        argdb = om.MArgDatabase(self.syntax(), args)
        kind = argdb.flagArgumentString("-k", 0) if argdb.isFlagSet("-k") else "male_body"
        if kind not in references.KINDS:
            om.MGlobal.displayError("a3obReference: unknown kind '%s' (expected one of %s)"
                                    % (kind, ", ".join(sorted(references.KINDS))))
            self.setResult("")
            return

        try:
            if argdb.isFlagSet("-sv"):
                path = argdb.flagArgumentString("-sv", 0)
                saved = references.save_reference(kind, path if path != "1" else "")
                om.MGlobal.displayInfo("a3obReference: saved %s reference to %s"
                                       % (references.KINDS[kind][1], saved))
                self.setResult(saved)
                return

            with undo_chunk():
                created = references.add_reference(kind)
            om.MGlobal.displayInfo("a3obReference: added %s (%d top-level node(s))"
                                   % (references.KINDS[kind][1], len(created)))
            self.setResult(created[0] if created else "")
        except Exception as error:  # noqa: BLE001 - report, never traceback at the user
            om.MGlobal.displayError("a3obReference: %s" % error)
            self.setResult("")


class BakeSkinCommand(_Base):
    """``a3obBakeSkin`` — copy live skinCluster weights onto the LOD transform.

    Deleting the skeleton deletes the skinCluster and every weight with it, and the export
    then produces a file with no bone selections at all. Baking first makes the weights
    survive that."""

    kName = "a3obBakeSkin"

    @staticmethod
    def creator():
        return BakeSkinCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-so", "-selectionOnly")
        return s

    def doIt(self, args):
        from a3ob.mayabridge import skinweights as sw
        from a3ob.mayabridge import attributes as attr
        from a3ob.mayabridge.attributes import A

        argdb = om.MArgDatabase(self.syntax(), args)
        selection_only = argdb.isFlagSet("-so")

        baked = 0
        with undo_chunk():
            for lod in lod_transforms(selection_only):
                mesh = first_mesh_child(lod)
                if mesh.isNull():
                    continue
                mesh_path = om.MFnDagNode(mesh).getPath()
                skin = read_skin(mesh_path)
                if skin is None:
                    continue
                skin_fn, weights, influence_count, _neighbours = skin
                names = [p.partialPathName().split("|")[-1].split(":")[-1]
                         for p in skin_fn.influenceObjects()]
                text = sw.bake_string(names, weights, influence_count)
                if not text:
                    continue
                attr.set_string(lod, A.BAKED_WEIGHTS, text)
                baked += 1
                om.MGlobal.displayInfo("a3obBakeSkin: baked %d bone(s) onto %s"
                                       % (len(names), node_name(lod)))

        if baked == 0:
            om.MGlobal.displayWarning("a3obBakeSkin: no skinned LOD found to bake")
        self.setResult(baked)
