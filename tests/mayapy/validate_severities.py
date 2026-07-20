"""Issues that silently change the exported file get their own severity (mayapy).

On a measured scene a3obValidate reported 0 errors and 21 warnings — so "errors block
the export" would never once have fired, while two camo selections silently did not
reach the P3D. A two-level scheme cannot express "this file will be written, and it
will quietly not be what you think it is".

Run:  mayapy.exe tests/mayapy/validate_severities.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_posed_rig():
    cmds.file(new=True, force=True)
    transform = cmds.polyCylinder(name="garment", r=1, h=4, sx=8, sy=4, ch=False)[0]
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    cmds.setAttr(tip + ".rotateX", 35)   # pose it: export would bake this in
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    build_posed_rig()

    rows = cmds.a3obValidate() or []
    posed = [r for r in rows if "pose" in r.lower()]
    _harness.check(posed, "a posed rig must be reported at all, got %r" % (rows,))
    _harness.check(posed[0].startswith("damage|"),
                   "a posed rig silently bakes the pose into the export — that is damage, "
                   "not a warning: %r" % (posed[0],))

    # An empty Object Builder set: its selection simply will not reach the P3D.
    empty = cmds.sets(name="a3ob_SEL_gone", empty=True)
    cmds.addAttr(empty, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(empty + ".a3obSelectionName", "camo_gone", type="string")
    rows = cmds.a3obValidate() or []
    lost = [r for r in rows if "no live members" in r]
    _harness.check(lost, "an empty selection set must be reported, got %r" % (rows,))
    _harness.check(lost[0].startswith("damage|"),
                   "a selection that will not reach the file is damage: %r" % (lost[0],))
    print("OK - posed rig and empty selection both reported as damage")


main()
