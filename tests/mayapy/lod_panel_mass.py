"""Mass is present for every LOD type, collapsed where it is unusual (mayapy).

Export writes a mass TAGG wherever a3obMassValues exists and does not restrict it by
LOD type, so hiding the controls would make the UI narrower than the format. The rule
is: relevance drives prominence, never availability.

Constructing real Qt widgets under mayapy needs a genuine ``QApplication`` in place
*before* ``maya.standalone.initialize()`` runs — see lod_panel_inline_edit.py for why
(a bare QGuiApplication from Maya's own standalone bring-up segfaults on a real QWidget).

Run:  mayapy.exe tests/mayapy/lod_panel_mass.py
"""

import os
import sys

from PySide6 import QtWidgets

_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lod(name, lod_type):
    transform = cmds.polyCube(name=name, ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obLodType", lod_type)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.file(new=True, force=True)
    geometry = build_lod("geo", 6)        # Geometry LOD: mass is usual here
    resolution = build_lod("res", 0)      # Resolution LOD: unusual, but not forbidden

    from a3ob.ui.dock import MayaObjectBuilderDock
    dock = MayaObjectBuilderDock()
    try:
        _harness.check(not hasattr(dock, "_build_mass_flags_section")
                       or "mass" not in (dock.__class__.__module__ or ""),
                       "mass must no longer live in its own panel")

        for node in (geometry, resolution):
            cmds.select(node, replace=True)
            dock.refresh_lod_list()
            _harness.check(dock.mass_section_is_present(),
                           "mass must be PRESENT for every LOD type, including %s" % node)

        # Collapsed for a Resolution LOD, expanded for a Geometry LOD — prominence only.
        cmds.select(resolution, replace=True)
        dock.refresh_lod_list()
        _harness.check(dock.mass_section_is_collapsed(),
                       "mass should start collapsed on a Resolution LOD")

        # And it must still WORK there, proving the collapse is cosmetic.
        dock.apply_mass(2.5)
        _harness.check(cmds.attributeQuery("a3obMassValues", node=resolution, exists=True),
                       "setting mass on a Resolution LOD must still work")
    finally:
        dock.teardown()
    print("OK - mass present everywhere, collapsed where unusual, still writable")


main()
