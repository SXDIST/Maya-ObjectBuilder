# Phase 3d fix — the AE section, rebuilt on a mechanism that works

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The DayZ Material section in the Attribute Editor actually shows and edits
`a3obTexture` / `a3obMaterial`, and Select Faces keeps working from a home that is not the AE.

**Architecture:** `editorTemplate -addControl` with a `-label` override and a change command,
instead of the `-callCustom` proc pair. Maya then owns the controls and re-points them itself,
which deletes every piece of per-tab bookkeeping the old design needed.

**Tech Stack:** Maya 2027, Python 3, `maya.cmds` + `maya.mel`.

## Why this rewrite exists — measured in a live session, not inferred

The shipped section renders an **empty frame** on every shading engine, marked or not. Verified on
screen, twice, and diagnosed with the hook confirmed firing (`build == ["jacketSG"]`, a real UI
parent, `procs == []`, `_SECTIONS == {}`):

**`editorTemplate -callCustom` never fires from inside the `AETemplateCustomContent` hook.**
`beginLayout`/`endLayout` do take effect — hence a frame containing nothing.

The headless suite could not catch this: `cmds.editorTemplate` no-ops in batch. The plan that
built it recorded "only RENDERING is untestable"; what was actually untestable was whether the
controls exist at all.

Measured, in live Maya, with the AE's **Copy Tab** button as a repeatable template rebuild:

| Mechanism | Result |
|---|---|
| `-callCustom` | never invoked |
| `-addControl` | works — fields render, populated, inside our frame |
| `-label` override | works: "Texture" / "Material", not Maya's "A 3ob Texture" |
| change command | fires, and receives the **node name** |
| native field re-pointing | automatic — Maya owns it |
| raw UI into the hook's parent | renders everything, but **cannot re-point** |

That last row is why the obvious fix was rejected: the hook fires once per node type per tab, so
raw UI stays bound to the first shading engine shown and a later edit writes to the wrong node —
the same defect class Phase 3d already fixed once, but guaranteed rather than multi-tab-only.

## Global Constraints

- **The `a3obTexture` / `a3obMaterial` schema entries and their short names are unchanged.** Only
  the editor moves. 33 long+short pairs, pinned by `tests/python/test_attr_schema.py`.
- **`should_show_section` must stay a SILENT read** — it runs for every node the user selects in
  the Attribute Editor. No warning, no write, no scene dirt.
- **A callback registered in `show_plugin_ui` must be cleared in `hide_plugin_ui`** — the
  exit-time crash class named in `entry._delete_qt_dock`.
- **Do not create `scripts/AETemplates/AEshadingEngineTemplate.mel` or any file by that name.**
  Maya 2027 ships its own and our `scripts/` is on `MAYA_SCRIPT_PATH`; ours would shadow it and
  destroy the stock Shading Group Attributes section.
- **Layering:** `ae_template` must not import `a3ob.ui.actions` at module level — every module
  there star-imports `a3ob.ui.entry`, and that cycle is what `entry._build_qt_dock`'s lazy import
  exists to prevent. Function-local imports only. Nothing under `mayabridge/` may import `a3ob.ui`.
- **Never run `python tests/run_all.py`** as an implementer. The controller runs the full suite.
- **Never run `mayapy tests/golden.py capture`.** Only `verify`.
- **Run every command in the FOREGROUND.**
- The byte contract must not move: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
- A real `QWidget` under mayapy segfaults with no traceback unless a `QApplication` exists before
  `maya.standalone.initialize()`. The AE section is plain Maya UI, never Qt.
- **Line endings:** the repo has no `.gitattributes` and genuinely mixed line endings. Edit in
  place; before committing confirm `git diff --shortstat` and `--ignore-cr-at-eol` agree.
- `mayapy` is `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe`.

## What headless tests can and cannot prove here

`cmds.editorTemplate` no-ops in batch, so **no test can prove the controls render.** That is
exactly what let the broken version ship. Tests must therefore pin what they *can*: that the hook
is registered and cleared, that `should_show_section` discriminates and stays silent, and that the
change-command handler writes what it should when called directly with a node name. Everything
else goes on the live-Maya checklist, and the author must run it before this is called done.

## File structure

| File | Responsibility after this fix |
|------|-------------------------------|
| `scripts/a3ob/ui/ae_template.py` | declares the section with `addControl`; handles edits; **loses** `_SECTIONS`, `_resolve_section`, `section_new`/`section_replace`, the MEL procs, `_path_row`, `_manage_layout` |
| `scripts/a3ob/ui/entry.py` | a **Select Faces by Material** menu item |
| `tests/mayapy/ae_material_section.py` | rewritten for the new mechanism |

Two tasks.

---

### Task 1: the section is declared with `addControl`

**Files:**
- Modify: `scripts/a3ob/ui/ae_template.py`
- Modify: `tests/mayapy/ae_material_section.py`

**Interfaces:**
- Keeps: `should_show_section(node_name)`, `build_section(node_name)`, `install()`, `uninstall()`.
- Produces: `on_attribute_edited(node_name)` — the change command. Reads both attributes off the
  node, normalises them, and persists through `write_material_metadata` (imported **inside** the
  function). Returns the set of node names written, so it is testable without any UI.
- Removes: `section_new`, `section_replace`, `_SECTIONS`, `_register_section`,
  `_forget_dead_sections`, `_resolve_section`, `_repoint`, `_manage_layout`, `_path_row`,
  `_field_text`, `_select_faces`, `_write_from_controls`, `_MEL_PROCS`, `NEW_PROC`,
  `REPLACE_PROC`. Grep before deleting each — some may be referenced by the test file.

- [ ] **Step 1: Sweep before deleting**

```bash
grep -rn "section_new\|section_replace\|_SECTIONS\|_resolve_section\|_repoint\|_manage_layout\|_path_row\|NEW_PROC\|REPLACE_PROC\|_write_from_controls\|_select_faces" \
  scripts/ tests/ docs/ CLAUDE.md README.md | grep -v __pycache__
```

Put the full result in your report.

- [ ] **Step 2: Write the failing test**

Rewrite `tests/mayapy/ae_material_section.py`. Its docstring must record why the old mechanism
went, so nobody restores it:

```python
"""The DayZ Material AE section registers, discriminates, and writes edits (mayapy).

The section used to be declared with `editorTemplate -callCustom`. Measured in a live Maya 2027
session: **callCustom never fires from inside the AETemplateCustomContent hook.** beginLayout and
endLayout DO take effect, so the section rendered as an empty frame on every shading engine,
marked or not, and no headless test could see it — cmds.editorTemplate no-ops in batch.

`-addControl` does work, takes a `-label` override, and its change command fires with the NODE
name. Maya then re-points the controls itself when the AE switches nodes, which is why every trace
of per-tab section bookkeeping is gone.

What this file CANNOT prove is that anything renders. That stays on the author's live-Maya list.

Run:  mayapy.exe tests/mayapy/ae_material_section.py
"""
```

Cover, at minimum:

```python
def test_install_registers_under_our_owner():
def test_uninstall_removes_it():
def test_installing_twice_registers_one_callback():
def test_the_section_is_offered_for_an_a3ob_shading_engine():
def test_the_section_is_not_offered_for_a_plain_shading_engine():
def test_the_section_is_not_offered_for_a_mesh_or_a_material_node():
def test_the_decision_is_silent_and_does_not_dirty_the_scene():
    """Needs a positive control in this same file, or it passes vacuously the moment the
    listener stops working. dock_panel_sync.py's test_list_influences_is_silent is the pattern."""

def test_an_edit_persists_both_paths_normalised():
    """on_attribute_edited(node) is the change command's whole job — call it directly."""
def test_an_edit_on_a_node_that_lost_its_attributes_writes_nothing_and_does_not_raise():
```

Drive the hook exactly as Maya does — positionally, through MEL, because the Python `callbacks`
command has no flag for the node name:

```python
mel.eval('callbacks -executeCallbacks -hook "AETemplateCustomContent" "%s";' % node)
```

- [ ] **Step 3: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/ae_material_section.py
```

- [ ] **Step 4: Rewrite the declaration**

`build_section` keeps its shape — return early unless the node is a `shadingEngine`. Note the
predicate asymmetry is now **gone**: with `addControl` there is no cached-template problem to work
around, because Maya re-points native controls itself. So the section may be declared only when
`should_show_section(node_name)` is true, and a plain shading engine gets nothing at all — which
also removes the empty-frame-on-plain-materials defect the live check found.

The declaration, measured working:

```python
def _begin_section(node_name):
    """Declare the section with native controls.

    `-callCustom` is NOT used: measured in live Maya, its procs never fire from inside the
    AETemplateCustomContent hook, which is what made this section render as an empty frame.
    `-addControl` works, `-label` overrides Maya's auto-prettified "A 3ob Texture", and the
    change command receives the node name. Maya re-points these controls on its own.
    """
    cmds.editorTemplate(beginLayout=SECTION_LABEL, collapse=False)
    for attribute, label in ((SG_TEXTURE, "Texture"), (SG_MATERIAL, "Material")):
        cmds.editorTemplate(attribute, CHANGE_PROC, addControl=True, label=label)
    cmds.editorTemplate(endLayout=True)
```

Use the schema constants rather than the string literals the old file hardcoded — read
`mayabridge/attributes.py` for their names and import them properly.

The change command still needs a MEL shim, because `editorTemplate` takes a proc name:

```python
_MEL_PROCS = """
global proc %(change)s(string $node) {
    python("import a3ob.ui.ae_template as _a3ob_ae; _a3ob_ae.on_attribute_edited('" + $node + "')");
}
""" % {"change": CHANGE_PROC}
```

`on_attribute_edited(node_name)` reads both attributes off the node, and persists through
`write_material_metadata(node, texture, material)` — imported inside the function. That helper
already normalises both paths, remembers them in the recent history, fans out to the material node
and its sibling shading engines, and guards a node that is neither kind.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/ae_material_section.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_metadata_write.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

- [ ] **Step 6: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/ui/ae_template.py tests/mayapy/ae_material_section.py
git commit -m "fix: the AE section uses addControl - callCustom never fires from the hook"
```

---

### Task 2: Select Faces gets a home outside the Attribute Editor

`select_faces_for_shading_group` survives — the spec is explicit that Hypershade can select objects
by material but not faces, so this capability has no native equivalent and must not be lost. It
cannot live in the AE section any more: `addControl` renders only attribute fields, and raw UI in
the hook cannot re-point.

**Files:**
- Modify: `scripts/a3ob/ui/entry.py`
- Create: `tests/mayapy/select_faces_from_selection.py`

**Interfaces:**
- Produces: `select_faces_for_selected_material()` in `scripts/a3ob/ui/actions/materials.py` →
  resolves the shading engine from the **current selection** at call time (a selected
  `shadingEngine`, or the one a selected material feeds) and delegates to
  `select_faces_for_shading_group`. Returns the face count. Warns and returns 0 when the selection
  names no material.

Resolving from the live selection rather than a stored node is the point: it has no binding to go
stale, which is the defect that killed the in-AE approach.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/select_faces_from_selection.py`. It needs `_harness.load_plugin()` only if it
calls an `a3ob*` command — it does not, so it should not. Cover:

```python
def test_a_selected_shading_engine_resolves_to_itself():
def test_a_selected_material_resolves_to_its_shading_engine():
def test_a_selection_with_no_material_warns_and_selects_nothing():
def test_the_faces_selected_are_the_ones_the_material_is_assigned_to():
    """Reuse material_faces.py's fixture shape; it already builds a shaded mesh."""
```

Remember `cmds.select(some_set)` selects the set's MEMBERS, not the set node — pass
`noExpand=True`. That bit twice in Phase 3b, once in production code.

- [ ] **Step 2: Run and witness the red**

- [ ] **Step 3: Implement, and wire the menu**

Add the resolver to `actions/materials.py` beside `select_faces_for_shading_group`. In
`entry.show_plugin_ui`, add a **Select Faces by Material** item. Menu callbacks must stay one-line
wrappers over functions that are testable — `show_plugin_ui` returns immediately under
`cmds.about(batch=True)`, so no headless test can reach the item itself.

- [ ] **Step 4: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/select_faces_from_selection.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

- [ ] **Step 5: Update the docs, check line endings, commit**

README and `docs/specs/2026-07-20-materials-into-attribute-editor-design.md` describe an AE section
with path pickers and a Select Faces button. Correct them to what now exists, and say why —
`callCustom` does not fire from the hook.

```bash
git add -A
git commit -m "feat: Select Faces moves to the menu, resolved from the selection"
```

---

## Accepted losses — do not relitigate

- **No browse button and no recent-paths dropdown inside the AE.** `addControl` renders an
  attribute field and nothing else. The field accepts typing and paste, `write_material_metadata`
  still records every path in the recent history for the pickers that remain elsewhere, and the
  texture root lives in the Preferences window.
- **The section no longer appears on a plain shading engine at all**, which is strictly better than
  the empty frame the live check found.

## Live-Maya checklist — this fix is NOT done until the author has run it

Headless tests cannot see any of this; that is precisely how the broken version shipped.

1. On an `a3ob` shading engine, the **DayZ Material** section shows **Texture** and **Material**
   with the node's real values, labelled exactly that — not "A 3ob Texture".
2. On a plain shading engine (`initialShadingGroup`) there is **no DayZ Material section at all**.
3. Selecting a *different* a3ob shading engine in the same AE tab **re-points the fields** to the
   new node's values. This is the defect that killed the alternative design — verify it directly.
4. Typing a path and pressing Enter writes it, normalised to the backslash form, and re-textures.
5. Nothing writes `a3obTexture`/`a3obMaterial` onto a node the plugin never marked.
6. The stock **Shading Group Attributes** section is intact.
7. **Select Faces by Material** selects the right faces with a shading engine selected, and with
   just the material selected.
8. The Script Editor stays silent while clicking around a busy scene with the AE open.

## Verification for the controller between tasks

```bash
python tests/run_all.py
```

Expected after Task 2: the current 65 plus one new file (`select_faces_from_selection`), all
green, with the byte gate printing real per-fixture lines.
