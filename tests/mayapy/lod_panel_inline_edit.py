"""Type and resolution are edited in the LOD row, and write to that row's node (mayapy).

The old panel edited whatever was SELECTED. Inline editors must address the node of
their own row — a measured scene had three distinct nodes all reading "Resolution 1",
so editing "the selected LOD" while looking at a different row wrote to the wrong one.

Constructing real Qt widgets under mayapy needs a genuine ``QApplication`` in place
*before* ``maya.standalone.initialize()`` runs — Maya's own standalone bring-up creates
a bare ``QGuiApplication``, and building a QWidget against that (rather than a full
``QApplication``) segfaults the process with no Python traceback at all. Creating the
QApplication first makes Maya's init reuse it instead.

Run:  mayapy.exe tests/mayapy/lod_panel_inline_edit.py
"""

import os
import sys

from PySide6 import QtWidgets

_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_two_lods():
    cmds.file(new=True, force=True)
    made = []
    for name in ("alpha", "beta"):
        transform = cmds.polyCube(name=name, ch=False)[0]
        for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                                ("a3obResolution", "long")):
            cmds.addAttr(transform, longName=attribute, attributeType=kind)
        cmds.setAttr(transform + ".a3obIsLOD", True)
        cmds.setAttr(transform + ".a3obResolution", 1)
        made.append(transform)
    return made


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    alpha, beta = build_two_lods()

    from a3ob.ui.dock import MayaObjectBuilderDock
    dock = MayaObjectBuilderDock()
    try:
        dock.refresh_lod_list()
        rows = dock.lod_row_nodes()
        _harness.check(set(rows) >= {alpha, beta} or
                       {r.split("|")[-1] for r in rows} >= {alpha, beta},
                       "both LODs must appear as rows, got %r" % (rows,))

        # Select alpha, then edit BETA's row. The write must land on beta.
        cmds.select(alpha, replace=True)
        dock.set_row_resolution(beta, 7)
        _harness.check(cmds.getAttr(beta + ".a3obResolution") == 7,
                       "editing beta's row must write to beta")
        _harness.check(cmds.getAttr(alpha + ".a3obResolution") == 1,
                       "editing beta's row must NOT touch the selected alpha")

        # Marking must never rename.
        dock.set_row_type(beta, 6)
        _harness.check(cmds.objExists(beta),
                       "changing a LOD's type must not rename its node")
        _harness.check(cmds.getAttr(beta + ".a3obLodType") == 6, "type did not stick")
    finally:
        dock.teardown()
    print("OK - row editors address their own node, and never rename")


main()
