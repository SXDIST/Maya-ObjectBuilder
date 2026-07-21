# Phase 3c — the Skinning panel slims to four buttons

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut `panels/skinning.py` from a wall of prose and eleven controls to four buttons and
a filtered influence list, moving the destructive and rare actions to a menu submenu where they
belong.

**Architecture:** Phase 1 already deleted the weights-storage block (roughly 40% of the panel)
with `a3obBakedWeights`. What remains is presentation plus three decisions: the `Detached over`
field goes because its default was measured rather than guessed; **Select Skin Outliers** arrives
from the Validation panel because it writes a selection and never belonged in a read-only
validator; and the reference-asset buttons move to a **Reference Assets** submenu because
`save_reference` overwrites with `force=True` and no confirmation.

**Tech Stack:** Maya 2027, Python 3, `maya.cmds` + Maya API 2.0, PySide6 (`a3ob.ui._qt`).

## Global Constraints

- **Never run `mayapy tests/golden.py capture`.** Only `verify`. `capture` overwrites the byte
  baseline and makes the gate vacuous. If `verify` prints `SKIP` rather than real per-fixture
  byte lines, stop and report it — two junction links are missing and every byte assertion is
  proving nothing.
- **Never run `python tests/run_all.py`** as an implementer. It stalls agents; the controller runs
  the full suite between tasks. Run individual test files instead.
- **Run every command in the FOREGROUND.** No background invocations.
- The byte contract must not move: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
- The `a3ob*` attribute schema is a hard contract — 33 long+short pairs in
  `scripts/a3ob/mayabridge/attributes.py`, pinned by `tests/python/test_attr_schema.py`. This
  phase adds no attribute and renames none.
- **Registered command names and their flags are a hard contract.** `a3obTransferSkin`,
  `a3obSkinWeights`, `a3obReference`, `a3obInfluence` and `a3obTestPose` all keep their names and
  every flag. `a3obTransferSkin -distance` stays — it is the escape hatch that justifies removing
  the panel field.
- **Panels must be silent reads.** Anything a panel calls during a refresh must not warn and must
  not write. `tests/mayapy/dock_panel_sync.py`, `tests/mayapy/panels_do_not_dirty_the_scene.py`
  and `tests/mayapy/dock_refresh_cost.py` guard this; all three must stay green.
- **A mayapy test that calls an `a3ob*` command needs `_harness.load_plugin()`.** Without it the
  command does not exist and the test fails with `AttributeError` unconditionally.
- **A real `QWidget` under mayapy segfaults** unless a `QApplication` exists *before*
  `maya.standalone.initialize()`. Use `_built_active_dock()` / `_release_active_dock()` from
  `tests/mayapy/_harness.py`.
- **The menu cannot be tested headlessly at all.** `entry.show_plugin_ui` returns immediately
  under `cmds.about(batch=True)` and every UI command returns `False`. So every menu callback must
  be a thin wrapper over a function that *is* testable, and the tests cover the function.
- Layering: `formats` → `mayabridge` → `ui`. Nothing under `mayabridge/` may import from
  `a3ob.ui` — in particular, a confirmation dialog belongs in the UI wrapper, never in
  `references.py`.
- **Line endings:** the repo has no `.gitattributes` and genuinely mixed endings. Before each
  commit compare `git diff --shortstat` against `git diff --shortstat --ignore-cr-at-eol` **over
  the full range you are committing**; the numbers must agree. Edit files in place.
- `mayapy` is `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe`. Each mayapy test runs in its
  own process.

## File structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `scripts/a3ob/mayabridge/commands/skin.py` | `a3obTransferSkin` reports rigidified shells alongside the mesh count |
| `scripts/a3ob/ui/entry.py` | `_transfer_skin` returns both numbers; `_save_reference_asset` confirms an overwrite |
| `scripts/a3ob/ui/panels/validation.py` | validation only — the outlier button leaves |
| `scripts/a3ob/ui/panels/skinning.py` | four buttons, a filtered list, two list actions, one summary line |
| `scripts/objectBuilderMenu.py` / `scripts/a3ob/ui/entry.py` | a **Reference Assets** submenu |

Four tasks. Task 1 is command-level and Qt-free. Task 2 moves one button. Task 3 is the panel
itself. Task 4 is the submenu and the overwrite guard, which is what makes removing the panel's
save buttons safe rather than merely tidier.

---

### Task 1: `a3obTransferSkin` reports how many shells were rigidified

`skintransfer.transfer_to_target` returns `(vertex count, rigidified shells)`
(`scripts/a3ob/mayabridge/skintransfer.py:365-366`). The command already unpacks both and writes
them to the script editor (`commands/skin.py:171-178`), but `setResult` carries only the mesh
count, so the panel cannot show the number and says "Transferred onto N mesh(es)".

That number matters *because* Task 3 removes the `Detached over` field. `DEFAULT_FAR_DISTANCE =
0.06` was measured on a real DayZ character — boots 0.009, trousers 0.019, jacket 0.024, helmet
0.025, against a backpack at 0.102 — so the field only ever overrode an already-correct value.
But the margin between fitted cloth and a backpack is 1.7×, and a bulky vest with pouches could
fall inside it. Removing the user's ability to correct a misclassification means the
misclassification must at least become **visible**.

**Files:**
- Modify: `scripts/a3ob/mayabridge/commands/skin.py` (the `TransferSkinCommand.doIt` loop and its `setResult`)
- Modify: `scripts/a3ob/ui/entry.py:120-126` (`_transfer_skin`)
- Create: `tests/mayapy/transfer_reports_rigid_shells.py`

**Interfaces:**
- Produces: `cmds.a3obTransferSkin(...)` returns a **two-element int list** `[meshes, rigid]`
  instead of a bare int.
- Produces: `_transfer_skin(distance=None)` in `a3ob.ui.entry` returns the tuple
  `(meshes, rigid)`. **The `distance` parameter becomes optional**: when it is `None` the flag is
  not passed at all, so the command applies `skintransfer.DEFAULT_FAR_DISTANCE` itself. That is
  what lets Task 3 delete the panel field without hard-coding `0.06` in the UI.

- [ ] **Step 1: Read the command before changing it**

Read `scripts/a3ob/mayabridge/commands/skin.py` lines 125-185. Note that `done` counts *meshes
transferred*, that the loop already binds `count, rigid` per target, and that failures inside the
loop are caught per-target. Your accumulator must only count shells from targets that actually
succeeded.

**The result-type change is the risk in this task, and it is deliberate.** Going from an int to a
two-element list changes what `cmds.a3obTransferSkin(...)` hands back to any scripted caller. The
hard contract is the command's *name and flags*, both untouched. Element 0 stays the mesh count,
so a caller doing `result[0]` is unaffected — but one doing `int(result)` on the raw return would
now fail. Grep the repo for callers before you change it, and report what you find.

- [ ] **Step 2: Write the failing test**

Create `tests/mayapy/transfer_reports_rigid_shells.py`:

```python
"""a3obTransferSkin reports rigidified shells, not just the mesh count (mayapy).

Phase 3c removes the panel's "Detached over" field: DEFAULT_FAR_DISTANCE = 0.06 was measured
on a real DayZ character (boots 0.009, trousers 0.019, jacket 0.024, helmet 0.025, backpack
0.102), so the field only ever overrode an already-correct value. But the margin between
fitted cloth and a backpack is 1.7x, and a bulky vest could fall inside it. With no field to
correct a misclassification, the misclassification has to be visible instead — so the count
the command already computes has to reach the caller.

Run:  mayapy.exe tests/mayapy/transfer_reports_rigid_shells.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_body_and_garment(garment_offset=0.0):
    """A skinned body plus one garment shell sitting `garment_offset` away from it.

    The offset is the whole point: at 0.0 the shell is fitted and follows the body's weights;
    pushed past DEFAULT_FAR_DISTANCE it is a detached shell and gets rigidified."""
    cmds.file(new=True, force=True)
    body = cmds.polyCube(name="body", width=2, height=2, depth=2, ch=False)[0]
    root = cmds.joint(name="Pelvis", position=(0, 0, 0))
    cmds.joint(name="Spine", position=(0, 1, 0))
    cmds.select(body, root, replace=True)
    cmds.skinCluster(root, body, toSelectedBones=True)

    garment = cmds.polyCube(name="garment", width=1, height=1, depth=1, ch=False)[0]
    cmds.move(0, 1.0 + garment_offset, 0, garment, absolute=True)
    return body, garment


def transfer(body, garment):
    """Select garment AND body, then transfer.

    ensure_reference -> find_reference picks the SKINNED mesh out of the selection as the
    reference, so the body being in the scene is enough. Deliberately does NOT touch the
    male_body optionVar: that is the user's real saved reference, and skin_transfer.py saves
    and restores it precisely because writing it leaks out of the test."""
    cmds.select(garment, body, replace=True)
    return cmds.a3obTransferSkin()


def test_the_result_is_a_pair():
    body, garment = build_body_and_garment()
    result = transfer(body, garment)
    check(isinstance(result, (list, tuple)) and len(result) == 2,
          "expected a two-element result, got %r" % (result,))


def test_element_zero_is_still_the_mesh_count():
    """Scripted callers reading result[0] must be unaffected by this change."""
    body, garment = build_body_and_garment()
    result = transfer(body, garment)
    check(int(result[0]) == 1, "element 0 is %r, expected the mesh count 1" % (result[0],))


def test_a_detached_shell_is_counted():
    body, garment = build_body_and_garment(garment_offset=0.5)
    result = transfer(body, garment)
    check(int(result[1]) >= 1,
          "a shell 0.5 from the body was not counted as rigidified: %r" % (result,))


def test_a_fitted_shell_reports_zero():
    """Zero must be reachable and distinct from the detached case — otherwise the number the
    panel shows carries no information."""
    body, garment = build_body_and_garment(garment_offset=0.0)
    result = transfer(body, garment)
    check(int(result[1]) == 0,
          "a fitted shell was reported as rigidified: %r" % (result,))


def test_the_ui_wrapper_returns_both_numbers():
    from a3ob.ui.entry import _transfer_skin
    body, garment = build_body_and_garment(garment_offset=0.5)
    cmds.select(garment, body, replace=True)
    meshes, rigid = _transfer_skin()
    check(meshes == 1, "wrapper reported %r meshes" % meshes)
    check(rigid >= 1, "wrapper reported %r rigid shells" % rigid)


def test_the_wrapper_omits_the_distance_flag_when_none():
    """Task 3 deletes the panel's distance field. The wrapper must then NOT pass -distance at
    all, so the command applies its own measured DEFAULT_FAR_DISTANCE — rather than the UI
    hard-coding 0.06 and silently drifting from it."""
    from a3ob.ui import entry
    seen = {}
    original = cmds.a3obTransferSkin

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return [0, 0]

    cmds.a3obTransferSkin = spy
    try:
        entry._transfer_skin()
        check("distance" not in seen,
              "the wrapper passed distance=%r when it should have omitted the flag"
              % seen.get("distance"))
        seen.clear()
        entry._transfer_skin(0.2)
        check(seen.get("distance") == 0.2,
              "an explicit distance was not forwarded: %r" % seen)
    finally:
        cmds.a3obTransferSkin = original


def main():
    for test in (test_the_result_is_a_pair,
                 test_element_zero_is_still_the_mesh_count,
                 test_a_detached_shell_is_counted,
                 test_a_fitted_shell_reports_zero,
                 test_the_ui_wrapper_returns_both_numbers,
                 test_the_wrapper_omits_the_distance_flag_when_none):
        test()
        print("ok:", test.__name__, flush=True)
    print("TRANSFER RIGID SHELLS: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 3: Run it and WITNESS the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/transfer_reports_rigid_shells.py
```

Expected: the first test fails because the result is a one-element list. **Paste the actual
output.**

If the fixture turns out not to produce a rigidified shell at 0.5 — the classifier works on
connected shells and disconnected geometry, so check `skintransfer.py` for what it actually
measures — fix the fixture rather than weakening the assertion, and say so in your report. A test
that cannot distinguish rigidified from not is worthless here, because distinguishing them is the
entire point of the task.

- [ ] **Step 4: Accumulate and return both numbers**

In `TransferSkinCommand.doIt`, add a `rigid_total = 0` accumulator beside `done`, add `rigid` to
it inside the success path of the per-target loop, and change the final result:

```python
        # A two-element result, not a bare int: element 0 stays the mesh count so existing
        # callers reading result[0] are unaffected, and element 1 carries the rigidified-shell
        # count the panel now shows. Phase 3c removed the panel's distance field, so this
        # number is the only remaining signal that a shell was classified as detached.
        self.setResult([done, rigid_total])
```

Leave the two early `self.setResult(0)` guards at lines 146 and 153 consistent with this — a
caller must not get an int in one path and a list in another. Make them `self.setResult([0, 0])`.
Check line 211 and 240 belong to a *different* command before touching them.

- [ ] **Step 5: Widen the UI wrapper**

Replace `_transfer_skin` in `scripts/a3ob/ui/entry.py` (lines 120-126):

```python
def _transfer_skin(distance=None):
    """Copy DayZ weights from the reference body onto the selected garments.

    Returns (meshes transferred, shells rigidified). ``distance`` defaults to None and the
    flag is then NOT passed: the command applies skintransfer.DEFAULT_FAR_DISTANCE, which was
    measured on a real DayZ character. Passing a copy of that number from the UI would let the
    two drift apart silently."""
    load_plugin()
    if distance is None:
        result = cmds.a3obTransferSkin()
    else:
        result = cmds.a3obTransferSkin(distance=distance)
    if not isinstance(result, (list, tuple)):
        return int(result or 0), 0
    meshes = int(result[0]) if len(result) > 0 else 0
    rigid = int(result[1]) if len(result) > 1 else 0
    return meshes, rigid
```

- [ ] **Step 6: Fix the panel's existing caller so the suite stays green**

`panels/skinning.py:106-114` unpacks a single int. Task 3 rewrites this method properly; for now
make it correct with the new return so nothing is broken between tasks:

```python
    def run_transfer_skin(self):
        try:
            distance = float(self.skin_distance_field.text())
        except (ValueError, AttributeError):
            distance = None
        meshes, rigid = _transfer_skin(distance)
        self._set_skinning_summary(
            "Transferred onto {0} mesh(es).".format(meshes) if meshes
            else "Nothing transferred — see the script editor for why.")
```

- [ ] **Step 7: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/transfer_reports_rigid_shells.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_transfer.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_weights_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

`skin_transfer.py` is the existing coverage of this command and the one most likely to assert on
the old result shape. If it fails, that failure is information — report what it asserted.

- [ ] **Step 8: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/mayabridge/commands/skin.py scripts/a3ob/ui/entry.py \
        scripts/a3ob/ui/panels/skinning.py tests/mayapy/transfer_reports_rigid_shells.py
git commit -m "feat: a3obTransferSkin reports how many shells were rigidified"
```

---

### Task 2: Select Skin Outliers moves to the Skinning panel

It sits in the Validation panel today (`panels/validation.py:29-31`) and writes a selection.
Validation is a read-only reporter; a weight tool that mutates the selection never belonged in it.

**Files:**
- Modify: `scripts/a3ob/ui/panels/validation.py` (remove the button, its hint and `run_skin_weights`)
- Modify: `scripts/a3ob/ui/panels/skinning.py` (add the button and the method)
- Modify: `tests/mayapy/p3d_workflow.py` (the dock-symbol assertions)

**Interfaces:**
- Produces: `run_skin_weights()` moves from `ValidationPanelMixin` to `SkinningPanelMixin` and
  writes its result to `self.skinning_summary` via `_set_skinning_summary`, not to
  `self.validation_summary`.
- Consumes: `_run_skin_weights()` from `a3ob.ui.entry`, unchanged.

- [ ] **Step 1: Add the absence and presence assertions first**

`tests/mayapy/p3d_workflow.py` has a function that positively asserts about twenty required dock
symbols (`assert_ui_redesign_helpers_load`) and carries retired-panel absence checks beside them.
Read it, then add — **inside that same function**, so they cannot pass vacuously if the
surrounding test stops running:

```python
    check(hasattr(dock_class, "run_skin_weights"),
          "run_skin_weights should live on the dock after moving to Skinning")
```

and a check that the Validation panel's builder no longer mentions the outlier button. Match the
file's local naming and its existing check idiom — read three neighbouring assertions and copy
their shape rather than inventing one.

Because `run_skin_weights` is a method on the same dock class either way, `hasattr` alone cannot
tell you which panel built the button. Assert on the **source** instead: read
`ValidationPanelMixin._build_validation_tab`'s code object or use `inspect.getsource` on it and
check `"Select Skin Outliers"` is absent, and present in `SkinningPanelMixin._build_skinning_tab`.
That is a real discriminator; `hasattr` is not.

- [ ] **Step 2: Run it and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

Expected: FAIL naming the Skinning panel's missing button. Record it.

- [ ] **Step 3: Remove it from Validation**

In `scripts/a3ob/ui/panels/validation.py`, delete the hint at lines 26-28, the button at lines
29-31, and the `run_skin_weights` method at lines 47-55. Leave `run_validation`,
`_populate_validation` and `_select_validation_node` alone.

- [ ] **Step 4: Add it to Skinning**

In `scripts/a3ob/ui/panels/skinning.py`, add the button after the Test Pose button, and the
method beside `run_test_pose`:

```python
        layout.addWidget(_qt_button(
            "Select Skin Outliers", self.run_skin_weights,
            "Select vertices whose weights disagree with their neighbours — transfer "
            "artefacts, invisible in bind pose. Fix them with Skin > Smooth Skin Weights.",
            ":/aselect.png"))
```

```python
    def run_skin_weights(self):
        count = _run_skin_weights()
        self._set_skinning_summary(
            "No skin weight outliers found ✓" if count == 0
            else "Selected {0} outlier vertex(es) — fix with Skin > Smooth Skin "
                 "Weights.".format(count))
```

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_weights_workflow.py
```

- [ ] **Step 6: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/ui/panels/validation.py scripts/a3ob/ui/panels/skinning.py \
        tests/mayapy/p3d_workflow.py
git commit -m "refactor: Select Skin Outliers moves to the Skinning panel"
```

---

### Task 3: the panel slims to four buttons and the influence list

**Files:**
- Modify: `scripts/a3ob/ui/panels/skinning.py`
- Modify: `tests/mayapy/p3d_workflow.py` (absence assertions)

The resulting panel, from the spec:

```
[ Add Male Character ]
[ Transfer Skin from Body ]
[ Test Pose ]
[ Select Skin Outliers ]

Filter [____________]
┌────────────────────┐
│ bone list          │
└────────────────────┘
[ Select Vertices ] [ Remove ]

<summary line>
```

**What goes, and why each:**

- **Add Skeleton** — the reference body carries its own skeleton and `ensure_reference` keeps it,
  so adding a bare skeleton is the rare case. Task 4 puts it in the submenu.
- **Save Selection as Body / as Skeleton** — `save_reference` exports with `force=True` and no
  confirmation, so a wrong selection plus one click silently replaces the asset. A destructive
  once-in-a-while action must not sit beside buttons pressed daily. Task 4 puts them in the
  submenu **with a confirmation**.
- **The `Detached over` field** — see Task 1. `a3obTransferSkin -distance` remains the escape
  hatch.
- **The four explanatory paragraphs** — with the panel down to four buttons and a list, the prose
  outweighs the interface. The detail is already in the tooltips, which is where it stays.

**Renamed:** *Add Male Body* → **Add Male Character**. It imports the body *with its materials and
its skeleton*; "Body" undersells what lands in the scene.

- [ ] **Step 1: Add the absence assertions**

In the same `p3d_workflow.py` function as Task 2, assert via `inspect.getsource` on
`SkinningPanelMixin._build_skinning_tab` that these strings are **absent**: `"Add Skeleton"`,
`"Save Selection as Body"`, `"Save Selection as Skeleton"`, `"Detached over"`, `"Add Male Body"`;
and that `"Add Male Character"` is **present**. Also assert `skin_distance_field` is not set
anywhere in that source.

Add one more, pinning a property the spec names and nothing currently tests: **`dock.py`
registers no `on_expand` callback for "Skinning"**, so expanding the panel triggers no scene
scan. Phase 1 removed the `refresh_weights_state` callback that used to be there and the entry
already reads `("Skinning", ..., None)`; assert the fourth element of that tuple is `None` so a
future edit cannot quietly reintroduce a scan. Read how `dock.py` builds the panel list before
writing the assertion — reach it through the same route the neighbouring assertions use.

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

- [ ] **Step 3: Rewrite the panel body**

Replace `_build_skinning_tab` lines 18-62 (from the first `_hint` through the Test Pose button)
with:

```python
        layout.addWidget(_qt_button(
            "Add Male Character", lambda: _add_reference_asset("male_body"),
            "Import the saved male character — mesh, materials and skeleton. "
            "Reference assets live in the MayaObjectBuilder menu under Reference Assets.",
            ":/kinJoint.png"))
        layout.addWidget(_qt_button(
            "Transfer Skin from Body", self.run_transfer_skin,
            "Select the garment, then transfer: weights come from the reference body so the "
            "garment deforms with it, and detached shells (pouches, backpacks) are made rigid. "
            "Scripted callers can override the detachment threshold with "
            "a3obTransferSkin -distance.",
            ":/smoothSkin.png"))
        layout.addWidget(_qt_button(
            "Test Pose", self.run_test_pose,
            "Bad weights are invisible in bind pose. This bends knees/elbows/shoulders, selects "
            "vertices that deform unlike their neighbours, and restores the pose.",
            ":/aselect.png"))
```

followed by the Select Skin Outliers button Task 2 added. Then delete the influence-list hint at
lines 64-67 — the list's own tooltip already says what it is, and the removal-moves-weight
detail belongs on the Remove button's tooltip, so extend that one:

```python
        influence_row.addWidget(_qt_button(
            "Remove", self.run_remove_influences,
            "Remove the highlighted bones. Their weight moves to each vertex's remaining bones "
            "— weight is never deleted, only redistributed.",
            ":/delete.png"))
```

- [ ] **Step 4: Simplify `run_transfer_skin` and report the shell count**

```python
    def run_transfer_skin(self):
        meshes, rigid = _transfer_skin()
        if not meshes:
            self._set_skinning_summary("Nothing transferred — see the script editor for why.")
            return
        # Report zero distinctly from a count: with the distance field gone, this line is the
        # only signal that a shell was classified as detached, and "0 rigid" has to be
        # readable as "nothing was treated as detached" rather than as an absent number.
        self._set_skinning_summary(
            "Transferred onto {0} mesh(es); {1} shell(s) made rigid.".format(meshes, rigid)
            if rigid else
            "Transferred onto {0} mesh(es); none detached.".format(meshes))
```

Delete `self.skin_distance_field` entirely — the attribute, the label, the tooltip and the row.
Grep for it afterwards; `dock.py` may declare it in `__init__`.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/transfer_reports_rigid_shells.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/influence_panel.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
```

`influence_panel.py` covers the part of the panel that survives — if it fails, something in the
list machinery was disturbed that should not have been.

- [ ] **Step 6: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/ui/panels/skinning.py scripts/a3ob/ui/dock.py tests/mayapy/p3d_workflow.py
git commit -m "refactor: the Skinning panel is four buttons and the influence list"
```

---

### Task 4: a Reference Assets submenu, and a guard on overwriting

This is what makes Task 3's deletions safe rather than merely tidier.

The menu is built in `entry.show_plugin_ui` (`scripts/a3ob/ui/entry.py:411-425`), which returns
immediately under `cmds.about(batch=True)`. **None of the menu itself is testable headlessly**, so
the callbacks must stay one-line wrappers and the testable part is the confirmation logic, which
lives in `_save_reference_asset`.

`KINDS` (`scripts/a3ob/mayabridge/references.py:15-19`) defines `female_body`, which has never had
any UI at all. The submenu exposes it for free and removes that inconsistency.

**Note on sequencing:** the index assigns the menu restructure to Phase 5. The submenu is built
here anyway, because Task 3 removed the only way to reach these actions and leaving them
unreachable across two phases is worse than Phase 5 restyling a submenu that already exists.

**Files:**
- Modify: `scripts/a3ob/ui/entry.py` (`_save_reference_asset`, and the menu in `show_plugin_ui`)
- Create: `tests/mayapy/reference_overwrite_guard.py`

**Interfaces:**
- Produces: `_save_reference_asset(kind)` asks before replacing an existing file, naming it, and
  returns `True` when it saved and `False` when the user declined or nothing was selected.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/reference_overwrite_guard.py`:

```python
"""Saving over an existing reference asset asks first (mayapy).

references.save_reference exports with force=True and no confirmation, so a wrong selection
plus one click silently replaces a reference the user may have spent real work on. Phase 3c
moves the save actions off the panel and into a menu submenu; the guard is what makes that
move a safety improvement rather than just a relocation.

The confirmation lives in the UI wrapper, not in references.py: mayabridge must never import
from a3ob.ui, and a dialog in the scene layer would be exactly that.

Run:  mayapy.exe tests/mayapy/reference_overwrite_guard.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

_harness.load_plugin()

from a3ob.mayabridge import references  # noqa: E402
from a3ob.ui import entry  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def scene_with_a_joint():
    cmds.file(new=True, force=True)
    joint = cmds.joint(name="Pelvis", position=(0, 0, 0))
    cmds.select(joint, replace=True)
    return joint


def existing_reference(tmpdir, contents="// placeholder\n"):
    path = os.path.join(tmpdir, "dayz_skeleton.ma")
    with open(path, "w") as handle:
        handle.write(contents)
    references.set_reference_path("skeleton", path)
    return path


class _Answer:
    """Stand in for cmds.confirmDialog, recording what it was asked."""

    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, *args, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def test_declining_leaves_the_file_untouched():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        saved = entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(answer.calls, "no confirmation was shown before overwriting")
    check(saved is False, "declining should report that nothing was saved, got %r" % saved)
    with open(path) as handle:
        check(handle.read() == "// original\n", "the reference was overwritten after declining")


def test_the_prompt_names_the_file_it_would_replace():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir)

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    text = " ".join(str(value) for call in answer.calls for value in call.values())
    check(os.path.basename(path) in text,
          "the prompt does not name the file it would replace: %r" % text)


def test_accepting_writes_the_file():
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Replace")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        saved = entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(saved is True, "accepting should report a save, got %r" % saved)
    with open(path) as handle:
        check(handle.read() != "// original\n", "the reference was not written after accepting")


def test_no_prompt_when_there_is_nothing_to_replace():
    """A first save must not ask — there is no work to lose."""
    tmpdir = tempfile.mkdtemp()
    scene_with_a_joint()
    references.set_reference_path("skeleton", os.path.join(tmpdir, "not_there_yet.ma"))

    answer = _Answer("Cancel")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    check(not answer.calls,
          "a confirmation was shown even though no existing file would be replaced")


def test_nothing_selected_still_refuses_without_writing():
    """The existing clear error must survive the new guard."""
    tmpdir = tempfile.mkdtemp()
    cmds.file(new=True, force=True)
    cmds.select(clear=True)
    path = existing_reference(tmpdir, "// original\n")

    answer = _Answer("Replace")
    original = cmds.confirmDialog
    cmds.confirmDialog = answer
    try:
        entry._save_reference_asset("skeleton")
    finally:
        cmds.confirmDialog = original

    with open(path) as handle:
        check(handle.read() == "// original\n",
              "an empty selection overwrote the reference")


def main():
    for test in (test_declining_leaves_the_file_untouched,
                 test_the_prompt_names_the_file_it_would_replace,
                 test_accepting_writes_the_file,
                 test_no_prompt_when_there_is_nothing_to_replace,
                 test_nothing_selected_still_refuses_without_writing):
        test()
        print("ok:", test.__name__, flush=True)
    print("REFERENCE OVERWRITE GUARD: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/reference_overwrite_guard.py
```

Expected: the first test fails on "no confirmation was shown before overwriting". Record it.

Note `reference_path(kind)` returns `""` when the configured file does not exist
(`references.py:29-36`), which is what makes `test_no_prompt_when_there_is_nothing_to_replace`
work. Verify that reading before relying on it.

- [ ] **Step 3: Add the guard**

Replace `_save_reference_asset` in `scripts/a3ob/ui/entry.py` (lines 185-187):

```python
def _save_reference_asset(kind):
    """Save the selection as a reference asset, asking first if one already exists.

    references.save_reference exports with force=True, so without this a wrong selection plus
    one click silently replaces a reference the user may have built by hand. The prompt lives
    here rather than in references.py because mayabridge must never import from a3ob.ui.

    Batch sessions proceed without asking: there is nobody to ask, and a script that called
    a3obReference -store asked for exactly this."""
    load_plugin()
    import os
    from a3ob.mayabridge import references

    existing = references.reference_path(kind)
    if existing and not cmds.about(batch=True):
        answer = cmds.confirmDialog(
            title="Replace reference asset?",
            message="This will replace the saved %s reference:\n\n%s\n\n"
                    "The current file will be overwritten."
                    % (references.KINDS[kind][1], os.path.basename(existing)),
            button=["Replace", "Cancel"], defaultButton="Cancel",
            cancelButton="Cancel", dismissString="Cancel")
        if answer != "Replace":
            return False
    cmds.a3obReference(kind=kind, store="1")
    return True
```

`a3obReference` already reports the "select something first" error through
`MGlobal.displayError` and writes nothing (`commands/skin.py:284-286` catches it), so the empty
selection case needs no extra code here — only the test that proves it still holds.

- [ ] **Step 4: Build the submenu**

In `show_plugin_ui`, after the `Export model.cfg Skeleton` item and before the existing divider,
add:

```python
        cmds.menuItem(divider=True, parent=menu)
        references_menu = cmds.menuItem(label="Reference Assets", parent=menu, subMenu=True,
                                        tearOff=True)
        cmds.menuItem(label="Add Male Character", parent=references_menu,
                      command=lambda *_: _add_reference_asset("male_body"))
        cmds.menuItem(label="Add Female Body", parent=references_menu,
                      command=lambda *_: _add_reference_asset("female_body"))
        cmds.menuItem(label="Add Skeleton", parent=references_menu,
                      command=lambda *_: _add_reference_asset("skeleton"))
        cmds.menuItem(divider=True, parent=references_menu)
        # Destructive: each replaces a saved asset. Separated from the Add items above by a
        # divider, and each asks before overwriting (_save_reference_asset).
        cmds.menuItem(label="Save Selection as Male Character…", parent=references_menu,
                      command=lambda *_: _save_reference_asset("male_body"))
        cmds.menuItem(label="Save Selection as Female Body…", parent=references_menu,
                      command=lambda *_: _save_reference_asset("female_body"))
        cmds.menuItem(label="Save Selection as Skeleton…", parent=references_menu,
                      command=lambda *_: _save_reference_asset("skeleton"))
        cmds.setParent("..", menu=True)
```

`cmds.setParent("..", menu=True)` closes the submenu — without it every later `menuItem` that
does not pass an explicit `parent=` lands inside it. Every item above does pass `parent=`, so this
is belt-and-braces; keep it anyway, because Phase 5 rearranges this menu and the next editor
should not have to know.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/reference_overwrite_guard.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py
```

`plugin_teardown.py` matters: it loads and unloads the plugin, which is where a menu-building
mistake would surface even though the menu itself is not built in batch.

- [ ] **Step 6: Update the docs**

The README's Skinning row (added in Phase 3b) says "Weight transfer, influence inspection and
skin-weight checks". Check it is still accurate and that nothing in `README.md`, `CLAUDE.md` or
`docs/` describes the removed buttons or the `Detached over` field.

- [ ] **Step 7: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add -A
git commit -m "feat: a Reference Assets submenu, and a guard on replacing one"
```

---

## What is deliberately NOT in this phase

- **Shipping the reference assets.** `assets/references/` with its own ADPL-SA `LICENSE`, the
  root README note, and the installer copying them into `default_directory()` is **Phase 4**, and
  is blocked on the author supplying the prepared `.ma` files. This phase only makes the actions
  reachable and safe.
- **Materials and Preferences.** `docs/plans/2026-07-20-phase3d-materials.md` covers the
  `AEshadingEngineTemplate`, the Preferences window and the Materials panel's removal. Split from
  this plan because the two halves share no file, no interface and no test.
- **Restyling the menu.** Phase 5 restructures it with `dividerLabel` sections and icons. This
  phase adds one submenu because Task 3 would otherwise leave its actions unreachable.

## Verification for the controller between tasks

```bash
python tests/run_all.py
```

Controller only. Expected after Task 4: the Phase 3b baseline of 55 plus two new files
(`transfer_reports_rigid_shells`, `reference_overwrite_guard`), all green, with the byte gate
printing real per-fixture lines rather than `SKIP`.
