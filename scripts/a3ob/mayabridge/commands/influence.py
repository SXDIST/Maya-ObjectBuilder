"""``a3obInfluence`` — list, inspect and remove the bones driving the selected mesh.

Dropping a bone from a garment is a round trip in stock Maya: leave the paint tool, find
the joint in the Outliner, add the mesh back to the selection, use the menu, return to
painting. Everything needed to make the decision is visible only inside the paint tool,
and the operation is only available outside it. This command is the scriptable half of the
dock's Influences panel.

Removing an influence never deletes its weight. Every vertex must sum to 1.0, so the weight
moves to the other influences, and the skinCluster's ``weightDistribution`` decides which:
"Distance" hands it to the nearest bone and "Neighbors" to whatever the surrounding
vertices already use. Distance is Maya's default and is how head weight ends up on an arm,
so removal switches to Neighbors first — during removal, not after, because the
redistribution happens as part of it.
"""

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import maya.cmds as cmds

from a3ob.mayabridge import influences as inf
from a3ob.mayabridge import skinweights as sw

from a3ob.mayabridge.commands.helpers import *  # noqa: F401,F403

# Artisan's skin-paint contexts are named around this stem (artAttrSkinContext,
# artAttrSkinPaintCtx...). Matching on the stem avoids depending on one exact spelling.
_PAINT_CONTEXT_STEM = "artAttrSkin"


def selected_mesh_shape():
    """The first mesh shape in the selection, as a full path, or ''."""
    for name in cmds.ls(selection=True, long=True) or []:
        node = name.split(".", 1)[0]
        if cmds.nodeType(node) == "mesh":
            return node
        shapes = cmds.listRelatives(node, shapes=True, fullPath=True,
                                    noIntermediate=True, type="mesh") or []
        if shapes:
            return shapes[0]
    return ""


def skin_cluster_of_shape(shape):
    """The skinCluster deforming a mesh shape, as a node name, or ''."""
    history = cmds.listHistory(shape, pruneDagObjects=True) or []
    skins = cmds.ls(history, type="skinCluster") or []
    return skins[0] if skins else ""


def influence_names(shape):
    """Influence names of the mesh's skinCluster (empty when it has none)."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return []
    return cmds.skinCluster(skin, query=True, influence=True) or []


def vertices_driven_by(shape, influence, threshold=sw.MIN_ENCODABLE_WEIGHT):
    """``shape.vtx[i]`` names the influence drives above the p3d encoding threshold.

    Below 1/254 a weight encodes to a zero byte and never reaches the file, so showing
    those vertices would misrepresent what is actually bound.

    Read through MFnSkinCluster rather than per-vertex skinPercent: a garment runs to
    thousands of vertices and one query each is unusable interactively."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return []

    mesh_selection = om.MSelectionList()
    mesh_selection.add(shape)
    mesh_path = mesh_selection.getDagPath(0)

    skin_selection = om.MSelectionList()
    skin_selection.add(skin)
    skin_fn = oma.MFnSkinCluster(skin_selection.getDependNode(0))

    # The dock passes a bare leaf name (what the user typed or clicked), so an exact
    # partialPathName() match is tried FIRST and, if found, wins outright — that is the
    # only way to disambiguate a fully-qualified caller like "ns1:Head" from "ns2:Head".
    # Only when there is no exact hit do we fall back to leaf-name matching, which is what
    # makes a short name typed in the dock work at all. But a scene with referenced rigs
    # can carry the very same leaf under two different namespaces, and if the fallback ever
    # matched more than one influence, silently picking the first would paint the wrong half
    # of the mesh with no error — so an ambiguous leaf match returns nothing instead.
    names = [path.partialPathName() for path in skin_fn.influenceObjects()]
    index = next((i for i, name in enumerate(names) if name == influence), -1)
    if index < 0:
        leaf = inf.leaf_name(influence)
        matches = [i for i, name in enumerate(names) if inf.leaf_name(name) == leaf]
        if len(matches) > 1:
            om.MGlobal.displayWarning(
                "a3obInfluence: '%s' is ambiguous — it matches %s; use the full path to "
                "pick one" % (influence, ", ".join(names[i] for i in matches)))
            return []
        index = matches[0] if matches else -1
    if index < 0:
        return []

    component_fn = om.MFnSingleIndexedComponent()
    component = component_fn.create(om.MFn.kMeshVertComponent)
    component_fn.setCompleteData(om.MFnMesh(mesh_path).numVertices)
    weights, count = skin_fn.getWeights(mesh_path, component)
    if count <= 0:
        return []

    return ["%s.vtx[%d]" % (shape, vertex)
            for vertex in range(len(weights) // count)
            if weights[vertex * count + index] > threshold]


def _leave_paint_tool():
    """Leave the Artisan paint tool, returning the context to restore (or '').

    Changing a skinCluster's influence list while the paint tool holds it is the leading
    suspect in a silent, log-less crash. Contexts exist only in an interactive session —
    under mayapy ``currentCtx()`` returns None — so this is a no-op headlessly."""
    try:
        current = cmds.currentCtx()
    except Exception:  # noqa: BLE001 - no UI at all
        return ""
    if not current or _PAINT_CONTEXT_STEM not in current:
        return ""
    try:
        cmds.setToolTo("selectSuperContext")
    except Exception:  # noqa: BLE001 - nothing to switch to; carry on regardless
        return ""
    return current


def _restore_tool(context):
    """Put the paint tool back. Never fatal: the removal already succeeded."""
    if not context:
        return
    try:
        if cmds.contextInfo(context, exists=True):
            cmds.setToolTo(context)
    except Exception:  # noqa: BLE001 - context went away underneath us
        pass


def remove_influences(shape, requested):
    """Remove the named influences. Returns ``(removed names, reason nothing was)``."""
    skin = skin_cluster_of_shape(shape)
    if not skin:
        return [], "no skinCluster on %s" % shape

    names = cmds.skinCluster(skin, query=True, influence=True) or []
    allowed, reason = inf.removable(names, requested)
    if not allowed:
        return [], reason

    survivors = [name for name in names if name not in set(allowed)]
    locked = [name for name in survivors
              if cmds.attributeQuery("lockInfluenceWeights", node=name, exists=True)
              and cmds.getAttr(name + ".lockInfluenceWeights")]
    if survivors and len(locked) == len(survivors):
        return [], ("every remaining influence is locked (%s) — normalization would have "
                    "nowhere to put the weight"
                    % ", ".join(inf.leaf_name(name) for name in locked[:4]))

    context = _leave_paint_tool()
    try:
        with undo_chunk():
            try:
                # Neighbors, and BEFORE the removal: redistribution happens during it.
                cmds.setAttr(skin + ".weightDistribution", 1)
            except RuntimeError:
                pass  # locked or driven by a connection; not worth failing over
            cmds.skinCluster(skin, edit=True, removeInfluence=allowed)
    finally:
        _restore_tool(context)
    return allowed, ""


class InfluenceCommand(_Base):
    """``a3obInfluence`` — the scene half of the dock's Influences panel."""

    kName = "a3obInfluence"

    @staticmethod
    def creator():
        return InfluenceCommand()

    @staticmethod
    def syntax():
        s = om.MSyntax()
        s.addFlag("-li", "-listInfluences")
        s.addFlag("-ri", "-removeInfluences", om.MSyntax.kString)
        s.addFlag("-sv", "-selectVertices", om.MSyntax.kString)
        return s

    def doIt(self, args):
        argdb = om.MArgDatabase(self.syntax(), args)

        shape = selected_mesh_shape()
        if not shape:
            om.MGlobal.displayWarning("a3obInfluence: select a skinned mesh first")
            self.setResult([])
            return

        if argdb.isFlagSet("-sv"):
            name = argdb.flagArgumentString("-sv", 0)
            components = vertices_driven_by(shape, name)
            if not components:
                om.MGlobal.displayWarning(
                    "a3obInfluence: '%s' drives no vertex above %.5f on %s"
                    % (name, sw.MIN_ENCODABLE_WEIGHT, shape.split("|")[-1]))
                self.setResult(0)
                return
            cmds.select(components, replace=True)
            om.MGlobal.displayInfo("a3obInfluence: selected %d vertex(es) driven by %s"
                                   % (len(components), inf.leaf_name(name)))
            self.setResult(len(components))
            return

        if argdb.isFlagSet("-ri"):
            requested = [name for name in argdb.flagArgumentString("-ri", 0).split(",") if name]
            removed, reason = remove_influences(shape, requested)
            if reason:
                om.MGlobal.displayWarning("a3obInfluence: %s" % reason)
            else:
                om.MGlobal.displayInfo(
                    "a3obInfluence: removed %d influence(s) — weight moved to the bones the "
                    "neighbouring vertices use: %s"
                    % (len(removed), ", ".join(inf.leaf_name(name) for name in removed)))
            self.setResult(len(removed))
            return

        names = influence_names(shape)
        if not names:
            om.MGlobal.displayWarning("a3obInfluence: %s has no skinCluster"
                                      % shape.split("|")[-1])
        self.setResult(names)


__all__ = [
    "InfluenceCommand",
    "selected_mesh_shape",
    "skin_cluster_of_shape",
    "influence_names",
    "vertices_driven_by",
    "remove_influences",
]
