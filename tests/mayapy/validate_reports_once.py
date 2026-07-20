"""A scene-global issue is reported once, not once per LOD (mayapy).

_validate_object_sets runs per mesh and walks EVERY set in the scene, so an empty set
was reported once per LOD — 21 rows on a six-LOD scene where a handful of problems
existed. Every set was also inspected once per LOD: 245 inspections where 35 would do.

Run:  mayapy.exe tests/mayapy/validate_reports_once.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lods(count):
    cmds.file(new=True, force=True)
    for index in range(count):
        transform = cmds.polyCube(name="lod%d" % index, ch=False)[0]
        for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                           ("a3obResolution", "long")):
            cmds.addAttr(transform, longName=name, attributeType=kind)
        cmds.setAttr(transform + ".a3obIsLOD", True)
        cmds.setAttr(transform + ".a3obResolution", index + 1)
    empty = cmds.sets(name="a3ob_SEL_gone", empty=True)
    cmds.addAttr(empty, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(empty + ".a3obSelectionName", "camo_gone", type="string")


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    build_lods(6)
    rows = [r for r in (cmds.a3obValidate() or []) if "no live members" in r]
    _harness.check(len(rows) == 1,
                   "one empty set in a 6-LOD scene must be reported ONCE, got %d: %r"
                   % (len(rows), rows))

    # And the count must not scale with LOD count.
    build_lods(2)
    rows_small = [r for r in (cmds.a3obValidate() or []) if "no live members" in r]
    _harness.check(len(rows_small) == 1,
                   "still once with 2 LODs, got %d" % len(rows_small))
    print("OK - scene-global issues reported once regardless of LOD count")


main()
