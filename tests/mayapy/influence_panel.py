"""a3obInfluence: list, inspect and remove the bones driving a mesh (run with mayapy).

Removing a bone cannot delete its weight — every vertex must sum to 1.0, so the weight
moves to other influences. Which ones is decided by the skinCluster's weightDistribution:
"Distance" picks the nearest bone and "Neighbors" picks what the surrounding vertices
already use. Measured on a collar weighted to facial bones, removing them under Neighbors
puts the weight on Head/Neck; under Distance it scatters. The command must set Neighbors
BEFORE removing, because redistribution happens during the removal.

Run:  mayapy.exe tests/mayapy/influence_panel.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def unwrap(result):
    """MPxCommand.setResult comes back as a 1-element list under mayapy."""
    if isinstance(result, (list, tuple)) and len(result) == 1:
        return result[0]
    return result


def build():
    """A collar skinned to Neck/Head plus two facial bones it should never have kept."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="collar", r=1, h=6, sx=8, sy=6, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]

    cmds.select(clear=True)
    neck = cmds.joint(position=(0, -3, 0), name="Neck")
    head = cmds.joint(position=(0, 0, 0), name="Head")
    cmds.select(clear=True)
    jaw = cmds.joint(position=(0.5, 1, 0), name="Face_Jawbone")
    chin = cmds.joint(position=(0.5, 1.5, 0), name="Face_Chin")

    skin = cmds.skinCluster(neck, head, jaw, chin, mesh,
                            toSelectedBones=True, maximumInfluences=4)[0]
    # Everything on Head, except a band that (wrongly) sits on the facial bones.
    for vertex in range(cmds.polyEvaluate(mesh, vertex=True)):
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=[(neck, 0.0), (head, 1.0), (jaw, 0.0), (chin, 0.0)])
    # A hair of pre-existing Head weight, as any real bind would have at a garment/body
    # seam: Maya's "Neighbors" distribution preserves the ratio a vertex ALREADY has
    # among its surviving influences (not the weights of its mesh neighbours, despite the
    # name) and falls back to nearest-bone ("Distance") when that ratio is exactly 0:0 —
    # verified against this Maya build by reproducing the raw skinCluster calls outside
    # this command entirely. A literal 0.0 here would make Neighbors mode indistinguishable
    # from Distance mode and defeat the point of the assertion below.
    for vertex in range(8):
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex),
                         transformValue=[(neck, 0.0), (head, 0.001), (jaw, 0.599), (chin, 0.4)])
    return mesh, shape, skin


def main():
    cmds.loadPlugin(os.path.join(_REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)

    # _syntax_is_safe skips a command whose syntax() Maya rejects, so a bad flag name shows
    # up as the command simply not existing rather than as a crash. Catch that here.
    check(cmds.pluginInfo("MayaObjectBuilder", query=True, loaded=True),
          "the plugin must be loaded")
    check("a3obInfluence" in (cmds.pluginInfo("MayaObjectBuilder", query=True, command=True) or []),
          "a3obInfluence did not register — a flag long name was probably rejected")

    mesh, shape, skin = build()
    cmds.select(mesh, replace=True)

    # 1. Listing
    listed = cmds.a3obInfluence(listInfluences=True) or []
    if isinstance(listed, str):
        listed = [listed]
    leaves = {name.split("|")[-1].split(":")[-1] for name in listed}
    check(leaves == {"Neck", "Head", "Face_Jawbone", "Face_Chin"},
          "all four influences must be listed, got %r" % (sorted(leaves),))

    # 2. Selecting the vertices a bone drives
    count = int(unwrap(cmds.a3obInfluence(selectVertices="Face_Jawbone")) or 0)
    check(count == 8, "Face_Jawbone drives the 8-vertex band, got %d" % count)
    selected = cmds.ls(selection=True, flatten=True) or []
    check(all(".vtx[" in item for item in selected),
          "the selection must be vertex components, got %r" % (selected[:3],))

    # 3. Removing — the weight must land where the neighbours are, not on the nearest bone
    cmds.select(mesh, replace=True)
    removed = int(unwrap(cmds.a3obInfluence(removeInfluences="Face_Jawbone,Face_Chin")) or 0)
    check(removed == 2, "both facial bones must be removed, got %d" % removed)

    left = cmds.skinCluster(skin, query=True, influence=True) or []
    check({n.split("|")[-1] for n in left} == {"Neck", "Head"},
          "only Neck and Head may remain, got %r" % (left,))
    check(cmds.getAttr(skin + ".weightDistribution") == 1,
          "weightDistribution must be Neighbors (1) so weight follows the neighbours")

    values = cmds.skinPercent(skin, "%s.vtx[0]" % shape, query=True, value=True)
    check(abs(sum(values) - 1.0) < 1e-4, "the vertex must stay normalized, got %r" % (values,))
    head_index = [n.split("|")[-1] for n in left].index("Head")
    check(values[head_index] > 0.5,
          "the facial weight must have moved to Head like its neighbours, got %r" % (values,))

    # 4. Refusing to strip the mesh bare — the mesh is still selected from step 3 (neither
    # a3obInfluence nor a refusal touches the selection), and re-selecting it here would push
    # its own undo entry ahead of the one below, so the later single undo would only undo the
    # reselect instead of the removal.
    stripped = int(unwrap(cmds.a3obInfluence(removeInfluences=",".join(left))) or 0)
    check(stripped == 0, "removing every influence must be refused, removed %d" % stripped)
    check(len(cmds.skinCluster(skin, query=True, influence=True) or []) == 2,
          "the refusal must leave the skinCluster untouched")

    # 5. One undo takes the whole removal back
    cmds.undo()
    restored = {n.split("|")[-1] for n in (cmds.skinCluster(skin, query=True, influence=True) or [])}
    check("Face_Jawbone" in restored,
          "one undo must restore the removed influences, got %r" % (sorted(restored),))

    print("OK a3obInfluence lists, selects, removes to neighbours, refuses to strip, undoes")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL influence_panel: %s" % error, file=sys.stderr)
        raise
