"""Maya workflow test for a3obSkinWeights (run with mayapy).

Builds a skinned cylinder LOD on a two-joint chain, plants one weight-transfer artefact
(a vertex at the top bound entirely to the lower joint), then checks that the command
selects exactly that vertex and that a3obValidate surfaces it as a warning. Repair is
deliberately NOT the plugin's job — Skin > Smooth Skin Weights does that.

Run:  mayapy.exe tests/mayapy/skin_weights_workflow.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def unwrap(result):
    """MPxCommand.setResult comes back as a 1-element list under mayapy."""
    if isinstance(result, (list, tuple)):
        return result[0] if result else 0
    return result


def main():
    _harness.load_plugin()

    transform = cmds.polyCylinder(r=1, h=6, sx=12, sy=8, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")

    cmds.select(clear=True)
    root = cmds.joint(position=(0, -3, 0), name="Lower")
    tip = cmds.joint(position=(0, 3, 0), name="Upper")
    skin = cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)[0]

    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    vertex_count = cmds.polyEvaluate(transform, vertex=True)

    # Maya's default bind gives this cylinder a nearly flat 0.5/0.5 gradient, which is too
    # weak for any outlier to stand out. Paint an explicit linear gradient along Y instead,
    # so the test measures the detector rather than Maya's bind heuristics.
    for i in range(vertex_count):
        height = cmds.pointPosition("%s.vtx[%d]" % (shape, i), world=True)[1]
        upper = min(1.0, max(0.0, (height + 3.0) / 6.0))
        cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, i),
                         transformValue=[(root, 1.0 - upper), (tip, upper)])

    # Pick a vertex near the top (dominated by Upper) and rebind it fully to Lower.
    top_vertex = None
    for i in range(vertex_count):
        if cmds.pointPosition("%s.vtx[%d]" % (shape, i), world=True)[1] > 2.5:
            top_vertex = i
            break
    _harness.check(top_vertex is not None, "no vertex found near the top of the cylinder")

    cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, top_vertex),
                     transformValue=[(root, 1.0), (tip, 0.0)])

    cmds.select(clear=True)
    found = unwrap(cmds.a3obSkinWeights())
    _harness.check(found == 1, "expected 1 outlier, got %r" % (found,))

    # Maya reports the component under the transform's short name, so compare the index.
    selected = cmds.ls(selection=True, flatten=True)
    _harness.check(len(selected) == 1 and selected[0].endswith(".vtx[%d]" % top_vertex),
          "expected only the artefact vertex selected, got %r" % (selected,))

    rows = cmds.a3obValidate() or []
    _harness.check(any("skin weight outlier" in row for row in rows),
          "a3obValidate must report the outlier, got %r" % (rows,))

    # The plugin must NOT have touched the rig — reporting only.
    still = cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, top_vertex), query=True, value=True)
    _harness.check(still[0] == 1.0 and still[1] == 0.0,
          "weights must be left untouched by a report-only command, got %r" % (still,))

    print("OK a3obSkinWeights detects and selects the artefact (vtx[%d])" % top_vertex)


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
