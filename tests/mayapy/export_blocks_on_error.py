"""Export validates every time, and refuses to write a malformed file (mayapy).

Validation used to be gated on three checkboxes that all defaulted to off, and the
result was discarded even when they were on — so nothing could ever stop a bad file
being written.

Run:  mayapy.exe tests/mayapy/export_blocks_on_error.py
"""

import os
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lod_with_bad_mass():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="crate", ch=False)[0]
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obLodType", 6)      # Geometry LOD
    cmds.addAttr(transform, longName="a3obMassValues", dataType="string")
    cmds.setAttr(transform + ".a3obMassValues", "-5.0", type="string")  # negative: an error
    cmds.select(transform, replace=True)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    build_lod_with_bad_mass()

    rows = cmds.a3obValidate() or []
    _harness.check(any(r.startswith("error|") for r in rows),
                   "fixture must produce a real error or this test proves nothing: %r" % (rows,))

    path = os.path.join(tempfile.mkdtemp(), "blocked.p3d")
    # The translator raises RuntimeError after do_write reports the refusal (see
    # MayaObjectBuilderTranslator.writer()) — the same pattern already used by
    # tests/mayapy/export_selection_scope.py and export_auto_lod.py for a refused export.
    raised = False
    try:
        cmds.file(path, force=True, options="selectedOnly=1", type="Arma P3D",
                  preserveReferences=False, exportSelected=True)
    except RuntimeError:
        raised = True
    _harness.check(raised, "export with a validation error must raise, not silently succeed")
    _harness.check(not os.path.isfile(path),
                   "an export with a validation error must write no file")
    print("OK - export refused to write a file with a validation error")


main()
