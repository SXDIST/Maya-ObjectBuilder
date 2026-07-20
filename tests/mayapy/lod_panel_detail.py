"""Named properties live under the selected LOD's row, and apply to it (mayapy).

They are per-LOD data — a3obProperties on the LOD transform, exported as that LOD's
TAGGs — so they belong where the LOD is selected, not in a panel of their own.

Run:  mayapy.exe tests/mayapy/lod_panel_detail.py
"""

import os
import sys

from PySide6 import QtWidgets

_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_lod(name):
    transform = cmds.polyCube(name=name, ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    return transform


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.file(new=True, force=True)
    alpha = build_lod("alpha")
    beta = build_lod("beta")

    from a3ob.ui.dock import MayaObjectBuilderDock
    dock = MayaObjectBuilderDock()
    try:
        _harness.check(not hasattr(dock, "_build_named_properties_tab"),
                       "the standalone Named Properties panel should be gone")

        cmds.select(alpha, replace=True)
        dock.refresh_lod_list()
        dock.apply_named_property("lodnoshadow", "1")
        _harness.check("lodnoshadow=1" in (cmds.getAttr(alpha + ".a3obProperties") or ""),
                       "the property must land on the selected LOD")
        _harness.check(not cmds.attributeQuery("a3obProperties", node=beta, exists=True)
                       or "lodnoshadow" not in (cmds.getAttr(beta + ".a3obProperties") or ""),
                       "it must not land on any other LOD")

        # A property outside the known vocabulary must still be storable — the combo
        # suggests, it does not restrict.
        dock.apply_named_property("someCustomThing", "42")
        _harness.check("someCustomThing=42" in (cmds.getAttr(alpha + ".a3obProperties") or ""),
                       "an unknown property name must still be accepted")

        # Regression: refresh_lod_list() now calls refresh_named_properties() at its own
        # end, and the "LODs" branch of dock._refresh_dirty_panels feeds it with no
        # defer= (unlike Materials, which passes defer=self._material_fields_focused()).
        # That means a SceneWatcher callback on the displayed LOD can rebuild the named
        # properties list while the user is mid-edit in one of the combos. It is safe
        # today only because refresh_named_properties() writes the combos solely when no
        # LOD resolves, and clearing/repopulating named_list does not re-fire
        # currentItemChanged with a valid item. Pin that as a test, not as folklore that
        # the next "auto-sync the combos" change could silently break.
        cmds.select(alpha, replace=True)
        dock.refresh_lod_list()
        dock.named_name_combo.lineEdit().setText("midEditName")
        dock.named_value_combo.lineEdit().setText("mid-edit-value")
        typed_name = dock.named_name_combo.lineEdit().text()
        typed_value = dock.named_value_combo.lineEdit().text()

        dock.refresh_lod_list()  # the path that now reaches refresh_named_properties()

        _harness.check(dock.named_name_combo.lineEdit().text() == typed_name,
                       "a LOD list refresh must not clobber an in-progress named-property name edit")
        _harness.check(dock.named_value_combo.lineEdit().text() == typed_value,
                       "a LOD list refresh must not clobber an in-progress named-property value edit")
    finally:
        dock.teardown()
    print("OK - named properties follow the selected LOD and accept unknown names")


main()
