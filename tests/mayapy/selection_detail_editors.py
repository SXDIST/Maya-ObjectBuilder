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

import contextlib
import os
import sys
import tempfile

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


# Task 4 pinned a `test_a_proxy_row_shows_the_blank_page` here, asserting a Proxy row
# fell through to the blank page (index 0) because it had no editor of its own yet. Task 5
# gives it one, so that assertion is now the wrong answer by design — keeping it would pit
# two tests against each other. `test_the_proxy_editor_page_follows_the_highlighted_row`
# below covers the identical scenario (a proxy row highlighted, via the same
# build_lod_with_a_proxy fixture) and asserts the new, correct index (2), so it supersedes
# the retired test rather than duplicating it under another name.


def test_a_flag_edit_undoes():
    """_undo_chunk is the whole safety argument for writing attributes directly.

    The brief chose cmds.setAttr over a new a3ob* command on the grounds that "a plain
    cmds.setAttr undoes correctly". apply_flag_edit_from_ui writes TWO attributes
    (a3obFlagComponent and a3obFlagValue) in one click, so the only assertion that pins
    _undo_chunk as load-bearing — rather than incidental — is that a SINGLE cmds.undo()
    reverts BOTH of them together. Changing only the value and checking only the value
    back would pass even with the `with _undo_chunk(...):` wrapper deleted, because Maya's
    own per-call undo record would revert that one setAttr regardless; two independently
    undoable setAttr calls still let one cmds.undo() restore the last one. This was
    witnessed directly: with the chunk removed, this test failed with
    'Ctrl+Z did not restore the component; got 'vertex'' while the value alone came back
    correctly — proving the chunk is what makes both attributes revert atomically."""
    from a3ob.ui.actions.metadata import apply_flag_edit_from_ui
    lod, flag_set = build_lod_with_a_flag(component="face", value=8, name="hidden")
    # mayapy starts with undo disabled; a user session never is. Enable it AFTER the
    # fixture so the queue holds only the edit under test, and restore whatever state
    # undo was in before this test — later tests in this file run with undo globally on
    # otherwise, accumulating an ever-growing queue.
    previous_undo_state = cmds.undoInfo(query=True, state=True)
    cmds.undoInfo(state=True, infinity=True)
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        flag_rows = [row for row in rows if row.data(_user_role())["kind"] == "Face Flag"]
        check(flag_rows, "the flag set is not listed at all")
        dock.selection_list.setCurrentItem(flag_rows[0])

        dock.flag_edit_component_combo.setCurrentIndex(1)  # Face -> Vertex
        dock.flag_edit_value_field.setValue(64)
        apply_flag_edit_from_ui()
        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 64,
              "the flag value was not written before the undo could be tested")
        check(cmds.getAttr(flag_set + ".a3obFlagComponent") == "vertex",
              "the flag component was not written before the undo could be tested")

        cmds.undo()
        check(cmds.getAttr(flag_set + ".a3obFlagValue") == 8,
              "Ctrl+Z did not restore the previous flag value; got %r"
              % cmds.getAttr(flag_set + ".a3obFlagValue"))
        check(cmds.getAttr(flag_set + ".a3obFlagComponent") == "face",
              "Ctrl+Z did not restore the component; got %r"
              % cmds.getAttr(flag_set + ".a3obFlagComponent"))
    finally:
        _release_active_dock(dock)
        cmds.undoInfo(state=previous_undo_state)


def build_lod_with_a_proxy(path="p\\weapon.p3d", index=1):
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    cmds.select(transform + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
    proxy_set = [node for node in cmds.ls(type="objectSet") or []
                 if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)][0]
    return transform, proxy_set


@contextlib.contextmanager
def _texture_root_containing(relative_path):
    """Set MayaObjectBuilder_texture_root to a temp dir holding a real file at
    relative_path, then restore whatever the optionVar held before.

    update_proxy_from_ui validates its path exactly like create_proxy_from_ui does
    (_validate_proxy_path in a3ob.ui.actions.metadata): a RELATIVE path is rejected
    outright unless it resolves to a real file under a configured texture root. The
    update tests below type a relative "p\\other.p3d" into the editor, so a real file
    has to exist there or Update warns and writes nothing — this is not a new
    restriction Task 5 introduces, it is the same rule create_proxy_from_ui already
    enforces, exercised for the first time by the update path."""
    had_root = cmds.optionVar(exists="MayaObjectBuilder_texture_root")
    previous_root = cmds.optionVar(query="MayaObjectBuilder_texture_root") if had_root else None
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, relative_path)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        open(target, "wb").close()
        cmds.optionVar(stringValue=("MayaObjectBuilder_texture_root", tmpdir))
        try:
            yield
        finally:
            if had_root:
                cmds.optionVar(stringValue=("MayaObjectBuilder_texture_root", previous_root))
            else:
                cmds.optionVar(remove="MayaObjectBuilder_texture_root")


def test_fields_report_a_proxy_path_and_index():
    _lod, proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=3)
    fields = selection_set_editable_fields(proxy_set)
    check(fields["kind"] == "Proxy", "kind is %r" % fields["kind"])
    check(fields["proxy_path"] == "p\\weapon.p3d", "path is %r" % fields["proxy_path"])
    check(fields["proxy_index"] == 3, "index is %r" % fields["proxy_index"])


def test_the_proxy_editor_page_follows_the_highlighted_row():
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=3)
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        check(proxy_rows, "the proxy set is not listed at all")
        dock.selection_list.setCurrentItem(proxy_rows[0])

        check(dock.selection_editor_stack.currentIndex() == 2,
              "the proxy editor page is not showing; index is %d"
              % dock.selection_editor_stack.currentIndex())
        path, index = dock.proxy_edit_values()
        check(path == "p\\weapon.p3d", "editor shows path %r" % path)
        check(index == 3, "editor shows index %r" % index)
    finally:
        _release_active_dock(dock)


def test_update_writes_the_new_path_to_both_halves():
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=1)
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        dock.selection_list.setCurrentItem(proxy_rows[0])

        before = len(cmds.ls(type="objectSet") or [])
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(7)
        with _texture_root_containing("p\\other.p3d"):
            update_proxy_from_ui()

        placeholder = None
        for child in cmds.listRelatives(lod, children=True, type="transform",
                                        fullPath=True) or []:
            if cmds.attributeQuery("a3obIsProxy", node=child, exists=True):
                placeholder = child
        check(placeholder is not None, "the placeholder vanished")
        check(cmds.getAttr(placeholder + ".a3obProxyPath") == "p\\other.p3d",
              "the placeholder still points at %r"
              % cmds.getAttr(placeholder + ".a3obProxyPath"))
        check(cmds.getAttr(placeholder + ".a3obProxyIndex") == 7,
              "the placeholder index is %r" % cmds.getAttr(placeholder + ".a3obProxyIndex"))

        proxy_sets = [node for node in cmds.ls(type="objectSet") or []
                      if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]
        check(len(proxy_sets) == 1, "expected one proxy set, got %r" % proxy_sets)
        check(cmds.getAttr(proxy_sets[0] + ".a3obSelectionName") == "proxy:p\\other.p3d.7",
              "the set names %r" % cmds.getAttr(proxy_sets[0] + ".a3obSelectionName"))
        check(before == len(cmds.ls(type="objectSet") or []),
              "the update left an orphan set behind")
    finally:
        _release_active_dock(dock)


def test_update_restores_the_previous_selection():
    """a3obUpdateProxy acts on the SELECTION, so the action must select the set and put the
    user's selection back — otherwise clicking Update silently changes what is selected."""
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    lod, _proxy_set = build_lod_with_a_proxy()
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        dock.selection_list.setCurrentItem(proxy_rows[0])

        cmds.select(lod, replace=True)
        before = cmds.ls(selection=True, long=True) or []
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(2)
        with _texture_root_containing("p\\other.p3d"):
            update_proxy_from_ui()
        after = cmds.ls(selection=True, long=True) or []
        check(before == after,
              "the selection changed from %r to %r across an Update" % (before, after))
    finally:
        _release_active_dock(dock)


def test_update_restores_selection_when_the_command_fails():
    """The `finally` in update_proxy_from_ui must run even when a3obUpdateProxy itself
    raises, not only on the happy path that test_update_restores_the_previous_selection
    covers. Today (before this test) the whole finally block could be deleted and every
    other test in this file would still pass, because none of them make the command fail.

    cmds.a3obUpdateProxy is swapped for a raising stand-in for the duration of the call:
    that is the only reliable way to make the real command fail here — a3obUpdateProxy's
    doIt has no path that raises a Python exception for a validly-selected proxy set (a
    missing/invalid selection is rejected by update_proxy_from_ui's own guards before the
    command ever runs, and Maya's own doIt reports its "not a proxy" case via
    MGlobal.displayError, which does not raise)."""
    from a3ob.ui.actions import metadata as metadata_actions
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=1)
    dock = _built_active_dock()
    real_command = cmds.a3obUpdateProxy

    def _raiser(*_args, **_kwargs):
        raise RuntimeError("simulated a3obUpdateProxy failure")

    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        check(proxy_rows, "the proxy set is not listed at all")
        dock.selection_list.setCurrentItem(proxy_rows[0])

        cmds.select(lod, replace=True)
        before = cmds.ls(selection=True, long=True) or []
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(2)
        cmds.a3obUpdateProxy = _raiser
        raised = False
        with _texture_root_containing("p\\other.p3d"):
            try:
                metadata_actions.update_proxy_from_ui()
            except RuntimeError:
                raised = True
        check(raised, "the simulated command failure did not propagate out of "
                      "update_proxy_from_ui — the test setup is not exercising the "
                      "failure path it claims to")
        after = cmds.ls(selection=True, long=True) or []
        check(before == after,
              "a failing Update left the selection at %r instead of restoring %r"
              % (after, before))
    finally:
        cmds.a3obUpdateProxy = real_command
        _release_active_dock(dock)


def test_update_restores_an_empty_selection():
    """The `else: cmds.select(clear=True)` half of the restore, on its own — the other
    restore test starts from a non-empty selection and never exercises this branch."""
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    lod, _proxy_set = build_lod_with_a_proxy()
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        check(proxy_rows, "the proxy set is not listed at all")
        dock.selection_list.setCurrentItem(proxy_rows[0])

        cmds.select(clear=True)
        check(not cmds.ls(selection=True), "fixture setup left something selected")
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(2)
        with _texture_root_containing("p\\other.p3d"):
            update_proxy_from_ui()
        after = cmds.ls(selection=True, long=True) or []
        check(not after, "an empty starting selection did not restore to empty, got %r" % after)
    finally:
        _release_active_dock(dock)


def test_undo_after_update_resurrects_no_orphan_set():
    """The spec's sharpest test. a3obProxy and a3obUpdateProxy are non-undoable precisely
    because MFnSet.create() never enters the undo queue: when they WERE undoable, Ctrl+Z
    rolled back the DAG side while the sets stayed, leaving orphan a3ob_proxy_* behind.
    Update runs through the same commands, so it inherits the same hazard."""
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=1)
    dock = _built_active_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        dock.selection_list.setCurrentItem(proxy_rows[0])

        before = len(cmds.ls(type="objectSet") or [])
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(7)
        with _texture_root_containing("p\\other.p3d"):
            update_proxy_from_ui()
        cmds.undo()

        after = len(cmds.ls(type="objectSet") or [])
        check(before == after,
              "Ctrl+Z after Update changed the set count from %d to %d — an orphan was "
              "resurrected" % (before, after))
        proxy_sets = [node for node in cmds.ls(type="objectSet") or []
                      if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]
        check(len(proxy_sets) == 1,
              "after undo there are %d proxy sets, expected 1: %r"
              % (len(proxy_sets), proxy_sets))
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
                 test_a_flag_edit_undoes,
                 test_fields_report_a_proxy_path_and_index,
                 test_the_proxy_editor_page_follows_the_highlighted_row,
                 test_update_writes_the_new_path_to_both_halves,
                 test_update_restores_the_previous_selection,
                 test_update_restores_selection_when_the_command_fails,
                 test_update_restores_an_empty_selection,
                 test_undo_after_update_resurrects_no_orphan_set):
        test()
        print("ok:", test.__name__, flush=True)
    print("SELECTION DETAIL EDITORS: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
