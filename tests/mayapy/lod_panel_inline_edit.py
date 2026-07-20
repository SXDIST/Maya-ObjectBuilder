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
import tempfile

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


def _add_third_lod(name="gamma"):
    transform = cmds.polyCube(name=name, ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    return transform


def test_row_widgets_survive_a_no_change_refresh():
    """refresh_lod_list rebuilds only when the set of LOD nodes changed.

    ``_rebuild_lod_tree`` constructs a fresh QComboBox + QSpinBox per row.
    ``refresh_lod_list`` is only supposed to pay that cost when ``node_order`` differs
    from the last rebuild — otherwise it must update the SAME editor objects in place
    (``_update_lod_tree_rows``). Nothing short of checking object identity across two
    refresh calls can tell "updated in place" from "silently rebuilt every time";
    ``dock_refresh_cost.py`` uses a ``FakeDock`` stub that stubs out ``refresh_lod_list``
    entirely and never reaches this real method.
    """
    from a3ob.ui.dock import MayaObjectBuilderDock

    alpha, beta = build_two_lods()
    dock = MayaObjectBuilderDock()
    try:
        dock.refresh_lod_list()
        node_keys = dock.lod_row_nodes()
        _harness.check(len(node_keys) == 2,
                       "expected two rows after the first refresh, got %r" % (node_keys,))
        before = {node: dict(dock._lod_row_editors[node]) for node in node_keys}

        # Same LOD set: refresh again and the row editors must be the SAME objects.
        dock.refresh_lod_list()
        after = {node: dict(dock._lod_row_editors[node]) for node in node_keys}
        for node in node_keys:
            for key in ("combo", "spin", "item"):
                _harness.check(before[node][key] is after[node][key],
                               "%s for %r must be the SAME object across a no-change "
                               "refresh (a full rebuild would replace it)" % (key, node))

        # Now change the LOD set: adding a node must force a real rebuild of the
        # PRE-EXISTING rows too, not just append a new one.
        _add_third_lod("gamma")
        dock.refresh_lod_list()
        rebuilt_keys = dock.lod_row_nodes()
        _harness.check(len(rebuilt_keys) == 3,
                       "expected three rows after adding gamma, got %r" % (rebuilt_keys,))
        for node in node_keys:
            rebuilt_entry = dock._lod_row_editors[node]
            _harness.check(before[node]["combo"] is not rebuilt_entry["combo"],
                           "combo for %r must be REBUILT once the LOD node set changes"
                           % (node,))
    finally:
        dock.teardown()
    print("OK - row editors are reused on a no-change refresh, rebuilt when the LOD set changes")


def test_refresh_does_not_dirty_the_scene():
    """refresh_lod_list must not mark the scene modified.

    ``_apply_row_values`` blocks signals while it drives the combo/spin from scene
    state, because programmatically setting a QComboBox's index fires
    ``currentIndexChanged`` the same as a user edit would, and that handler writes an
    attribute back onto the node. A dropped ``blockSignals`` call would silently turn
    every refresh into a scene write — Maya then asks "Save changes?" after a purely
    read-only session, which is a bug this project has shipped before
    (``panels_do_not_dirty_the_scene.py``, which never touches the dock or these
    widgets).
    """
    from a3ob.ui.dock import MayaObjectBuilderDock

    alpha, beta = build_two_lods()
    dock = MayaObjectBuilderDock()
    try:
        dock.refresh_lod_list()

        path = os.path.join(tempfile.gettempdir(), "lod_panel_inline_edit_no_dirty.ma")
        cmds.file(rename=path)
        cmds.file(save=True, type="mayaAscii")
        _harness.check(not cmds.file(query=True, modified=True),
                       "scene must be clean right after saving")

        # Change beta's resolution BEHIND the dock's back (e.g. another script, undo, a
        # scene reload) so the next refresh must actually move the spin box's value —
        # a no-op setValue(same value) cannot exercise blockSignals either way. The
        # setAttr call itself dirties the scene (as any real edit would), so reset the
        # modified flag afterward to isolate what the upcoming refresh itself does.
        cmds.setAttr(beta + ".a3obResolution", 42)
        cmds.file(modified=False)

        dock.refresh_lod_list()
        entry = dock._lod_row_editors.get(dock._resolve_lod_row_node(beta))
        _harness.check(entry is not None and entry["spin"].value() == 42,
                       "refresh must still pick up the externally-changed resolution")
        _harness.check(not cmds.file(query=True, modified=True),
                       "refresh_lod_list must not mark the scene modified (a dropped "
                       "blockSignals would let the programmatic spin-box update fire "
                       "valueChanged, which writes the node back onto itself)")
    finally:
        dock.teardown()
    print("OK - refresh_lod_list does not dirty the scene")


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

    test_row_widgets_survive_a_no_change_refresh()
    test_refresh_does_not_dirty_the_scene()


main()
