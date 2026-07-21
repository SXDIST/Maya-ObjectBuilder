# Phase 3b — Selections absorbs Proxies and Flags

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the Proxies and Flags panels; the Selections panel — which already lists both
kinds — gains their creation entry points and, for the first time, the ability to edit an
existing proxy or flag instead of deleting and rebuilding it.

**Architecture:** The Selections list already shows every Object Builder set with a `kind`
("Selection" / "Proxy" / "Vertex Flag" / "Face Flag") from `_set_kind`. Creation moves behind a
menu on the existing **Create** button. Editing appears in the details area below the list, which
becomes a `QStackedWidget`: a summary label for ordinary selections, a flag editor for flag rows,
a proxy editor for proxy rows. One command-level defect is fixed first, because the proxy editor
cannot be correct on top of it.

**Tech Stack:** Maya 2027, Python 3, `maya.cmds` + Maya API 2.0, PySide6 (`a3ob.ui._qt`).

## Global Constraints

These apply to every task. They are not repeated per task.

- **Never run `mayapy tests/golden.py capture`.** Only `verify`. `capture` overwrites the byte
  baseline and makes the gate vacuous.
- **Never run `python tests/run_all.py`** as an implementer. It stalls agents; the controller runs
  the full suite between tasks. Run individual test files instead.
- **Run every command in the FOREGROUND.** No background invocations.
- The byte contract must not move: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
- The `a3ob*` attribute schema is a hard contract — 33 long+short pairs in
  `scripts/a3ob/mayabridge/attributes.py`, pinned by `tests/python/test_attr_schema.py`. This
  phase adds no attribute and renames none.
- Registered command names and their flags are a hard contract. `a3obUpdateProxy` keeps its name
  and its `-p` / `-i` flags. Task 1 changes only what the command *does*.
- **Panels must be silent reads.** Anything a panel calls during refresh must not warn and must
  not write. `tests/mayapy/dock_panel_sync.py` and `tests/mayapy/panels_do_not_dirty_the_scene.py`
  guard this; both must stay green.
- **`a3obProxy` and `a3obUpdateProxy` are deliberately NON-undoable** and wrap their bodies in
  `undo_chunk()`. Making them undoable is what previously left orphan `a3ob_proxy_*` sets behind,
  because `MFnSet.create()` never enters the undo queue. Do not add `self.modifier` to either.
- **A real `QWidget` under mayapy segfaults** unless a `QApplication` exists *before*
  `maya.standalone.initialize()`. Any test that builds a real dock must copy the header order of
  `tests/mayapy/lod_panel_inline_edit.py` exactly.
- **Line endings:** this repo has no `.gitattributes` and genuinely mixed endings. Before each
  commit compare `git diff --shortstat` against `git diff --shortstat --ignore-cr-at-eol`; the
  numbers must agree. Edit files in place, never rewrite them wholesale.
- `mayapy` is `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe`. Each mayapy test runs in its
  own process — `maya.standalone` cannot be initialized twice.

## File structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `scripts/a3ob/mayabridge/commands/helpers/sets.py` | gains `sync_proxy_pair` — updating one half of a proxy repoints the other |
| `scripts/a3ob/mayabridge/commands/update_proxy.py` | calls it, so `a3obUpdateProxy` leaves a consistent pair |
| `scripts/a3ob/ui/dialogs.py` | **new leaf** — the Proxy and Flag creation dialogs. Qt, no imports from `a3ob.ui.actions` |
| `scripts/a3ob/ui/scene/selections.py` | gains `selection_set_editable_fields` — a silent read describing what the details area should show |
| `scripts/a3ob/ui/panels/selections.py` | Create menu; details area becomes a stack with flag and proxy editors |
| `scripts/a3ob/ui/actions/metadata.py` | `create_proxy_from_ui` / `apply_flag_from_ui` read the dialogs, not dock fields; gains `update_proxy_from_ui`, `apply_flag_edit_from_ui` |
| `scripts/a3ob/ui/panels/metadata.py` | **deleted** — both its sections are gone |
| `scripts/a3ob/ui/dock.py` | loses the Flags and Proxies panel entries and the six widget attributes they owned |

Six tasks. Task 1 is command-level and Qt-free. Tasks 2–3 add creation, tasks 4–5 add editing,
task 6 removes the old panels once nothing depends on them.

---

### Task 1: `a3obUpdateProxy` updates the whole proxy pair

A proxy is two nodes keyed by the same string, `proxy:PATH.INDEX` (`proxy_selection_name` in
`commands/helpers/primitives.py:73`):

- a placeholder **transform** under the LOD, carrying `a3obProxyPath`, `a3obProxyIndex` and
  `a3obProxySelection`;
- a **selection set** named `a3ob_proxy_...`, carrying `a3obSelectionName` and
  `a3obIsProxySelection`.

`a3obProxy` writes both consistently. `a3obUpdateProxy` branches on which one is selected and
updates only that one: `update_proxy_placeholder` never touches the set, and
`update_proxy_selection_set` never touches the placeholder. So changing a path today leaves the
pair disagreeing, and `a3obValidate` then reports *"proxy placeholder has no matching selection
set"* (`commands/validate.py:146`). The command has no UI caller, which is why this has never
been hit. Task 5 gives it one — so it must be correct first.

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/helpers/sets.py` (add `sync_proxy_pair`, export it)
- Modify: `scripts/a3ob/mayabridge/commands/update_proxy.py:44-50`
- Create: `tests/mayapy/proxy_update_keeps_pair.py`

**Interfaces:**
- Produces: `sync_proxy_pair(node, path, index)` in
  `a3ob.mayabridge.commands.helpers.sets` — given either half of a proxy pair, updates both.
  Returns `None`. Safe when the counterpart does not exist.
- Consumes: existing `update_proxy_placeholder(proxy, path, index)`,
  `update_proxy_selection_set(set_obj, path, index)`, `proxy_selection_name(path, index)`,
  `proxy_placeholder(lod, selection_name)`, `proxy_selection_set_exists(selection_name)`.

- [ ] **Step 1: Read the existing helpers before changing them**

Read `scripts/a3ob/mayabridge/commands/helpers/sets.py` lines 230-270 and
`scripts/a3ob/mayabridge/commands/proxy.py` lines 33-70. Note two rules stated in those
docstrings that constrain your implementation:

1. Every write here goes through `cmds` (`rename` / `addAttr` / `setAttr`), never `attr.set_*` or
   an `MDagModifier`. Both commands are non-undoable and rely on `undo_chunk()` plus `cmds`' own
   undo records. Mixing the two makes a rename undo while the metadata silently stays changed.
2. `a3obProxy` finds an existing placeholder with `proxy_placeholder(lod, selection_name)`, keyed
   on the **old** selection name.

- [ ] **Step 2: Write the failing test**

Create `tests/mayapy/proxy_update_keeps_pair.py`:

```python
"""a3obUpdateProxy must leave the placeholder and its selection set agreeing (mayapy).

A proxy is two nodes keyed by the same string, proxy:PATH.INDEX: a placeholder transform
under the LOD and an objectSet holding its components. a3obProxy writes both. Before this
test, a3obUpdateProxy updated only whichever half happened to be selected, so correcting a
path renamed the set while the placeholder still pointed at the old proxy — a state
a3obValidate reports as "proxy placeholder has no matching selection set".

Run:  mayapy.exe tests/mayapy/proxy_update_keeps_pair.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_proxy(path="p\\weapon.p3d", index=1):
    """A LOD with a mesh, and a proxy built from two of its faces."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    cmds.select(transform + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
    return transform


def placeholder_under(lod):
    for child in cmds.listRelatives(lod, children=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery("a3obIsProxy", node=child, exists=True):
            return child
    return None


def proxy_sets():
    return [node for node in cmds.ls(type="objectSet") or []
            if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]


def pair_state(lod):
    """(placeholder path, placeholder index, placeholder's selection name, set's name)."""
    placeholder = placeholder_under(lod)
    check(placeholder is not None, "no proxy placeholder was created")
    sets = proxy_sets()
    check(len(sets) == 1, "expected exactly one proxy selection set, got %r" % sets)
    return (cmds.getAttr(placeholder + ".a3obProxyPath"),
            cmds.getAttr(placeholder + ".a3obProxyIndex"),
            cmds.getAttr(placeholder + ".a3obProxySelection"),
            cmds.getAttr(sets[0] + ".a3obSelectionName"))


def test_update_via_the_placeholder_also_renames_the_set():
    lod = build_proxy()
    cmds.select(placeholder_under(lod), replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    path, index, placeholder_selection, set_selection = pair_state(lod)
    check(path == "p\\other.p3d", "placeholder path not updated: %r" % path)
    check(index == 4, "placeholder index not updated: %r" % index)
    check(placeholder_selection == "proxy:p\\other.p3d.4",
          "placeholder selection name not updated: %r" % placeholder_selection)
    check(set_selection == placeholder_selection,
          "the set still names %r while the placeholder names %r"
          % (set_selection, placeholder_selection))


def test_update_via_the_set_also_repoints_the_placeholder():
    lod = build_proxy()
    cmds.select(proxy_sets()[0], replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    path, index, placeholder_selection, set_selection = pair_state(lod)
    check(set_selection == "proxy:p\\other.p3d.4",
          "set selection name not updated: %r" % set_selection)
    check(path == "p\\other.p3d",
          "the placeholder still points at %r after updating through the set" % path)
    check(index == 4, "placeholder index not updated: %r" % index)
    check(placeholder_selection == set_selection,
          "the placeholder names %r while the set names %r"
          % (placeholder_selection, set_selection))


def test_update_creates_no_extra_set_and_leaves_no_orphan():
    lod = build_proxy()
    before = len(cmds.ls(type="objectSet") or [])
    cmds.select(placeholder_under(lod), replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)
    after = len(cmds.ls(type="objectSet") or [])
    check(before == after, "set count changed from %d to %d — an orphan was left behind"
                           % (before, after))


def test_a_placeholder_with_no_set_still_updates():
    """fromSelection=False builds a placeholder alone. Syncing must not require a set."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.select(transform, replace=True)
    cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=False, update=True)

    placeholder = placeholder_under(transform)
    check(placeholder is not None, "no placeholder was created")
    check(proxy_sets() == [], "fromSelection=False should create no set")

    cmds.select(placeholder, replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=2)
    check(cmds.getAttr(placeholder + ".a3obProxyPath") == "p\\other.p3d",
          "a placeholder without a set failed to update")


def main():
    for test in (test_update_via_the_placeholder_also_renames_the_set,
                 test_update_via_the_set_also_repoints_the_placeholder,
                 test_update_creates_no_extra_set_and_leaves_no_orphan,
                 test_a_placeholder_with_no_set_still_updates):
        test()
        print("ok:", test.__name__, flush=True)
    print("PROXY UPDATE PAIR: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 3: Run it and WITNESS the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_update_keeps_pair.py
```

Expected: `FAIL:` naming a disagreement between the two halves — the first two tests fail, the
last two pass. **Paste the actual failure text into your report.** A green here means the
fixture is wrong, not that the bug is absent.

- [ ] **Step 4: Add `sync_proxy_pair` to `helpers/sets.py`**

Insert after `update_proxy_placeholder` (which ends at line 268). Every write goes through the
two existing updaters, so the cmds-only rule is preserved by construction:

> **SUPERSEDED — do not re-implement the lookup below.** `proxy_selection_name` encodes no
> LOD identity, so `proxy:PATH.INDEX` is carried by several placeholders and several sets on
> any multi-LOD model. The scene-wide first-match helpers sketched here therefore updated the
> selected node and then retagged a *different* LOD's half. The shipped code scopes the
> counterpart to ONE LOD (`proxy_placeholder(lod, ...)` / `_proxy_selection_set_in_lod`), and
> resolves a set's LOD from its members via `lod_for_set` — a set with no surviving members
> resolves to no LOD and therefore to no counterpart. It also iterates `MItDependencyNodes`
> instead of `cmds.ls("*.attr")`, which does not recurse into namespaces (measured: a
> `ref:`-namespaced set is invisible to the pattern and visible to the iterator). See
> `tests/mayapy/proxy_update_keeps_pair.py`.

```python
def sync_proxy_pair(node, path, index):
    """Update BOTH halves of a proxy from either one of them.

    A proxy is a placeholder transform plus a selection set, keyed by the same
    ``proxy:PATH.INDEX`` string. ``a3obProxy`` writes them together; the two updaters below
    each write only one. Updating one alone leaves the pair disagreeing, which
    ``a3obValidate`` reports as "proxy placeholder has no matching selection set" — so the
    only correct edit is the pair, and this is the single place that knows that.

    Either half may legitimately be missing: ``a3obProxy -fromSelection 0`` builds a
    placeholder with no set at all. A missing counterpart is not an error."""
    old_selection_name = ""
    if node.hasFn(om.MFn.kSet):
        old_selection_name = attr.get_string(node, A.SELECTION_NAME)
    else:
        old_selection_name = attr.get_string(node, A.PROXY_SELECTION)

    placeholder = NULL
    set_obj = NULL
    if node.hasFn(om.MFn.kSet):
        set_obj = node
        placeholder = _proxy_placeholder_by_selection(old_selection_name)
    else:
        placeholder = node
        set_obj = _proxy_selection_set_by_name(old_selection_name)

    if not placeholder.isNull():
        update_proxy_placeholder(placeholder, path, index)
    if not set_obj.isNull():
        update_proxy_selection_set(set_obj, path, index)


def _proxy_placeholder_by_selection(selection_name):
    """The proxy placeholder transform whose a3obProxySelection equals selection_name.

    Searched scene-wide rather than under one LOD: the caller holds a selection SET, and a
    set does not know which LOD it belongs to without walking its members — which is both
    slower and wrong for a set whose members have been deleted."""
    if not selection_name:
        return NULL
    for node_name in cmds.ls("*." + A.PROXY_SELECTION[0], objectsOnly=True, long=True) or []:
        if cmds.getAttr(node_name + "." + A.PROXY_SELECTION[0]) == selection_name:
            found = om.MSelectionList()
            found.add(node_name)
            return found.getDependNode(0)
    return NULL


def _proxy_selection_set_by_name(selection_name):
    """The proxy selection set whose a3obSelectionName equals selection_name."""
    if not selection_name:
        return NULL
    for node_name in cmds.ls("*." + A.SELECTION_NAME[0], objectsOnly=True) or []:
        if not cmds.objectType(node_name, isType="objectSet"):
            continue
        if cmds.getAttr(node_name + "." + A.SELECTION_NAME[0]) == selection_name:
            found = om.MSelectionList()
            found.add(node_name)
            return found.getDependNode(0)
    return NULL
```

Add `"sync_proxy_pair"` to the module's `__all__` if it has one; if the module exports by star
import without `__all__`, no change is needed. Check first — do not add an `__all__` that did
not exist, because that would silently stop exporting everything else.

- [ ] **Step 5: Call it from the command**

In `scripts/a3ob/mayabridge/commands/update_proxy.py`, replace lines 44-50 with:

```python
            if attr.get_bool_any(node, A.IS_PROXY, A.IS_PROXY_ALT_SHORT):
                sync_proxy_pair(node, path, index)
                return
            if attr.get_bool(node, A.IS_PROXY_SELECTION) or node.hasFn(om.MFn.kSet):
                sync_proxy_pair(node, path, index)
                return
            om.MGlobal.displayError("a3obUpdateProxy: selected node is not a proxy placeholder or proxy selection set")
```

The two branches now do the same thing, but keep them separate: they are the command's
*validation* that the selected node is one of the two accepted kinds. Collapsing them into a
single `if` would accept any node at all and silently no-op on a plain mesh.

- [ ] **Step 6: Run the test and verify it passes**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_update_keeps_pair.py
```

Expected: four `ok:` lines then `PROXY UPDATE PAIR: PASS`.

- [ ] **Step 7: Verify the neighbours still pass**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_undo.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

`command_undo.py` matters most: it covers the orphan-set rule this command exists under. The
golden run must print real per-fixture byte lines — if it prints `SKIP`, the junctions are
missing and the gate is proving nothing; stop and report that rather than continuing.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/mayabridge/commands/helpers/sets.py \
        scripts/a3ob/mayabridge/commands/update_proxy.py \
        tests/mayapy/proxy_update_keeps_pair.py
git commit -m "fix: a3obUpdateProxy updates both halves of a proxy pair"
```

---

### Task 2: the Create button becomes a menu, with a Proxy dialog

The Proxies panel is a create-only form that displays nothing: a path picker, an index, a
"Create from selected components" checkbox and a button. Its capability moves behind the
Selections panel's existing **Create** button, which becomes a small menu.

The checkbox is **dropped**. It selects between two modes the current selection already
determines: with components selected the proxy is built from them, with nothing selected a
standalone placeholder is created. The dialog states which of the two it will do. `a3obProxy
-fromSelection` keeps both behaviours for scripted callers — only the UI control goes.

**Files:**
- Create: `scripts/a3ob/ui/dialogs.py`
- Modify: `scripts/a3ob/ui/panels/selections.py:31-39` (the Create button)
- Modify: `scripts/a3ob/ui/actions/metadata.py:75-93` (`create_proxy_from_ui`)
- Create: `tests/mayapy/proxy_creation_mode.py`

**Interfaces:**
- Produces: `proxy_creation_mode()` in `a3ob.ui.dialogs` → `"components"` or `"standalone"`.
- Produces: `proxy_dialog(dock)` in `a3ob.ui.dialogs` → `(path, index)` on accept, `None` on
  cancel.
- Consumes: `dock._path_picker(label, caption, mode, file_filter, recent_key=None)` from
  `a3ob.ui.dock` — returns a container widget whose line edit is `container._line_edit`; usable
  outside the dock. Reusing it is what preserves the recent-paths dropdown.
- Consumes: `_validate_proxy_path(path)` from `a3ob.ui.actions.metadata`, unchanged.

- [ ] **Step 1: Write the failing test for the mode helper**

Create `tests/mayapy/proxy_creation_mode.py`:

```python
"""The proxy dialog reports which of its two modes the current selection implies (mayapy).

The old panel had a "Create from selected components" checkbox, which let the user ask for a
mode the selection could not deliver. The selection already decides: components selected ->
build the proxy from them; nothing selected -> a standalone placeholder. The dialog states
which, rather than offering a control.

Run:  mayapy.exe tests/mayapy/proxy_creation_mode.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.dialogs import proxy_creation_mode  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_components_selected():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".f[0:1]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "faces selected should give 'components', got %r" % mode)


def test_vertices_selected():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".vtx[0:3]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "vertices selected should give 'components', got %r" % mode)


def test_nothing_selected():
    cmds.file(new=True, force=True)
    cmds.polyCube(name="body", ch=False)
    cmds.select(clear=True)
    mode = proxy_creation_mode()
    check(mode == "standalone", "empty selection should give 'standalone', got %r" % mode)


def test_whole_object_selected_is_standalone():
    """A whole transform is not a component selection: the proxy has no faces to attach to."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform, replace=True)
    mode = proxy_creation_mode()
    check(mode == "standalone", "a whole object should give 'standalone', got %r" % mode)


def test_reading_the_mode_does_not_dirty_the_scene():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".f[0]", replace=True)
    cmds.file(modified=False)
    proxy_creation_mode()
    check(not cmds.file(query=True, modified=True),
          "reading the proxy creation mode dirtied the scene")


def main():
    for test in (test_components_selected, test_vertices_selected, test_nothing_selected,
                 test_whole_object_selected_is_standalone,
                 test_reading_the_mode_does_not_dirty_the_scene):
        test()
        print("ok:", test.__name__, flush=True)
    print("PROXY CREATION MODE: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 2: Run it and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_creation_mode.py
```

Expected: `ModuleNotFoundError: No module named 'a3ob.ui.dialogs'`. Record it.

- [ ] **Step 3: Create `scripts/a3ob/ui/dialogs.py`**

This is a **leaf**: it imports Qt and `maya.cmds`, and must NOT import from `a3ob.ui.actions`.
Every module in `a3ob.ui.actions` does `from a3ob.ui.entry import *`, so an actions import here
would close the `actions ↔ entry ↔ dock` cycle that `entry._build_qt_dock`'s lazy import exists
to break.

```python
"""Modal dialogs for creating proxies and flags.

A leaf module: Qt and maya.cmds only. It must never import from a3ob.ui.actions — every
module there star-imports a3ob.ui.entry, and importing back into it would close the
actions/entry/dock cycle that entry._build_qt_dock's lazy import exists to break.
"""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403


def proxy_creation_mode():
    """"components" when mesh components are selected, otherwise "standalone".

    A silent read: it inspects the selection and writes nothing. The old panel offered this
    as a checkbox, which allowed asking for a mode the selection could not deliver."""
    for item in cmds.ls(selection=True, long=True) or []:
        if ".f[" in item or ".vtx[" in item:
            return "components"
    return "standalone"


_MODE_TEXT = {
    "components": "Will build the proxy from the selected components.",
    "standalone": "Nothing is selected — will create a standalone proxy placeholder.",
}


def proxy_dialog(dock):
    """Ask for a proxy path and index. Returns (path, index), or None if cancelled.

    The path picker is the dock's own _path_picker, so the recent-paths dropdown behaves
    exactly as it did in the retired Proxies panel."""
    dialog = qt_widgets.QDialog(dock)
    dialog.setWindowTitle("Create Proxy")
    layout = qt_widgets.QVBoxLayout(dialog)

    form_holder = qt_widgets.QWidget()
    form = qt_widgets.QFormLayout(form_holder)
    form.setContentsMargins(0, 0, 0, 0)
    path_field = dock._path_picker("Proxy path", "Select proxy P3D", 1,
                                   "Arma P3D (*.p3d)", recent_key="proxy")
    index_field = qt_widgets.QSpinBox()
    index_field.setRange(0, 2147483647)
    index_field.setValue(1)
    form.addRow("Path", path_field)
    form.addRow("Index", index_field)
    layout.addWidget(form_holder)

    mode_label = qt_widgets.QLabel(_MODE_TEXT[proxy_creation_mode()])
    mode_label.setWordWrap(True)
    layout.addWidget(mode_label)

    # The mode follows the viewport selection while the dialog is open, so the stated
    # behaviour never goes stale under the user. parent= ties the job's lifetime to the
    # dialog: without it the job outlives the widget and fires on a deleted label.
    job = cmds.scriptJob(event=["SelectionChanged",
                                lambda: mode_label.setText(_MODE_TEXT[proxy_creation_mode()])],
                         parent=dialog.objectName() or None, protected=False)

    buttons = qt_widgets.QDialogButtonBox(
        qt_widgets.QDialogButtonBox.Ok | qt_widgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    try:
        accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    finally:
        if cmds.scriptJob(exists=job):
            cmds.scriptJob(kill=job, force=True)

    if not accepted:
        return None
    return path_field._line_edit.text().strip(), index_field.value()
```

- [ ] **Step 4: Run the test and verify it passes**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_creation_mode.py
```

Expected: five `ok:` lines then `PROXY CREATION MODE: PASS`. Only `proxy_creation_mode` is
exercised headlessly — `proxy_dialog` builds real widgets and is checked by hand in Task 6.

- [ ] **Step 5: Rewrite `create_proxy_from_ui` to use the dialog**

In `scripts/a3ob/ui/actions/metadata.py`, replace the body of `create_proxy_from_ui`
(lines 75-93) with:

```python
def create_proxy_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    from a3ob.ui.dialogs import proxy_dialog, proxy_creation_mode
    answer = proxy_dialog(dock)
    if answer is None:
        return
    path, index = answer
    if not path:
        cmds.warning("Enter a proxy path")
        return
    ok, msg = _validate_proxy_path(path)
    if not ok:
        cmds.warning(msg)
        return
    from_selection = proxy_creation_mode() == "components"
    with _undo_chunk("Create Proxy"):
        cmds.a3obProxy(path=path, index=index, fromSelection=from_selection, update=True)
    from a3ob.ui.recent import remember_path
    remember_path("proxy", path)
    _refresh_context_ui()
```

The `a3ob.ui.dialogs` import is deliberately **inside the function**, not at module level: this
module star-imports `a3ob.ui.entry`, and a module-level Qt import here would make every
`a3ob.ui.actions` import pull Qt in even in headless callers that never build a dock.

Note `_refresh_context_ui()` at the end — the old panel had no list to refresh, but the
Selections list must now show the new proxy immediately.

- [ ] **Step 6: Turn the Create button into a menu**

In `scripts/a3ob/ui/panels/selections.py`, the first button row (lines 31-39) currently builds
four plain buttons. Replace the `("Create", ...)` entry so the row becomes:

```python
        first_row = qt_widgets.QHBoxLayout()
        for label, callback, tip, icon in (
            ("Select", _select_set_members, "Select the live members of the highlighted set", ":/aselect.png"),
            ("Rename", _rename_selection_set, "Rename the highlighted Object Builder selection", ":/quickRename.png"),
        ):
            first_row.addWidget(_qt_button(label, callback, tip, icon))

        create_button = qt_widgets.QToolButton()
        create_button.setText("Create")
        create_button.setToolTip("Create a selection, proxy or flag set")
        create_icon = _qt_icon(":/create.png")
        if create_icon is not None and not create_icon.isNull():
            create_button.setIcon(create_icon)
        create_button.setPopupMode(qt_widgets.QToolButton.InstantPopup)
        create_menu = qt_widgets.QMenu(create_button)
        create_menu.addAction("Selection from components", _create_selection_set)
        create_menu.addAction("Proxy...", create_proxy_from_ui)
        create_button.setMenu(create_menu)
        # Qt does not own a menu set with setMenu(); without a reference the QMenu is garbage
        # collected as soon as this method returns and the button opens an empty popup.
        self.selection_create_menu = create_menu
        first_row.addWidget(create_button)

        first_row.addWidget(_qt_button("Find", find_components_from_ui,
                                       "Find closed mesh components and create Component## selection sets",
                                       ":/search.png"))
        layout.addLayout(first_row)
```

Add `self.selection_create_menu = None` to `scripts/a3ob/ui/dock.py` beside the other selection
attributes at line 83-85.

The Flag entry is added in Task 3 — leave the menu with two entries for now.

- [ ] **Step 7: Verify the dock still builds and the panels stay silent**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_path_validation.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
```

All four must pass. `proxy_path_validation.py` covers `_validate_proxy_path`, which this task
kept intact — if it fails, the validation call was dropped rather than moved.

- [ ] **Step 8: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
```

The two must report the same numbers. Then:

```bash
git add scripts/a3ob/ui/dialogs.py scripts/a3ob/ui/panels/selections.py \
        scripts/a3ob/ui/actions/metadata.py scripts/a3ob/ui/dock.py \
        tests/mayapy/proxy_creation_mode.py
git commit -m "feat: create proxies from the Selections panel's Create menu"
```

---

### Task 3: the Create menu gains a Flag entry

Flag creation currently lives in the Flags panel: a component combo, a value, a set name and an
Apply button. It follows proxies into the Create menu.

**Files:**
- Modify: `scripts/a3ob/ui/dialogs.py` (add `flag_dialog`)
- Modify: `scripts/a3ob/ui/panels/selections.py` (third menu entry)
- Modify: `scripts/a3ob/ui/actions/metadata.py:28-40` (`apply_flag_from_ui`)
- Modify: `tests/mayapy/proxy_creation_mode.py` (rename is NOT wanted — add a separate file)
- Create: `tests/mayapy/flag_creation.py`

**Interfaces:**
- Produces: `flag_dialog(dock)` in `a3ob.ui.dialogs` → `(component, value, name)` on accept where
  `component` is `"face"` or `"vertex"` (already lowercased for the command), `value` an int and
  `name` a non-empty string; `None` on cancel.
- Consumes: `cmds.a3obSetFlag(component=..., value=..., name=...)`, unchanged. It rejects
  `value == 0` and any component outside `("vertex", "face")` itself.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/flag_creation.py`:

```python
"""Flag sets created from the Selections panel land in that panel's list (mayapy).

The premise of folding Flags into Selections: create_metadata_set writes a3obSelectionName
alongside a3obFlagComponent, and _selection_sets() skips sets WITHOUT a3obSelectionName. So a
flag set already passes the Selections filter and already carries a kind. If that ever stops
being true, this whole panel merge rests on nothing — which is what this test pins.

Run:  mayapy.exe tests/mayapy/flag_creation.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.scene.selections import selection_sets_for_owner  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_lod():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    return transform


def test_a_face_flag_appears_in_the_selections_list_with_its_kind():
    lod = build_lod()
    cmds.select(lod + ".f[0:1]", replace=True)
    cmds.a3obSetFlag(component="face", value=8, name="hidden")

    rows = selection_sets_for_owner(lod)
    kinds = [row["kind"] for row in rows]
    check("Face Flag" in kinds,
          "a face flag set is not listed as 'Face Flag'; got kinds %r" % kinds)
    row = [item for item in rows if item["kind"] == "Face Flag"][0]
    check(row["name"] == "hidden", "flag row name is %r, expected 'hidden'" % row["name"])


def test_a_vertex_flag_is_listed_as_vertex_flag():
    lod = build_lod()
    cmds.select(lod + ".vtx[0:3]", replace=True)
    cmds.a3obSetFlag(component="vertex", value=1, name="soft")

    kinds = [row["kind"] for row in selection_sets_for_owner(lod)]
    check("Vertex Flag" in kinds,
          "a vertex flag set is not listed as 'Vertex Flag'; got kinds %r" % kinds)


def test_flag_sets_carry_a_selection_name():
    """The load-bearing premise: _selection_sets() drops any set without a3obSelectionName."""
    lod = build_lod()
    cmds.select(lod + ".f[0]", replace=True)
    cmds.a3obSetFlag(component="face", value=2, name="marker")

    flag_sets = [node for node in cmds.ls(type="objectSet") or []
                 if cmds.attributeQuery("a3obFlagComponent", node=node, exists=True)]
    check(len(flag_sets) == 1, "expected one flag set, got %r" % flag_sets)
    check(cmds.attributeQuery("a3obSelectionName", node=flag_sets[0], exists=True),
          "the flag set has no a3obSelectionName — it would vanish from the Selections list")


def main():
    for test in (test_a_face_flag_appears_in_the_selections_list_with_its_kind,
                 test_a_vertex_flag_is_listed_as_vertex_flag,
                 test_flag_sets_carry_a_selection_name):
        test()
        print("ok:", test.__name__, flush=True)
    print("FLAG CREATION: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 2: Run it**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/flag_creation.py
```

This one is expected to **PASS immediately** — it pins an existing property rather than driving
new code. Say so plainly in your report; do not claim a witnessed failure you did not see.

To confirm it is not vacuous, temporarily edit `scripts/a3ob/ui/scene/selections.py:51` from
`if not _attr_exists(node, "a3obSelectionName"): continue` to
`if _attr_exists(node, "a3obFlagComponent"): continue`, re-run, and confirm it fails naming the
missing kind. **Revert that edit immediately** and re-run to confirm green. Paste both outputs.

- [ ] **Step 3: Add `flag_dialog` to `scripts/a3ob/ui/dialogs.py`**

Append:

```python
def flag_dialog(dock):
    """Ask for a flag's component type, value and set name.

    Returns (component, value, name) with component already lowercased for a3obSetFlag, or
    None if cancelled. The command itself rejects a zero value and any component outside
    vertex/face, so this dialog does not duplicate that check — it only refuses an empty
    name, which the command would otherwise turn into the placeholder "a3ob_flag#"."""
    dialog = qt_widgets.QDialog(dock)
    dialog.setWindowTitle("Create Flag Set")
    layout = qt_widgets.QVBoxLayout(dialog)

    form_holder = qt_widgets.QWidget()
    form = qt_widgets.QFormLayout(form_holder)
    form.setContentsMargins(0, 0, 0, 0)
    component_combo = qt_widgets.QComboBox()
    component_combo.addItems(["Face", "Vertex"])
    value_field = qt_widgets.QSpinBox()
    value_field.setRange(-2147483648, 2147483647)
    value_field.setValue(1)
    name_field = qt_widgets.QLineEdit("a3ob_flag")
    form.addRow("Component", component_combo)
    form.addRow("Value", value_field)
    form.addRow("Set name", name_field)
    layout.addWidget(form_holder)

    hint = qt_widgets.QLabel("Select mesh vertices or faces before creating a flag set.")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    buttons = qt_widgets.QDialogButtonBox(
        qt_widgets.QDialogButtonBox.Ok | qt_widgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    if not accepted:
        return None
    return (component_combo.currentText().lower(), value_field.value(),
            name_field.text().strip())
```

- [ ] **Step 4: Rewrite `apply_flag_from_ui`**

In `scripts/a3ob/ui/actions/metadata.py`, replace `apply_flag_from_ui` (lines 28-40):

```python
def apply_flag_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    from a3ob.ui.dialogs import flag_dialog
    answer = flag_dialog(dock)
    if answer is None:
        return
    component, value, name = answer
    if not name:
        cmds.warning("Enter a flag set name")
        return
    with _undo_chunk("Set Flag"):
        cmds.a3obSetFlag(component=component, value=value, name=name)
    _refresh_context_ui()
```

- [ ] **Step 5: Add the third menu entry**

In `scripts/a3ob/ui/panels/selections.py`, after the `"Proxy..."` action:

```python
        create_menu.addAction("Flag...", apply_flag_from_ui)
```

`apply_flag_from_ui` is already reachable — `panels/selections.py` star-imports
`a3ob.ui.actions`, and `actions/metadata.py` exports it in `__all__`. Confirm with:

```bash
grep -n "apply_flag_from_ui" scripts/a3ob/ui/actions/metadata.py
```

Expected: the `def`, and a line inside `__all__`.

- [ ] **Step 6: Re-run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/flag_creation.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
```

- [ ] **Step 7: Commit**

```bash
git add scripts/a3ob/ui/dialogs.py scripts/a3ob/ui/panels/selections.py \
        scripts/a3ob/ui/actions/metadata.py tests/mayapy/flag_creation.py
git commit -m "feat: create flag sets from the Selections panel's Create menu"
```

---

### Task 4: flag rows become editable in the details area

Highlighting a Vertex Flag or Face Flag row exposes its component and value for editing.
Everything else keeps the summary label it has today.

There is no `a3obUpdateFlag` command — `a3obSetFlag` only creates. Editing therefore writes
`a3obFlagComponent` / `a3obFlagValue` on the existing set with `cmds.setAttr`, inside an undo
chunk. Do **not** add a command for this: registered command names are a hard contract, and this
edit creates no set, so it carries none of the orphan-set risk that made the proxy commands
non-undoable.

**Files:**
- Modify: `scripts/a3ob/ui/scene/selections.py` (add `selection_set_editable_fields`)
- Modify: `scripts/a3ob/ui/panels/selections.py` (details area becomes a stack)
- Modify: `scripts/a3ob/ui/actions/selections.py:24-32` (`_update_selection_details`)
- Modify: `scripts/a3ob/ui/actions/metadata.py` (add `apply_flag_edit_from_ui`)
- Modify: `scripts/a3ob/ui/dock.py` (new widget attributes)
- Create: `tests/mayapy/selection_detail_editors.py`

**Interfaces:**
- Produces: `selection_set_editable_fields(set_node)` in `a3ob.ui.scene.selections` → a dict
  `{"kind": str, "flag_component": str, "flag_value": int, "proxy_path": str,
  "proxy_index": int}`. A **silent read**: it warns nothing and writes nothing. Absent data is
  `""` / `0`. Task 5 fills in the two proxy keys; this task returns `""` and `0` for them.
- Produces: `dock.show_selection_editor(fields)` in `a3ob.ui.panels.selections` — switches the
  stacked details area to the page matching `fields["kind"]` and loads the values into it.
- Produces: `dock.flag_edit_values()` → `(component, value)` from the flag editor page.
- Produces: `apply_flag_edit_from_ui()` in `a3ob.ui.actions.metadata`.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/selection_detail_editors.py`. This builds a **real dock**, so the header
order is mandatory — `QApplication` before `_harness.bootstrap()`, exactly as in
`tests/mayapy/lod_panel_inline_edit.py`:

```python
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

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

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
    from a3ob.ui.entry import _build_qt_dock
    lod, flag_set = build_lod_with_a_flag(component="vertex", value=3, name="soft")
    dock = _build_qt_dock()
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
        dock.close()
        dock.deleteLater()


def test_an_ordinary_selection_shows_no_editor():
    from a3ob.ui.entry import _build_qt_dock
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    set_node = cmds.sets(transform + ".f[0]", name="a3ob_SEL_camo")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "camo", type="string")

    dock = _build_qt_dock()
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
        dock.close()
        dock.deleteLater()


def test_applying_a_flag_edit_writes_through_and_creates_no_set():
    from a3ob.ui.actions.metadata import apply_flag_edit_from_ui
    from a3ob.ui.entry import _build_qt_dock
    lod, flag_set = build_lod_with_a_flag(component="face", value=8, name="hidden")
    dock = _build_qt_dock()
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
        dock.close()
        dock.deleteLater()


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
                 test_applying_a_flag_edit_writes_through_and_creates_no_set):
        test()
        print("ok:", test.__name__, flush=True)
    print("SELECTION DETAIL EDITORS: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 2: Run it and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/selection_detail_editors.py
```

Expected: `ImportError` on `selection_set_editable_fields`. Record the exact text.

- [ ] **Step 3: Add the scene read**

In `scripts/a3ob/ui/scene/selections.py`, after `_selection_set_details` (line 112), add:

```python
def selection_set_editable_fields(set_node):
    """What the details area should show for one set — a SILENT read.

    Called on every list highlight change, so it must not warn and must not write:
    _selection_sets() normalising on read once dirtied the scene badly enough that Maya asked
    "Save changes?" after a read-only session.

    A set can be deleted between the list being built and a row being highlighted, so a
    missing node reports an empty kind rather than raising. The proxy keys are filled in for
    Proxy rows only; every other kind reports "" and 0."""
    empty = {"kind": "", "flag_component": "", "flag_value": 0,
             "proxy_path": "", "proxy_index": 0}
    if not _node_exists(set_node):
        return empty
    is_proxy = bool(_safe_get_attr(set_node, "a3obIsProxySelection", False))
    flag_component = _safe_get_attr(set_node, "a3obFlagComponent", "") or ""
    fields = dict(empty)
    fields["kind"] = _set_kind(is_proxy, flag_component)
    fields["flag_component"] = flag_component
    fields["flag_value"] = int(_safe_get_attr(set_node, "a3obFlagValue", 0) or 0)
    return fields
```

Add `"selection_set_editable_fields"` to that module's `__all__` list (line 147-159).

- [ ] **Step 4: Turn the details area into a stack**

In `scripts/a3ob/ui/panels/selections.py`, replace lines 27-29 (the bare `selection_details`
label) with:

```python
        self.selection_details = qt_widgets.QLabel("Select a row to see details.")
        self.selection_details.setWordWrap(True)
        layout.addWidget(self.selection_details)

        # Page 0 is empty: an ordinary Selection row has nothing to edit, and the summary
        # label above already says everything about it. Pages 1 and 2 are the flag and proxy
        # editors — the capability the retired create-only panels never had.
        self.selection_editor_stack = qt_widgets.QStackedWidget()
        self.selection_editor_stack.addWidget(qt_widgets.QWidget())
        self.selection_editor_stack.addWidget(self._build_flag_editor_page())
        layout.addWidget(self.selection_editor_stack)
```

Then add these three methods to `SelectionsPanelMixin`:

```python
    def _build_flag_editor_page(self):
        page = qt_widgets.QWidget()
        form = qt_widgets.QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        self.flag_edit_component_combo = qt_widgets.QComboBox()
        self.flag_edit_component_combo.addItems(["Face", "Vertex"])
        self.flag_edit_value_field = qt_widgets.QSpinBox()
        self.flag_edit_value_field.setRange(-2147483648, 2147483647)
        form.addRow("Component", self.flag_edit_component_combo)
        form.addRow("Value", self.flag_edit_value_field)
        form.addRow(_qt_button("Apply", apply_flag_edit_from_ui,
                               "Write the component type and value onto the highlighted flag set",
                               ":/confirm.png"))
        return page


    def flag_edit_values(self):
        if self.flag_edit_component_combo is None or self.flag_edit_value_field is None:
            return "face", 0
        return (self.flag_edit_component_combo.currentText().lower(),
                self.flag_edit_value_field.value())


    def show_selection_editor(self, fields):
        """Switch the details area to the page matching the highlighted row's kind.

        Values are loaded with signals blocked: the editors are plain inputs with no
        change handler today, but a future one must not fire on a programmatic load and
        write back the value the user is only looking at."""
        if self.selection_editor_stack is None:
            return
        kind = fields.get("kind", "")
        if kind in ("Vertex Flag", "Face Flag"):
            self.flag_edit_component_combo.blockSignals(True)
            self.flag_edit_value_field.blockSignals(True)
            index = 1 if fields.get("flag_component") == "vertex" else 0
            self.flag_edit_component_combo.setCurrentIndex(index)
            self.flag_edit_value_field.setValue(int(fields.get("flag_value", 0)))
            self.flag_edit_component_combo.blockSignals(False)
            self.flag_edit_value_field.blockSignals(False)
            self.selection_editor_stack.setCurrentIndex(1)
            return
        self.selection_editor_stack.setCurrentIndex(0)
```

In `scripts/a3ob/ui/dock.py`, beside the other selection attributes (lines 83-85), add:

```python
        self.selection_editor_stack = None
        self.flag_edit_component_combo = None
        self.flag_edit_value_field = None
```

- [ ] **Step 5: Have the details update drive the stack**

In `scripts/a3ob/ui/actions/selections.py`, replace `_update_selection_details` (lines 24-32):

```python
def _update_selection_details():
    set_node = _selected_selection_set()
    dock = _active_qt_dock()
    if not set_node:
        _clear_selection_manager_state()
        if dock is not None:
            dock.show_selection_editor({"kind": ""})
        return
    details = _selection_set_details(set_node)
    if dock is not None:
        dock.set_selection_details(details)
        dock.show_selection_editor(selection_set_editable_fields(set_node))
```

`selection_set_editable_fields` arrives through the existing
`from a3ob.ui.scene import *` at the top of the file, because Step 3 added it to that module's
`__all__`. Confirm with:

```bash
grep -n "selection_set_editable_fields" scripts/a3ob/ui/scene/selections.py
```

Expected two lines: the `def`, and an entry inside `__all__`. If the `__all__` entry is missing
the star import will not re-export it and `_update_selection_details` will raise `NameError` at
the first highlight change — which no test would catch until a row is actually clicked.

- [ ] **Step 6: Add the action that writes the edit**

In `scripts/a3ob/ui/actions/metadata.py`, add after `apply_flag_from_ui`:

```python
def apply_flag_edit_from_ui():
    """Write the details-area flag editor onto the highlighted set.

    There is no a3obUpdateFlag command — a3obSetFlag only creates — so this writes the two
    attributes directly. That is safe where the proxy commands are not: this creates no
    objectSet, so it carries none of the orphan-set risk that makes a3obProxy and
    a3obUpdateProxy deliberately non-undoable. A plain cmds.setAttr undoes correctly."""
    dock = _active_qt_dock()
    if dock is None:
        return
    set_node = dock.selected_selection_set_node()
    if not set_node:
        cmds.warning("Select a flag set to edit")
        return
    component, value = dock.flag_edit_values()
    if value == 0:
        cmds.warning("A flag value of 0 is not exported — enter a non-zero value")
        return
    with _undo_chunk("Edit Flag"):
        cmds.setAttr(set_node + ".a3obFlagComponent", component, type="string")
        cmds.setAttr(set_node + ".a3obFlagValue", value)
    _refresh_context_ui()
```

The zero check mirrors `a3obSetFlag`'s own rejection and `a3obValidate`'s "invalid zero flag
value" error — a zero-valued flag set exports nothing (`export/taggs/data.py:98`), so writing
one would silently drop the flag.

Add `"apply_flag_edit_from_ui"` to that module's `__all__`.

- [ ] **Step 7: Run the test and verify it passes**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/selection_detail_editors.py
```

Expected: seven `ok:` lines then `SELECTION DETAIL EDITORS: PASS`.

- [ ] **Step 8: Verify the silence gates**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/undo_survives_dock_actions.py
```

All four must pass. `dock_refresh_cost.py` matters: `show_selection_editor` now runs on every
highlight change, and a component pick must still cost zero rebuilds.

- [ ] **Step 9: Commit**

```bash
git add scripts/a3ob/ui/scene/selections.py scripts/a3ob/ui/panels/selections.py \
        scripts/a3ob/ui/actions/selections.py scripts/a3ob/ui/actions/metadata.py \
        scripts/a3ob/ui/dock.py tests/mayapy/selection_detail_editors.py
git commit -m "feat: edit a flag set from the Selections details area"
```

---

### Task 5: proxy rows become editable

The spec calls this "the one that turns a wrong path from 'delete and rebuild the proxy' into
'fix the path'". It rests on Task 1: without the pair fix, an Update through the set would rename
the set and leave the placeholder pointing at the old proxy.

`a3obUpdateProxy` takes **no target node** — it acts on the current selection
(`selected_dependency_node_or_null()`, `commands/update_proxy.py:40`). The action therefore
selects the set, runs the command, and restores the previous selection in a `finally`. This is
the same resolve-then-restore shape that P2 Task 8 used to reconcile validation with the
exporter.

**Files:**
- Modify: `scripts/a3ob/ui/scene/selections.py` (`selection_set_editable_fields` fills the proxy keys)
- Modify: `scripts/a3ob/ui/panels/selections.py` (third stack page)
- Modify: `scripts/a3ob/ui/actions/metadata.py` (add `update_proxy_from_ui`)
- Modify: `scripts/a3ob/ui/dock.py` (two more widget attributes)
- Modify: `tests/mayapy/selection_detail_editors.py` (add the proxy cases)

**Interfaces:**
- Produces: `dock.proxy_edit_values()` → `(path, index)` from the proxy editor page.
- Produces: `update_proxy_from_ui()` in `a3ob.ui.actions.metadata`.
- Consumes: `sync_proxy_pair` indirectly, through `cmds.a3obUpdateProxy(path=..., index=...)`.

- [ ] **Step 1: Add the failing tests**

Append to `tests/mayapy/selection_detail_editors.py`, before `_user_role`:

```python
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


def test_fields_report_a_proxy_path_and_index():
    _lod, proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=3)
    fields = selection_set_editable_fields(proxy_set)
    check(fields["kind"] == "Proxy", "kind is %r" % fields["kind"])
    check(fields["proxy_path"] == "p\\weapon.p3d", "path is %r" % fields["proxy_path"])
    check(fields["proxy_index"] == 3, "index is %r" % fields["proxy_index"])


def test_the_proxy_editor_page_follows_the_highlighted_row():
    from a3ob.ui.entry import _build_qt_dock
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=3)
    dock = _build_qt_dock()
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
        dock.close()
        dock.deleteLater()


def test_update_writes_the_new_path_to_both_halves():
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    from a3ob.ui.entry import _build_qt_dock
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=1)
    dock = _build_qt_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        dock.selection_list.setCurrentItem(proxy_rows[0])

        before = len(cmds.ls(type="objectSet") or [])
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(7)
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
        dock.close()
        dock.deleteLater()


def test_update_restores_the_previous_selection():
    """a3obUpdateProxy acts on the SELECTION, so the action must select the set and put the
    user's selection back — otherwise clicking Update silently changes what is selected."""
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    from a3ob.ui.entry import _build_qt_dock
    lod, _proxy_set = build_lod_with_a_proxy()
    dock = _build_qt_dock()
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
        update_proxy_from_ui()
        after = cmds.ls(selection=True, long=True) or []
        check(before == after,
              "the selection changed from %r to %r across an Update" % (before, after))
    finally:
        dock.close()
        dock.deleteLater()
```

```python
def test_undo_after_update_resurrects_no_orphan_set():
    """The spec's sharpest test. a3obProxy and a3obUpdateProxy are non-undoable precisely
    because MFnSet.create() never enters the undo queue: when they WERE undoable, Ctrl+Z
    rolled back the DAG side while the sets stayed, leaving orphan a3ob_proxy_* behind.
    Update runs through the same commands, so it inherits the same hazard."""
    from a3ob.ui.actions.metadata import update_proxy_from_ui
    from a3ob.ui.entry import _build_qt_dock
    lod, _proxy_set = build_lod_with_a_proxy(path="p\\weapon.p3d", index=1)
    dock = _build_qt_dock()
    try:
        cmds.select(lod, replace=True)
        dock.refresh_selection_manager()
        rows = [dock.selection_list.item(i) for i in range(dock.selection_list.count())]
        proxy_rows = [row for row in rows if row.data(_user_role())["kind"] == "Proxy"]
        dock.selection_list.setCurrentItem(proxy_rows[0])

        before = len(cmds.ls(type="objectSet") or [])
        dock.proxy_edit_path_field._line_edit.setText("p\\other.p3d")
        dock.proxy_edit_index_field.setValue(7)
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
        dock.close()
        dock.deleteLater()
```

Register all five in `main()`'s tuple, after the existing entries.

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/selection_detail_editors.py
```

Expected: the first new test fails on `proxy_path` being `""` — Task 4 left those keys empty.
Record it.

- [ ] **Step 3: Fill in the proxy keys**

A proxy's path and index live on the **placeholder transform**, not on the selection set. The
set carries only `a3obSelectionName`, which is the `proxy:PATH.INDEX` key. Read the placeholder
through that key. In `scripts/a3ob/ui/scene/selections.py`, extend
`selection_set_editable_fields` before its `return`:

```python
    if fields["kind"] == "Proxy":
        selection_name = _safe_get_attr(set_node, "a3obSelectionName", "") or ""
        fields["proxy_path"], fields["proxy_index"] = _proxy_path_and_index(selection_name)
    return fields


def _proxy_path_and_index(selection_name):
    """(path, index) of the placeholder matching a proxy selection name, or ("", 0).

    The set holds only the proxy:PATH.INDEX key; the path and index themselves live on the
    placeholder transform. Parsing them back out of the key would be simpler and wrong — a
    DayZ path may itself contain dots, so the last dot is not reliably the index separator.
    Read the placeholder's own attributes instead."""
    if not selection_name:
        return "", 0
    for node in cmds.ls("*.a3obProxySelection", objectsOnly=True, long=True) or []:
        if _safe_get_attr(node, "a3obProxySelection", "") == selection_name:
            return (_safe_get_attr(node, "a3obProxyPath", "") or "",
                    int(_safe_get_attr(node, "a3obProxyIndex", 0) or 0))
    return "", 0
```

- [ ] **Step 4: Add the proxy editor page**

In `scripts/a3ob/ui/panels/selections.py`, add a third page to the stack:

```python
        self.selection_editor_stack.addWidget(self._build_proxy_editor_page())
```

directly after the `_build_flag_editor_page()` line, and add these methods:

```python
    def _build_proxy_editor_page(self):
        page = qt_widgets.QWidget()
        form = qt_widgets.QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        self.proxy_edit_path_field = self._path_picker("Proxy path", "Select proxy P3D", 1,
                                                       "Arma P3D (*.p3d)", recent_key="proxy")
        self.proxy_edit_index_field = qt_widgets.QSpinBox()
        self.proxy_edit_index_field.setRange(0, 2147483647)
        form.addRow("Path", self.proxy_edit_path_field)
        form.addRow("Index", self.proxy_edit_index_field)
        form.addRow(_qt_button("Update", update_proxy_from_ui,
                               "Point the highlighted proxy at a new path and index",
                               ":/confirm.png"))
        return page


    def proxy_edit_values(self):
        field = _picker_field(self.proxy_edit_path_field)
        path = field.text().strip() if field is not None else ""
        index = self.proxy_edit_index_field.value() if self.proxy_edit_index_field is not None else 1
        return path, index
```

Extend `show_selection_editor` — insert before its final `setCurrentIndex(0)`:

```python
        if kind == "Proxy":
            field = _picker_field(self.proxy_edit_path_field)
            if field is not None:
                field.blockSignals(True)
                field.setText(fields.get("proxy_path", ""))
                field.blockSignals(False)
            self.proxy_edit_index_field.blockSignals(True)
            self.proxy_edit_index_field.setValue(int(fields.get("proxy_index", 0)))
            self.proxy_edit_index_field.blockSignals(False)
            self.selection_editor_stack.setCurrentIndex(2)
            return
```

In `scripts/a3ob/ui/dock.py`, beside the attributes added in Task 4:

```python
        self.proxy_edit_path_field = None
        self.proxy_edit_index_field = None
```

- [ ] **Step 5: Add the action**

In `scripts/a3ob/ui/actions/metadata.py`:

```python
def update_proxy_from_ui():
    """Point the highlighted proxy at a new path and index.

    a3obUpdateProxy takes no target node — it acts on whatever is SELECTED
    (selected_dependency_node_or_null in commands/update_proxy.py). So this selects the set,
    runs the command and restores the user's selection in a finally: clicking Update must not
    silently change what is selected in the viewport, and it must not leave the proxy set
    selected if the command raises."""
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    set_node = dock.selected_selection_set_node()
    if not set_node:
        cmds.warning("Select a proxy in the list to update")
        return
    path, index = dock.proxy_edit_values()
    if not path:
        cmds.warning("Enter a proxy path")
        return
    ok, msg = _validate_proxy_path(path)
    if not ok:
        cmds.warning(msg)
        return
    previous = cmds.ls(selection=True, long=True) or []
    try:
        cmds.select(set_node, replace=True)
        with _undo_chunk("Update Proxy"):
            cmds.a3obUpdateProxy(path=path, index=index)
    finally:
        if previous:
            cmds.select(previous, replace=True)
        else:
            cmds.select(clear=True)
    from a3ob.ui.recent import remember_path
    remember_path("proxy", path)
    _refresh_context_ui()
```

Add `"update_proxy_from_ui"` to `__all__`.

- [ ] **Step 6: Run the test**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/selection_detail_editors.py
```

Expected: twelve `ok:` lines then `SELECTION DETAIL EDITORS: PASS`.

- [ ] **Step 7: Verify the neighbours**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/proxy_update_keeps_pair.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/undo_survives_dock_actions.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_undo.py
```

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/ui/scene/selections.py scripts/a3ob/ui/panels/selections.py \
        scripts/a3ob/ui/actions/metadata.py scripts/a3ob/ui/dock.py \
        tests/mayapy/selection_detail_editors.py
git commit -m "feat: edit a proxy's path and index from the Selections details area"
```

---

### Task 6: retire the Flags and Proxies panels

Nothing depends on them now. The dock goes from eight panels to six.

**Files:**
- Delete: `scripts/a3ob/ui/panels/metadata.py`
- Modify: `scripts/a3ob/ui/dock.py` (panel entries, mixin, six attributes)
- Modify: `scripts/a3ob/ui/panels/__init__.py`
- Modify: `CLAUDE.md` if it names either panel
- Modify: `tests/mayapy/dock_panel_sync.py` (absence assertions)

- [ ] **Step 1: Find every reference before deleting**

```bash
grep -rn "MetadataPanelMixin\|_build_flags_section\|_build_proxies_section" \
  scripts/ tests/ plug-ins/ install/ docs/ CLAUDE.md README.md | grep -v __pycache__
grep -rn "flag_component_combo\|flag_value_field\|flag_name_field\|proxy_path_field\|proxy_index_field\|proxy_from_selection_check" \
  scripts/ tests/ | grep -v __pycache__
grep -rn "def flag_component\|def flag_value\|def flag_name\|def proxy_path\|def proxy_index\|def proxy_from_selection" \
  scripts/ | grep -v __pycache__
```

Write the full result into your report. This sweep exists because Phase 1's Task 5 lost a day to
a file no task's list named: `export/exporter.py` read a constant a deletion removed, and it
would have raised `AttributeError` on every export. Do not skip it.

Note carefully: the six accessor methods (`flag_component`, `flag_value`, `flag_name`,
`proxy_path`, `proxy_index`, `proxy_from_selection`) are on `MetadataPanelMixin` and are used by
the **old** action bodies, which Tasks 2 and 3 replaced. If the sweep still shows a live caller,
stop and report it — something from an earlier task was not converted.

- [ ] **Step 2: Add the absence assertions to `dock_panel_sync.py`**

Find the test function in `tests/mayapy/dock_panel_sync.py` that asserts required dock symbols
exist (it positively checks roughly twenty of them). Add inside **that same function** — not a
new one, so the assertions cannot pass vacuously if the surrounding test stops running:

```python
    for gone in ("_build_flags_section", "_build_proxies_section", "flag_component",
                 "flag_name", "proxy_from_selection"):
        check(not hasattr(dock_class, gone),
              "%s survived the Flags/Proxies panel removal" % gone)
```

Match the local naming — if the function calls its dock class something else, use that name.

- [ ] **Step 3: Run it and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
```

Expected: FAIL naming `_build_flags_section`. Record it.

- [ ] **Step 4: Delete the panel module and unwire it**

```bash
git rm scripts/a3ob/ui/panels/metadata.py
```

In `scripts/a3ob/ui/dock.py`:
- remove the `MetadataPanelMixin` import and its entry in the dock class's base list;
- remove the two panel entries at lines 124 and 127 (`("Flags", ...)` and `("Proxies", ...)`);
- remove the six attributes at lines 66-71.

In `scripts/a3ob/ui/panels/__init__.py`, remove the `metadata` import and its `__all__` entry.

Leave `scripts/a3ob/ui/actions/metadata.py` alone — it is a different file and still holds the
mass and flag and proxy actions.

- [ ] **Step 5: Run the test and verify it passes**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
```

- [ ] **Step 6: Verify the whole dock still stands**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/selection_detail_editors.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

`plugin_teardown.py` matters here: it loads and unloads the plugin, which is where a dangling
import of a deleted module shows up.

- [ ] **Step 7: Update the docs**

If `CLAUDE.md` or `README.md` names the Flags or Proxies panels, or states a panel count, correct
it. Phase 1's final review found `CLAUDE.md` stale in three places because no task owned it.

- [ ] **Step 8: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add -A
git commit -m "refactor: retire the Flags and Proxies panels"
```

---

## What is deliberately NOT in this phase

- **Viewport visualisation of proxy placeholders.** The spec names it as a real gap — a proxy is
  invisible until export — and explicitly defers it as a viewport feature, not a panel one.
- **Mass and Named Properties.** Both already moved into the LOD detail area in Phase 3a Tasks 2
  and 3. The `mass-flags-properties` spec's remaining claim on this phase is Flags only.
- **A `a3obUpdateFlag` command.** Editing a flag writes two attributes on an existing set; adding
  a registered command name is a hard-contract change with nothing to buy.
- **Gating any control by LOD type.** "Relevance drives prominence, never availability" — the
  editors appear per row *kind*, which is what the row actually is, not a guess about what the
  user needs.

## Verification for the controller between tasks

```bash
python tests/run_all.py
```

Controller only. Expected after Task 6: the Phase 3a baseline of 52 plus the four new files
(`proxy_update_keeps_pair`, `proxy_creation_mode`, `flag_creation`, `selection_detail_editors`),
all green, with the byte gate printing real per-fixture lines rather than `SKIP`.
