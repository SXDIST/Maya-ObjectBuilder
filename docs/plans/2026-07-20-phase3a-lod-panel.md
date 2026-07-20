# Phase 3a: one LOD panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps
> use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four dock panels — LODs, LOD Properties, Mass & Flags, Named Properties — become
one. Type and resolution are edited inline in the list; mass and named properties move into
a detail area below it; flags leave for Selections in Phase 3b.

**Architecture:** The list becomes a `QTreeWidget` with per-row editors. Everything that
belongs to *one LOD* gathers under that LOD's row; everything component-shaped leaves. Built
bottom-up: the row editors first, then the detail area they sit above, then the deletions.

**Tech Stack:** Python 3, PySide/Qt via `a3ob.ui._qt`, Maya API 2.0, `mayapy` for tests.

**Specs:** `docs/specs/2026-07-20-ui-simplification-design.md` (LOD merge),
`docs/specs/2026-07-20-mass-flags-properties-design.md`

## Global Constraints

- **Never run `mayapy tests/golden.py capture`.** `verify` only. The gate must stay at
  `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229. **This phase touches no
  export code, so any movement means something is very wrong** — stop and report.
- **Run every command in the FOREGROUND.** Background suite runs stalled three agents
  earlier in this work.
- **Do not run `python tests/run_all.py` in a task** — the orchestrator runs it. Targeted
  tests only. The suite is currently 48/48.
- **Relevance drives prominence, never availability.** From the mass/flags spec: every one
  of these parameters is used situationally and the tool cannot know which. Mass is always
  *present*, merely collapsed when the LOD type makes it unusual; the property name combo
  suggests but stays editable; nothing is removed from `KNOWN_NAMED_PROPS`.
- **LOD identity is its NODE, never its label.** A measured scene had `|helmet`,
  `|group1|body|Resolution_2` and `|group1|body|Resolution_1` all reading "Resolution 1".
  Row data must carry the node.
- **Marking a mesh as a LOD must NOT rename it.** Renaming shipped once and was reverted:
  "helmet" became "Resolution_1" and a second mesh of the same type collided into a suffix.
- **Panels must be SILENT queries that never write on refresh.** A panel that dirtied the
  scene made Maya ask "Save changes?" after a read-only session.
- **Component picking must cost zero panel rebuilds** (`dock_refresh_cost.py`).
  `SelectionChanged` fires per marquee-drag step; per-row widgets are the risk this phase
  introduces.
- Every module in `a3ob.ui.actions` does `from a3ob.ui.entry import *`, so `entry` must never
  import from that package at module level.
- Mixed line endings, no `.gitattributes` — targeted edits, never wholesale rewrites.
- `mayapy` is `C:\Program Files\Autodesk\Maya2027\bin\mayapy.exe`; each mayapy test runs in
  its own process.

## Starting point

`dock.py` currently lists ten panels. This plan removes two and renames one:

| Panel | Fate |
|-------|------|
| `LODs` | absorbs the others |
| `LOD Properties` | **gone** — type/resolution move into the rows |
| `Mass & Flags` | mass to the detail area; renamed `Flags`, which Phase 3b folds into Selections |
| `Named Properties` | **gone** — into the detail area |

## File Structure

| File | Responsibility after 3a |
|------|-------------------------|
| `scripts/a3ob/ui/panels/lod_list.py` | the whole LOD panel: tree, row editors, detail area |
| `scripts/a3ob/ui/panels/lod.py` | Memory Points only, plus the LOD-marking actions |
| `scripts/a3ob/ui/panels/metadata.py` | proxies and flags only, until Phase 3b takes them |
| `scripts/a3ob/ui/panels/named_properties.py` | **deleted** — its body moves into the detail area |
| `scripts/a3ob/ui/dock.py` | eight panels instead of ten |

---

### Task 1: The tree, with type and resolution in the row

**Files:**
- Modify: `scripts/a3ob/ui/panels/lod_list.py`
- Create: `tests/mayapy/lod_panel_inline_edit.py`

**Interfaces:**
- Produces: `refresh_lod_list()` unchanged in name and callers; rows carry the node in
  `qt_core.Qt.UserRole` as they already do.

- [ ] **Step 1: Write the failing test**

```python
"""Type and resolution are edited in the LOD row, and write to that row's node (mayapy).

The old panel edited whatever was SELECTED. Inline editors must address the node of
their own row — a measured scene had three distinct nodes all reading "Resolution 1",
so editing "the selected LOD" while looking at a different row wrote to the wrong one.

Run:  mayapy.exe tests/mayapy/lod_panel_inline_edit.py
"""

import os

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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py`
Expected: FAIL — `AttributeError: 'MayaObjectBuilderDock' object has no attribute 'lod_row_nodes'`

If constructing the dock headless fails outright, read `tests/mayapy/dock_panel_sync.py` for
how this suite builds one and match it. Qt is available under `mayapy` in this project —
`dock_refresh_cost.py` and `dock_panel_sync.py` both instantiate the dock.

- [ ] **Step 3: Convert the list to a tree**

In `_build_lod_list_section`, replace `qt_widgets.QListWidget()` with a four-column
`qt_widgets.QTreeWidget()`: **LOD**, **Type**, **Res**, **Stats**. Keep the existing
context menu, double-click-to-frame, and the Add/Frame/Isolate row exactly as they are.

- [ ] **Step 4: Give each row its editors**

In `refresh_lod_list`, for each row create a `QComboBox` populated from `LOD_DEFINITIONS`
(same icons the old `lod_type_combo` used) and a `QSpinBox` (range 0..1000000), attached with
`setItemWidget`.

Two rules the editors must follow:

```python
        # The editor writes to the node of ITS OWN ROW, captured here — never to
        # _selected_lod_transform(). The old panel edited the selection, which is wrong the
        # moment the row being edited is not the row selected.
        combo.currentIndexChanged.connect(
            lambda _index, n=node, c=combo: self._on_row_type_changed(n, c))
        spin.valueChanged.connect(
            lambda value, n=node: self._on_row_resolution_changed(n, value))
```

and

```python
        # has_resolution == False means the type carries a fixed resolution; show it, do not
        # let it be edited. Disabled, not hidden: the value is still information.
        spin.setEnabled(bool(definition["has_resolution"]))
```

- [ ] **Step 5: Add the three methods the test names**

```python
    def lod_row_nodes(self):
        """Every row's node, in display order. Read-only; used by tests and by the
        detail area to find the row a node belongs to."""

    def set_row_type(self, node, lod_type):
        """Set a row's LOD type as if its combo had been changed."""

    def set_row_resolution(self, node, resolution):
        """Set a row's resolution as if its spin box had been changed."""
```

`set_row_*` must go through the same write path the editors use, or the test verifies
something the user never exercises. Both write through `cmds.a3obCreateLOD` the way
`_mark_selection_as_lod` does — **passing the node explicitly**, not relying on the current
selection — so the node's own name is left alone.

- [ ] **Step 6: Run the test to verify it passes**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py`
Expected: `OK - row editors address their own node, and never rename`

- [ ] **Step 7: Prove refresh cost did not regress**

Run:
```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
```
Expected: PASS both.

**If `dock_refresh_cost.py` fails**, the cause is almost certainly that `refresh_lod_list`
now rebuilds per-row widgets on every call. The fix is to rebuild widgets **only when the
set of LOD nodes changes**, and otherwise update the existing editors in place with signals
blocked. Do not "fix" it by making the refresh less correct.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: edit LOD type and resolution in the row

Each editor writes to the node of its own row, captured at creation. The old
panel edited whatever was selected, which is wrong the moment the row being
edited is not the row selected — and a measured scene had three distinct nodes
all reading 'Resolution 1'."
```

---

### Task 2: The detail area, and Named Properties into it

**Files:**
- Modify: `scripts/a3ob/ui/panels/lod_list.py`
- Delete: `scripts/a3ob/ui/panels/named_properties.py`
- Modify: `scripts/a3ob/ui/dock.py` — drop the panel entry, its polling, `_named_snapshot`
  and `_named_fields_focused`
- Create: `tests/mayapy/lod_panel_detail.py`

**Interfaces:**
- Consumes: `lod_row_nodes` from Task 1.
- Produces: the detail area follows the row selection; `refresh_named_properties` keeps its
  name so `entry.py` callers do not change.

- [ ] **Step 1: Write the failing test**

```python
"""Named properties live under the selected LOD's row, and apply to it (mayapy).

They are per-LOD data — a3obProperties on the LOD transform, exported as that LOD's
TAGGs — so they belong where the LOD is selected, not in a panel of their own.

Run:  mayapy.exe tests/mayapy/lod_panel_detail.py
"""

import os

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
    finally:
        dock.teardown()
    print("OK - named properties follow the selected LOD and accept unknown names")


main()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_detail.py`
Expected: FAIL — the standalone panel still exists.

- [ ] **Step 3: Build the detail area**

Below the tree and its button row in `_build_lod_list_section`, add a detail widget holding
the named-property controls moved from `named_properties.py`: the list, the editable name
combo, the value combo, the **Apply to all selected LODs** checkbox, and Add/Update + Remove.

Move the code rather than rewriting it — `_update_named_value_combo`,
`selected_named_property_lod`, `set_named_property_fields` and the rest already work and
carry their reasons. `selected_named_property_lod` should now resolve from the tree's current
row rather than the scene selection, falling back to the selection when no row is current.

Add `apply_named_property(name, value)` as the programmatic path the test uses, and have the
Add/Update button call it — the button and the test must exercise the same code.

- [ ] **Step 4: Delete the standalone panel**

```bash
git rm scripts/a3ob/ui/panels/named_properties.py
```

In `dock.py`: remove the `("Named Properties", ...)` entry, the `"Named Properties"` branch
of `_refresh_dirty_panels`, `_named_snapshot`, `_named_fields_focused`, and the
`NamedPropertiesPanelMixin` import and base class. Keep the polling machinery itself — it
still serves Materials and Selections.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_detail.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```
Expected: all pass. `p3d_workflow.py` asserts a list of dock symbols exist — update its
expectations if it names `_build_named_properties_tab`, and say so in your report.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: named properties move under the LOD they belong to

a3obProperties lives on the LOD transform and exports as that LOD's TAGGs, so
it belongs where the LOD is selected rather than in a panel of its own. The
name combo still suggests from KNOWN_NAMED_PROPS and still accepts anything
typed — the vocabulary is Arma-wide and a garment author uses two or three of it."
```

---

### Task 3: Mass into the detail area

**Files:**
- Modify: `scripts/a3ob/ui/panels/lod_list.py`
- Modify: `scripts/a3ob/ui/panels/metadata.py` — `_build_mass_flags_section` loses its mass
  half; the flag half stays until Phase 3b
- Modify: `scripts/a3ob/ui/dock.py` — the `Mass & Flags` panel becomes `Flags`
- Create: `tests/mayapy/lod_panel_mass.py`

- [ ] **Step 1: Write the failing test**

```python
"""Mass is present for every LOD type, collapsed where it is unusual (mayapy).

Export writes a mass TAGG wherever a3obMassValues exists and does not restrict it by
LOD type, so hiding the controls would make the UI narrower than the format. The rule
is: relevance drives prominence, never availability.

Run:  mayapy.exe tests/mayapy/lod_panel_mass.py
"""

import os

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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_mass.py`
Expected: FAIL — `mass_section_is_present` does not exist.

- [ ] **Step 3: Move the mass controls**

Move the mass half of `_build_mass_flags_section` — value, mode, current total, Apply, Clear,
density, Distribute evenly, From volume — into the detail area as its own collapsible group.
Add `mass_section_is_present()`, `mass_section_is_collapsed()` and `apply_mass(value)`.

Decide the collapse from the selected row's `a3obLodType`: expanded for the geometry family,
collapsed otherwise. **Collapsed, never hidden and never disabled** — the spec is explicit
that export permits mass on any LOD type and the UI must not be narrower than the format.

`refresh_mass_summary` keeps its name and its behaviour; point it at the row's node.

- [ ] **Step 4: Rename the remaining panel**

In `dock.py`, `("Mass & Flags", self._build_mass_flags_section(), ...)` becomes
`("Flags", self._build_flags_section(), ...)`, and `metadata.py`'s builder is renamed to
match. Phase 3b moves it into Selections; this task only stops it lying about its contents.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_mass.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_detail.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py
```
Expected: all pass. `command_correctness.py` covers `a3obSetMass`, which the moved controls
still call.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: mass moves under the LOD it belongs to

Present for every LOD type and merely collapsed where it is unusual. Export
writes a mass TAGG wherever a3obMassValues exists, without restricting it by
type, so hiding the controls would make the UI narrower than the format."
```

---

### Task 4: Retire LOD Properties, and gates

**Files:**
- Modify: `scripts/a3ob/ui/panels/lod.py` — `_build_lod_properties_section` goes; Memory
  Points and the marking actions stay
- Modify: `scripts/a3ob/ui/dock.py` — drop the panel entry and the now-unused
  `lod_type_combo` / `lod_resolution` attributes
- Modify: `scripts/a3ob/ui/actions/lod.py` — `_selected_lod_definition` and
  `_lod_resolution_value` read those widgets; repoint or remove them

- [ ] **Step 1: Find every consumer before deleting**

```bash
grep -rn "lod_type_combo\|lod_resolution\|lod_toggle\|lod_context\|_build_lod_properties_section\|selected_lod_definition\|lod_resolution_value" scripts/ tests/ --include=*.py
```

Handle every hit. `create_lod_type` and `assign_lod_to_selection` in `actions/lod.py` read
the dock's combo and spin box to decide what to create — they need a new source. The
tree's **Add LOD** menu already passes an explicit type; make the actions take their values
as arguments rather than reaching into widgets that no longer exist.

- [ ] **Step 2: Remove the panel**

Delete `_build_lod_properties_section` and the `("LOD Properties", ...)` entry. The
`DayZ LOD` checkbox becomes a **Mark Selection as LOD** button in the tree's button row, and
an **Unmark** entry in the row context menu, per the spec — `assign_lod_to_selection` and
`_remove_lod_from_selection` keep their behaviour.

- [ ] **Step 3: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_inline_edit.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_detail.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_panel_mass.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_naming.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_counts_ignore_intermediates.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/undo_survives_dock_actions.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```
Expected: all pass. `lod_naming.py` is the one that pins "marking must not rename" — if it
fails, the row editors are renaming and that is a real regression, not a stale expectation.

- [ ] **Step 4: Confirm the dock is down to eight panels**

```bash
grep -c '("\(.*\)", self\._build' scripts/a3ob/ui/dock.py
```
Expected: `8` — LODs, Flags, Materials, Selections, Proxies, Memory Points, Skinning,
Validation. Ten minus the two this plan removes (LOD Properties, Named Properties); Mass &
Flags is renamed, not removed, because Phase 3b is what folds it into Selections.

Report the list you actually get. If it is not these eight, say which differs rather than
adjusting the number to match.

- [ ] **Step 5: Byte gate**

Run: `"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify`
Expected: PASS, `5e66ed46ac09f396`/6145116 and `0ba984eb4fdb5d5e`/60229. **This phase touches
no export code — any movement is a serious signal.** Never `capture`.

- [ ] **Step 6: Line endings**

```bash
git diff --shortstat main..HEAD
git diff --shortstat --ignore-cr-at-eol main..HEAD
```
Expected: the two agree.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: retire the LOD Properties panel

Type and resolution are in the rows now; the DayZ LOD checkbox becomes a button
and a context-menu entry. Phase 3a complete."
```

---

## Self-review notes

**Spec coverage.** Inline type/resolution editing (Task 1), named properties into the detail
area (Task 2), mass into the detail area with prominence-not-availability honoured (Task 3),
the LOD Properties panel retired and the marking affordances relocated (Task 4).

**Deliberately deferred to Phase 3b.** Flags leave for Selections there; this plan only
renames the panel so it stops claiming to hold mass. The spec's proxy work and
`a3obUpdateProxy` editing are 3b's entirely.

**Deliberately deferred to Phase 3c.** The Skinning slim-down and the Materials → Attribute
Editor move, with the Preferences window that takes the texture root and the alpha toggle.

**The risk this plan carries.** Per-row widgets in a list that rebuilds on `SelectionChanged`
is exactly the shape `dock_refresh_cost.py` exists to catch. Tasks 1, 3 and 4 each re-run it
for that reason. If it fails, the answer is to rebuild widgets only when the node set changes
— not to make the refresh lazier in ways that leave the panel stale.

**Not specified here, and not an oversight.** Whether the multi-select + "Apply to all
selected LODs" path should also drive mass is left alone: the checkbox belongs to named
properties today, and widening it is a design change the spec does not ask for.
