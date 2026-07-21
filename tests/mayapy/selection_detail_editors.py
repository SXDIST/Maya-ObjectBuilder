"""The Selections details area shows an editor matching the highlighted row's kind (mayapy).

Proxies and flags used to have create-only panels: nothing in the dock displayed an existing
one, and nothing could change it. The only repair for a wrong flag value was delete and
recreate. The details area below the list now switches to an editor for the highlighted
row's kind, and to a plain summary for an ordinary selection.

Constructing real Qt widgets under mayapy needs a genuine QApplication in place *before*
maya.standalone.initialize() runs — Maya's standalone bring-up creates a bare
QGuiApplication, and building a QWidget against that segfaults the process with no Python
traceback at all. Creating the QApplication first makes Maya's init reuse it instead.

Run:  mayapy.exe tests/mayapy/selection_detail_editors.py
"""

import sys

from PySide6 import QtWidgets

_qt_app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)

import _harness
# Shared with Task 5's proxy-editor tests: a real dock plus action functions that reach
# it through _active_qt_dock(). They live in _harness so the teardown they do stays in
# ONE place — a second copy would be one dock_teardown fix away from being wrong.
from _harness import _built_active_dock, _release_active_dock

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()  # a3obSetFlag / a3obProxy do not exist until the plugin is loaded

from a3ob.ui.scene.selections import selection_set_editable_fields  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_lod_with_a_flag(component="face", value=8, name="hidden"):
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    components = ".f[0:1]" if component == "face" else ".vtx[0:3]"
    cmds.select(transform + components, replace=True)
    cmds.a3obSetFlag(component=component, value=value, name=name)
    flag_set = [node for node in cmds.ls(type="objectSet") or []
                if cmds.attributeQuery("a3obFlagComponent", node=node, exists=True)][0]
    return transform, flag_set


def test_fields_report_a_flag_set():
    _lod, flag_set = build_lod_with_a_flag(component="face", value=8)
    fields = selection_set_editable_fields(flag_set)
    check(fields["kind"] == "Face Flag", "kind is %r" % fields["kind"])
    check(fields["flag_component"] == "face", "component is %r" % fields["flag_component"])
    check(fields["flag_value"] == 8, "value is %r" % fields["flag_value"])


def test_fields_report_an_ordinary_selection():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    set_node = cmds.sets(transform + ".f[0]", name="a3ob_SEL_camo")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "camo", type="string")

    fields = selection_set_editable_fields(set_node)
    check(fields["kind"] == "Selection", "kind is %r" % fields["kind"])
    check(fields["flag_component"] == "", "an ordinary selection reported a flag component")
    check(fields["flag_value"] == 0, "an ordinary selection reported a flag value")


def test_reading_the_fields_does_not_dirty_the_scene():
    _lod, flag_set = build_lod_with_a_flag()
    cmds.file(modified=False)
    selection_set_editable_fields(flag_set)
    check(not cmds.file(query=True, modified=True),
          "reading the editable fields dirtied the scene")


def test_a_deleted_set_reports_an_empty_kind_instead_of_raising():
    """The list can outlive its sets by one refresh; the details area must not raise."""
    _lod, flag_set = build_lod_with_a_flag()
    cmds.delete(flag_set)
    fields = selection_set_editable_fields(flag_set)
    check(fields["kind"] == "", "a deleted set reported kind %r" % fields["kind"])


def test_the_editor_page_follows_the_highlighted_row():
    lod, flag_set = build_lod_with_a_flag(component="vertex", value=3, name="soft")
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()

        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        flag_rows = [row for row in rows
                     if row.data(_user_role())["kind"] == "Vertex Flag"]
        check(flag_rows, "the flag set is not listed at all")
        dock.selection_list.setCurrentItem(flag_rows[0])

        component, value = dock.flag_edit_values()
        check(component == "vertex", "editor shows component %r" % component)
        check(value == 3, "editor shows value %r" % value)
        check(dock.selection_editor_stack.currentIndex() == 1,
              "the flag editor page is not showing; index is %d"
              % dock.selection_editor_stack.currentIndex())
    finally:
        _release_active_dock(dock)


def test_an_ordinary_selection_shows_no_editor():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    set_node = cmds.sets(transform + ".f[0]", name="a3ob_SEL_camo")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "camo", type="string")

    dock = _built_active_dock()
    try:
        cmds.select(transform, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        check(rows, "the selection set is not listed at all")
        dock.selection_list.setCurrentItem(rows[0])
        check(dock.selection_editor_stack.currentIndex() == 0,
              "an ordinary selection showed an editor page (index %d)"
              % dock.selection_editor_stack.currentIndex())
    finally:
        _release_active_dock(dock)


def test_applying_a_flag_edit_writes_through_and_creates_no_set():
    from a3ob.ui.actions.metadata import apply_flag_edit_from_ui
    lod, flag_set = build_lod_with_a_flag(component="face", value=8, name="hidden")
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        flag_rows = [row for row in rows if row.data(_user_role())["kind"] == "Face Flag"]
        dock.selection_list.setCurrentItem(flag_rows[0])

        before = len(cmds.ls(type="objectSet") or [])
        dock.flag_edit_value_field.setValue(64)
        apply_flag_edit_from_ui()

        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 64,
              "the flag value was not written: %r" % cmds.getAttr(flag_set + ".a3obFlagValue"))
        after = len(cmds.ls(type="objectSet") or [])
        check(before == after, "editing a flag changed the set count from %d to %d"
                               % (before, after))
    finally:
        _release_active_dock(dock)


def test_a_zero_flag_value_warns_and_writes_nothing():
    """The zero guard must be a real gate, not just a warning printed before the write.

    A flag set whose value is 0 exports nothing (export/taggs/data.py), so letting a 0
    through would silently drop the flag from the P3D while the panel still lists it."""
    from a3ob.ui.actions.metadata import apply_flag_edit_from_ui
    lod, flag_set = build_lod_with_a_flag(component="face", value=8, name="hidden")
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        flag_rows = [row for row in rows if row.data(_user_role())["kind"] == "Face Flag"]
        check(flag_rows, "the flag set is not listed at all")
        dock.selection_list.setCurrentItem(flag_rows[0])

        dock.flag_edit_value_field.setValue(0)
        apply_flag_edit_from_ui()

        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 8,
              "a zero flag value was written through: %r"
              % cmds.getAttr(flag_set + ".a3obFlagValue"))
    finally:
        _release_active_dock(dock)


def test_a_proxy_row_shows_the_blank_page():
    """Pinned so Task 5's proxy editor page is a visible change, not a silent one.

    A Proxy row has no editor today: it falls through show_selection_editor's flag
    branch to page 0, the same blank page an ordinary Selection gets."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    cmds.select(transform + ".f[0:1]", replace=True)
    cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=True, update=True)

    dock = _built_active_dock()
    try:
        cmds.select(transform, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        check(proxy_rows, "the proxy set is not listed at all; rows are %r"
                          % [row.data(_user_role())["kind"] for row in rows])
        dock.selection_list.setCurrentItem(proxy_rows[0])
        check(dock.selection_editor_stack.currentIndex() == 0,
              "a proxy row showed an editor page (index %d)"
              % dock.selection_editor_stack.currentIndex())
    finally:
        _release_active_dock(dock)


def test_a_flag_edit_undoes():
    """_undo_chunk is the whole safety argument for writing attributes directly.

    The brief chose cmds.setAttr over a new a3ob* command on the grounds that "a plain
    cmds.setAttr undoes correctly". Nothing tested that claim, so this does."""
    from a3ob.ui.actions.metadata import apply_flag_edit_from_ui
    lod, flag_set = build_lod_with_a_flag(component="face", value=8, name="hidden")
    # mayapy starts with undo disabled; a user session never is. Enable it AFTER the
    # fixture so the queue holds only the edit under test.
    cmds.undoInfo(state=True, infinity=True)
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        flag_rows = [row for row in rows if row.data(_user_role())["kind"] == "Face Flag"]
        check(flag_rows, "the flag set is not listed at all")
        dock.selection_list.setCurrentItem(flag_rows[0])

        dock.flag_edit_value_field.setValue(64)
        apply_flag_edit_from_ui()
        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 64,
              "the flag value was not written before the undo could be tested")

        cmds.undo()
        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 8,
              "Ctrl+Z did not restore the previous flag value; got %r"
              % cmds.getAttr(flag_set + ".a3obFlagValue"))
    finally:
        _release_active_dock(dock)


def _user_role():
    from a3ob.ui._qt import qt_core
    return qt_core.Qt.UserRole


def main():
    for test in (test_fields_report_a_flag_set,
                 test_fields_report_an_ordinary_selection,
                 test_reading_the_fields_does_not_dirty_the_scene,
                 test_a_deleted_set_reports_an_empty_kind_instead_of_raising,
                 test_the_editor_page_follows_the_highlighted_row,
                 test_an_ordinary_selection_shows_no_editor,
                 test_applying_a_flag_edit_writes_through_and_creates_no_set,
                 test_a_zero_flag_value_warns_and_writes_nothing,
                 test_a_proxy_row_shows_the_blank_page,
                 test_a_flag_edit_undoes):
        test()
        print("ok:", test.__name__, flush=True)
    print("SELECTION DETAIL EDITORS: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
