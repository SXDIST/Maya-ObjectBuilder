# Phase 3d — Materials move to the Attribute Editor; preferences get their own window

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` to
> implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the Materials panel. Per-material editing moves to a **DayZ Material** section
in the Attribute Editor, where a Maya user already looks for material attributes; the two global
preferences it also held — texture root and alpha→transparency — move to a Preferences window.

**Architecture:** `a3obTexture` and `a3obMaterial` are *dynamic* attributes on the
`shadingEngine`, so Maya already shows them under Extra Attributes with no plugin code. The panel
duplicates that view and adds what Maya cannot: path pickers, recent-path history,
`_normalize_dayz_path`, immediate re-texturing, and **Select Faces** — Hypershade can select
objects by material but not faces, so that capability has no native equivalent and must survive.

**Tech Stack:** Maya 2027, Python 3, `maya.cmds` + `maya.mel`, PySide6 (`a3ob.ui._qt`).

## The mechanism, measured rather than assumed

Maya 2027 **ships** `scripts/AETemplates/AEshadingEngineTemplate.mel`. Defining our own
`AEshadingEngineTemplate` would shadow it — our `scripts/` is on `MAYA_SCRIPT_PATH` — and replace
the stock Shading Group Attributes section wholesale. **Do not write that file.**

The supported extension point is the `AETemplateCustomContent` callback hook, and it does reach
shading engines. The chain, read out of Maya's own scripts:

```
AEshadingEngineTemplate  →  AEentityTemplate  →  AEdependNodeTemplate
                                                 └─ callbacks -executeCallbacks
                                                        -hook "AETemplateCustomContent" $nodeName
```

Three facts established by probing a live `mayapy`, all of which shape the tests:

1. `cmds.callbacks(addCallback=fn, hook="AETemplateCustomContent", owner="...")` works **in
   batch**, and `cmds.callbacks(listCallbacks=True, hook=..., owner=...)` returns the registered
   function. Registration is verifiable headlessly.
2. The Python `callbacks` command has **no flag for passing the node name** — `nodeName=` raises
   `TypeError: Invalid flag 'nodeName'`. MEL passes it positionally, exactly as
   `AEdependNodeTemplate` does, so a test must drive the callback with
   `mel.eval('callbacks -executeCallbacks -hook "AETemplateCustomContent" "<node>";')`. The
   callback's signature is therefore `def callback(node_name)`.
3. `cmds.editorTemplate(beginLayout=..., ...)` **does not raise in batch** — it silently
   no-ops. So the callback body runs end to end headlessly without an Attribute Editor.

Together these make the section far more testable than the spec assumed. What still cannot be
tested is whether it *renders*; that stays on the author's live-Maya list.

## Global Constraints

- **Never run `mayapy tests/golden.py capture`.** Only `verify`. If `verify` prints `SKIP` rather
  than real per-fixture byte lines, stop and report it — two junction links are missing and every
  byte assertion is proving nothing.
- **Never run `python tests/run_all.py`** as an implementer. The controller runs the full suite.
- **Run every command in the FOREGROUND.**
- The byte contract must not move: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.
- **The `a3obTexture` / `a3obMaterial` schema entries and their short names are unchanged.**
  Nothing about where the data lives changes — only where it is edited. 33 long+short pairs,
  pinned by `tests/python/test_attr_schema.py`.
- Registered command names and their flags are a hard contract. This phase adds no command.
- **Panels must be silent reads.** `dock_panel_sync.py`, `panels_do_not_dirty_the_scene.py` and
  `dock_refresh_cost.py` guard this.
- **A test must never write into the user's real Maya folder.** Phase 3c shipped a test that
  created a junk reference in `Documents/maya/MayaObjectBuilder/references` and repointed an
  optionVar at it. Anything here that touches `MayaObjectBuilder_texture_root` or
  `MayaObjectBuilder_paa_alpha_transparency` must snapshot and restore it in a `finally` —
  `tests/mayapy/skin_transfer.py` has the idiom.
- **Callbacks must be removed before the thing they point at dies.** `entry._delete_qt_dock`
  calls this "the exit-time crash class". A callback registered in `show_plugin_ui` must be
  cleared in `hide_plugin_ui`.
- Layering: `formats` → `mayabridge` → `ui`. Nothing under `mayabridge/` may import from
  `a3ob.ui`.
- A real `QWidget` under mayapy **segfaults with no traceback** unless a `QApplication` exists
  before `maya.standalone.initialize()`; use `_built_active_dock()` / `_release_active_dock()`
  from `tests/mayapy/_harness.py`.
- **Line endings:** compare `git diff --shortstat` against `git diff --shortstat
  --ignore-cr-at-eol` **over the full range you commit**; they must agree. Edit files in place.
- `mayapy` is `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe`. Each mayapy test runs in its
  own process.

## File structure

| File | Responsibility after this phase |
|------|-------------------------------|
| `scripts/a3ob/mayabridge/paatex/resolve.py` | also reports **which** source resolved a texture |
| `scripts/a3ob/ui/actions/materials.py` | write and select take arguments; no dock reads |
| `scripts/a3ob/ui/ae_template.py` | **new leaf** — the DayZ Material AE section and its registration |
| `scripts/a3ob/ui/preferences.py` | **new leaf** — the Preferences window |
| `scripts/a3ob/ui/entry.py` | registers/clears the AE callback; opens Preferences from the menu |
| `scripts/a3ob/ui/panels/materials.py` | **deleted** |
| `scripts/a3ob/ui/dock.py` | loses the Materials panel, `_materials_snapshot` and `_material_fields_focused` |

Five tasks. Tasks 1 and 2 build seams that are fully testable. Tasks 3 and 4 build the two new
surfaces. Task 5 deletes the panel once nothing depends on it.

---

### Task 1: the resolver reports which source found the texture

The Preferences window has to state **which source actually resolved textures** — configured
root, `P:/`, or the bounded basename search — because the current situation, where a stale root
silently does nothing, must not be expressible without a warning. It is not hypothetical: the
measured scene had the root set to `…\Maya-ObjectBuilder\tests\paa`, a directory that **does not
exist**, and textures displayed anyway because the chain fell through to `P:/`.

`resolve_paa_path` (`scripts/a3ob/mayabridge/paatex/resolve.py:24`) returns only a path.

**Files:**
- Modify: `scripts/a3ob/mayabridge/paatex/resolve.py`
- Create: `tests/mayapy/texture_resolution_source.py`

**Interfaces:**
- Produces: `resolve_paa_path_with_source(texture_path)` → `(path_or_None, source)` where
  `source` is one of `"absolute"`, `"configured"`, `"drive"`, `"search"`, or `""` when nothing
  resolved.
- Unchanged: `resolve_paa_path(texture_path)` keeps its exact signature and return value, and
  becomes a one-line wrapper. **Every existing caller must keep working** — this is the import
  pipeline, and the byte gate does not cover texture resolution.

- [ ] **Step 1: Find every caller first**

```bash
grep -rn "resolve_paa_path" scripts/ tests/ --include=*.py | grep -v __pycache__
```

Put the full result in your report. Phase 1 lost a day to a deletion whose readers a plan's file
list had missed; this task changes a function the whole import path leans on.

- [ ] **Step 2: Write the failing test**

Create `tests/mayapy/texture_resolution_source.py`. It uses real temporary directories and
**must** restore the texture-root optionVar:

```python
"""The resolver reports WHICH source found a texture, not just that one was found (mayapy).

The measured scene had MayaObjectBuilder_texture_root pointing at a directory that does not
exist, and textures displayed anyway because the chain falls through to P:/. The field stated
one source while another did the work, and nothing said so. The Preferences window has to be
able to say so, which means the resolver has to report it.

Restores the texture-root optionVar in a finally: it is the user's real configuration, and a
test that leaves it pointing at a deleted temp directory has changed their environment.

Run:  mayapy.exe tests/mayapy/texture_resolution_source.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge.paatex import settings  # noqa: E402
from a3ob.mayabridge.paatex.resolve import (  # noqa: E402
    resolve_paa_path, resolve_paa_path_with_source)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_texture(directory, relative):
    path = os.path.join(directory, relative.replace("\\", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(b"\0")
    return path


def test_absolute_path_reports_absolute():
    root = tempfile.mkdtemp()
    path = make_texture(root, "direct_co.paa")
    resolved, source = resolve_paa_path_with_source(path)
    check(resolved == path, "resolved %r" % resolved)
    check(source == "absolute", "source is %r, expected 'absolute'" % source)


def test_a_hit_under_the_configured_root_reports_configured():
    root = tempfile.mkdtemp()
    make_texture(root, "mod\\data\\jacket_co.paa")
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\jacket_co.paa")
    check(resolved is not None, "nothing resolved under the configured root")
    check(source == "configured", "source is %r, expected 'configured'" % source)


def test_a_basename_hit_reports_search():
    """The file exists under the root but NOT at the relative path — the bounded walk finds
    it. That is a materially different answer from a clean relative hit and must say so."""
    root = tempfile.mkdtemp()
    make_texture(root, "somewhere\\else\\helmet_co.paa")
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\helmet_co.paa")
    check(resolved is not None, "the basename search found nothing")
    check(source == "search", "source is %r, expected 'search'" % source)


def test_nothing_found_reports_an_empty_source():
    root = tempfile.mkdtemp()
    settings.set_texture_root(root)
    resolved, source = resolve_paa_path_with_source("mod\\data\\absent_co.paa")
    check(resolved is None, "resolved %r for a texture that does not exist" % resolved)
    check(source == "", "source is %r, expected ''" % source)


def test_a_configured_root_that_does_not_exist_is_not_reported_as_configured():
    """The exact situation from the measured scene. Whatever resolves it, it is not the
    configured root, and the caller must be able to tell."""
    settings.set_texture_root(os.path.join(tempfile.mkdtemp(), "gone"))
    _resolved, source = resolve_paa_path_with_source("mod\\data\\absent_co.paa")
    check(source != "configured",
          "a nonexistent configured root was reported as the resolving source")


def test_the_old_entry_point_is_unchanged():
    """resolve_paa_path is on the import path. Its signature and answer must not move."""
    root = tempfile.mkdtemp()
    made = make_texture(root, "mod\\data\\boots_co.paa")
    settings.set_texture_root(root)
    check(resolve_paa_path("mod\\data\\boots_co.paa") == os.path.join(root, "mod", "data", "boots_co.paa")
          or resolve_paa_path("mod\\data\\boots_co.paa") == made,
          "resolve_paa_path changed its answer: %r" % resolve_paa_path("mod\\data\\boots_co.paa"))
    check(resolve_paa_path("mod\\data\\absent_co.paa") is None,
          "resolve_paa_path should still return None when nothing resolves")


def main():
    previous = settings.texture_root()
    had_var = cmds.optionVar(exists=settings.TEXTURE_ROOT_VAR)
    try:
        for test in (test_absolute_path_reports_absolute,
                     test_a_hit_under_the_configured_root_reports_configured,
                     test_a_basename_hit_reports_search,
                     test_nothing_found_reports_an_empty_source,
                     test_a_configured_root_that_does_not_exist_is_not_reported_as_configured,
                     test_the_old_entry_point_is_unchanged):
            test()
            print("ok:", test.__name__, flush=True)
    finally:
        if had_var:
            settings.set_texture_root(previous)
        else:
            cmds.optionVar(remove=settings.TEXTURE_ROOT_VAR)
    print("TEXTURE RESOLUTION SOURCE: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
```

**The `"drive"` case is deliberately untested.** It needs a real `P:/`, which the CI machine may
or may not have, and a test that silently skips is worse than an absent one. Say in your report
whether `P:/` exists on this machine; if it does, add a case, and if it does not, say so.

- [ ] **Step 3: Run it and WITNESS the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/texture_resolution_source.py
```

Expected: `ImportError` on `resolve_paa_path_with_source`. Paste it.

- [ ] **Step 4: Split the resolver**

Rewrite `resolve_paa_path` as a wrapper and move the body into the new function, keeping the
existing comments — they record why the basename search is bounded to the configured root and
never runs under `P:/`:

```python
def resolve_paa_path_with_source(texture_path):
    """Resolve a P3D texture path, and report WHICH strategy found it.

    Returns (path or None, source) where source is "absolute", "configured", "drive",
    "search" or "" — the Preferences window states this, because a configured root that does
    not exist otherwise fails silently while P:/ quietly does the work."""
    if not texture_path:
        return None, ""
    if os.path.isfile(texture_path):
        return texture_path, "absolute"
    relative = texture_path.replace("\\", "/").lstrip("/")
    configured = texture_root()
    for root in _candidate_roots():
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            same = configured and os.path.normcase(os.path.abspath(root)) == os.path.normcase(
                os.path.abspath(configured))
            return candidate, "configured" if same else "drive"
    # Last resort: search by file name, but only under the (bounded) configured root —
    # never under P:\\, which could be an enormous tree.
    if configured and os.path.isdir(configured):
        base = os.path.basename(relative).lower()
        scanned = 0
        for dirpath, _dirs, files in os.walk(configured):
            scanned += 1
            if scanned > _WALK_DIR_LIMIT:
                break
            for name in files:
                if name.lower() == base:
                    return os.path.join(dirpath, name), "search"
    return None, ""


def resolve_paa_path(texture_path):
    """Resolve a P3D texture path to a real file, or None. The import pipeline's entry point;
    signature and answer unchanged — see resolve_paa_path_with_source for the reasoning."""
    return resolve_paa_path_with_source(texture_path)[0]
```

Note the `"configured"` vs `"drive"` discrimination compares normalised absolute paths, because
`_candidate_roots` returns the configured root verbatim and `P:/` as a literal — comparing the
raw strings would call a configured root of `p:\` a drive hit.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/texture_resolution_source.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

Then run whatever the Step 1 grep named that these do not cover.

- [ ] **Step 6: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/mayabridge/paatex/resolve.py tests/mayapy/texture_resolution_source.py
git commit -m "feat: the texture resolver reports which source found the file"
```

---

### Task 2: material writes take arguments instead of reading dock widgets

`_persist_selected_material_metadata` reads `dock.material_texture_path()` and
`dock.material_rvmat_path()`; `_selected_material_metadata_item` and `select_faces_with_material`
read `dock.selected_material_metadata_item()`. The AE section has no dock, so all three need a
dock-free form.

This is the same refactor Phase 3a Task 4 applied to `create_lod_type` and
`assign_lod_to_selection` — take arguments, do not reach into widgets.

**Files:**
- Modify: `scripts/a3ob/ui/actions/materials.py`
- Modify: `scripts/a3ob/ui/panels/materials.py` (its callers pass what they used to be read for)
- Create: `tests/mayapy/material_metadata_write.py`

**Interfaces:**
- Produces: `write_material_metadata(shading_group, texture, material)` → the set of node names
  actually written, empty when every target was deleted. Normalises both paths with
  `_normalize_dayz_path`, remembers both in the recent-path history, and propagates to the
  material node and its sibling shading engines exactly as today.
- Produces: `select_faces_for_shading_group(shading_group)` → the number of faces selected.
- `_persist_selected_material_metadata()` and `select_faces_with_material()` remain, as thin
  dock-reading wrappers over the two new functions, until Task 5 deletes the panel.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/material_metadata_write.py`. Cover, at minimum:

```python
def test_writing_sets_both_attributes_on_the_shading_group():
    """A shading engine with a3obTexture/a3obMaterial takes the normalised values."""

def test_paths_are_normalised_on_the_way_in():
    """Forward slashes and a drive letter become the backslash form DayZ stores —
    _normalize_dayz_path is the single definition and must still be the one applied."""

def test_the_material_node_and_sibling_shading_groups_also_receive_it():
    """The panel wrote to every target, not just the one shading group; the AE must not
    quietly narrow that."""

def test_a_deleted_target_reports_nothing_written_rather_than_raising():

def test_selecting_faces_returns_the_count_and_selects_them():

def test_selecting_faces_on_an_unassigned_material_selects_nothing_and_warns():
```

Write each body against the real scene — build a poly cube, assign a shader, add the two
attributes — and assert on `cmds.getAttr` afterwards. Do **not** mock the shading network.

Read `tests/mayapy/material_faces.py` first: it already builds a shaded mesh fixture, and reusing
its shape keeps the two files consistent.

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_metadata_write.py
```

- [ ] **Step 3: Extract the two functions**

Move the body of `_persist_selected_material_metadata` into `write_material_metadata(
shading_group, texture, material)`, taking the item's targets from the node rather than from the
dock's cached item dict. Move `select_faces_with_material`'s body into
`select_faces_for_shading_group(shading_group)`, keeping the comment that explains why the scope
is read *before* selecting — computing the shapes afterwards would scope the result to its own
output.

Keep both old names as wrappers so `panels/materials.py` is untouched by this task:

```python
def _persist_selected_material_metadata():
    item = _selected_material_metadata_item()
    dock = _active_qt_dock()
    if not item or dock is None:
        return None
    written = write_material_metadata(item["material_node"] or (item["shading_groups"] or [None])[0],
                                      dock.material_texture_path(), dock.material_rvmat_path())
    ...
```

Work out the exact wrapper from the code you find — the point is that **no new behaviour changes
here**, only where the values come from. If the existing item-dict shape makes a faithful wrapper
awkward, say so in your report rather than changing what the panel does.

- [ ] **Step 4: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_metadata_write.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

- [ ] **Step 5: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/ui/actions/materials.py tests/mayapy/material_metadata_write.py
git commit -m "refactor: material writes take arguments instead of reading the dock"
```

---

### Task 3: the DayZ Material section in the Attribute Editor

**Files:**
- Create: `scripts/a3ob/ui/ae_template.py`
- Modify: `scripts/a3ob/ui/entry.py` (register in `show_plugin_ui`, clear in `hide_plugin_ui`)
- Create: `tests/mayapy/ae_material_section.py`

**Interfaces:**
- Produces: `should_show_section(node_name)` → bool. The Qt-free, AE-free decision seam: true only
  for a `shadingEngine` that carries `a3obTexture` or `a3obMaterial`. **A silent read** — it runs
  for every node the user selects in the Attribute Editor.
- Produces: `build_section(node_name)` — the callback. Returns immediately when
  `should_show_section` is false.
- Produces: `install()` / `uninstall()` — register and clear the callback under the owner
  `"MayaObjectBuilder"`.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/ae_material_section.py`. The three probed facts above are what make it
possible; encode them in its docstring so the next reader does not re-derive them.

```python
"""The DayZ Material AE section registers, and fires only for a3ob shading engines (mayapy).

Maya 2027 SHIPS AEshadingEngineTemplate.mel, so defining our own would shadow it and replace
the stock Shading Group Attributes section. The supported extension point is the
AETemplateCustomContent hook, and it does reach shading engines:

    AEshadingEngineTemplate -> AEentityTemplate -> AEdependNodeTemplate
                                                   `- callbacks -executeCallbacks
                                                        -hook "AETemplateCustomContent" $nodeName

Three things measured on a live mayapy, which is why this file can exist at all:
  * cmds.callbacks(addCallback=..., hook=..., owner=...) works in batch, and listCallbacks
    returns the function, so registration is verifiable.
  * the Python callbacks command has NO flag for the node name (nodeName= raises
    "Invalid flag"), so the callback must be driven the way MEL drives it — positionally,
    through mel.eval.
  * cmds.editorTemplate(...) does not raise in batch, it no-ops, so the body runs end to end.

What is NOT testable here is whether the section RENDERS. That stays on the author's
live-Maya list.

Run:  mayapy.exe tests/mayapy/ae_material_section.py
"""
```

Cover:

```python
def test_install_registers_under_our_owner():
    """listCallbacks returns the function for hook AETemplateCustomContent, owner
    MayaObjectBuilder."""

def test_uninstall_removes_it():
    """A callback that outlives what it points at is the exit-time crash class."""

def test_installing_twice_registers_one_callback():
    """show_plugin_ui can run more than once in a session; a second install must not stack a
    duplicate that then builds the section twice."""

def test_the_section_is_offered_for_an_a3ob_shading_engine():
    """Drive it the way MEL does and assert build_section ran for the node."""

def test_the_section_is_not_offered_for_a_plain_shading_engine():
    """initialShadingGroup carries no a3ob attributes and must be left alone."""

def test_the_section_is_not_offered_for_a_mesh_or_a_material_node():
    """The hook fires for EVERY node type. A section that appeared on a transform would be
    both wrong and, on a big scene, expensive."""

def test_the_decision_does_not_dirty_the_scene():
    """It runs on every Attribute Editor selection change."""
```

Drive the callback exactly as Maya does:

```python
import maya.mel as mel
mel.eval('callbacks -executeCallbacks -hook "AETemplateCustomContent" "%s";' % node)
```

- [ ] **Step 2: Run and witness the red**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/ae_material_section.py
```

- [ ] **Step 3: Write `scripts/a3ob/ui/ae_template.py`**

A **leaf**: `maya.cmds`, `maya.mel` and `a3ob.ui.recent` only. It must NOT import from
`a3ob.ui.actions` at module level — every module there star-imports `a3ob.ui.entry`, and closing
that cycle is what `entry._build_qt_dock`'s lazy import exists to prevent. Import the write
helpers from Task 2 **inside** the functions that use them.

The section holds, per the spec:

- **Texture** — path picker with browse, clear and the existing `recent_key="texture"` history.
- **Material** — the same with `recent_key="rvmat"`.
- **Select Faces** — the faces this material is assigned to. Hypershade can select objects by
  material but not faces, so this has no native equivalent and must survive the panel.

Editing writes through the same path as today: normalise, store on the shading engine, re-resolve
the texture. **Edits stay instant — there is no Apply button now and none is added.**

Use `editorTemplate -callCustom` with a new/replace proc pair, the idiom every stock template
uses (`AEshadingEngineTemplate.mel:72-79` is a worked example). The controls themselves are
`cmds.rowLayout` / `cmds.textFieldButtonGrp` — plain Maya UI, not Qt, because they live inside
Maya's own Attribute Editor layout.

- [ ] **Step 4: Register and unregister**

In `entry.show_plugin_ui`, after the menu is built:

```python
    from a3ob.ui import ae_template
    ae_template.install()
```

and in `entry.hide_plugin_ui`, **before** the dock is deleted:

```python
    from a3ob.ui import ae_template
    ae_template.uninstall()
```

Both imports are function-local for the same reason as everywhere else in this file.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/ae_material_section.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

`plugin_teardown.py` is the one that matters: it loads and unloads the plugin, which is where a
callback that outlives its owner shows up.

- [ ] **Step 6: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add scripts/a3ob/ui/ae_template.py scripts/a3ob/ui/entry.py tests/mayapy/ae_material_section.py
git commit -m "feat: a DayZ Material section in the Attribute Editor"
```

---

### Task 4: the Preferences window

**Files:**
- Create: `scripts/a3ob/ui/preferences.py`
- Modify: `scripts/a3ob/ui/entry.py` (a Preferences menu entry; the existing *Set Texture Root* item goes)
- Create: `tests/mayapy/preferences_texture_root.py`

**Interfaces:**
- Produces: `texture_root_status()` → a dict `{"root": str, "exists": bool, "message": str}`.
  The **testable seam**; the window only displays it. A configured root that does not exist must
  be reported as such.
- Produces: `resolution_source_label(texture_path)` → a human string naming which source
  resolved a texture, built on Task 1's `resolve_paa_path_with_source`.
- Produces: `show_preferences()` — opens the window. Not testable headlessly.

The window holds exactly two settings, both still optionVars. Only where they are edited changes:

- **Texture root**, with validation. A configured path that does not exist is reported as such,
  and the window states which source actually resolved textures. **The current situation, where
  a stale root silently does nothing, must not be expressible without a warning.**
- **Alpha → transparency**, unchanged in behaviour and **still off by default**: a DayZ `_ca`
  alpha is often a data channel rather than a cut-out, and wiring it makes solid armour
  see-through.

- [ ] **Step 1: Write the failing test**

Create `tests/mayapy/preferences_texture_root.py`, covering `texture_root_status` and the alpha
default. It **must** snapshot and restore both optionVars in a `finally` — see the Global
Constraints; Phase 3c shipped a test that changed the user's real configuration.

```python
def test_an_unset_root_is_reported_as_unset():
def test_a_configured_root_that_exists_is_reported_as_present():
def test_a_configured_root_that_does_NOT_exist_says_so():
    """The measured scene's exact state. The message must name the problem, not stay silent."""
def test_alpha_transparency_defaults_to_off():
    """A DayZ _ca alpha is often a data channel; on by default makes solid armour
    see-through."""
def test_toggling_alpha_transparency_round_trips():
```

- [ ] **Step 2: Run and witness the red**

- [ ] **Step 3: Write `scripts/a3ob/ui/preferences.py`**

A leaf, like `dialogs.py`: Qt and `maya.cmds` only, no import from `a3ob.ui.actions`. Reuse the
dock's `_path_picker` if the window has a dock to borrow it from; if not, build the row directly
and say so in your report rather than duplicating `_path_picker` wholesale.

Applying a new root must call `_paatex.assign_pending_textures()` exactly as the panel's
`_on_texture_root_edited` does today, and toggling alpha must call
`_paatex.apply_alpha_transparency_setting()` — the setting applies to materials already in the
scene, not only to future imports.

- [ ] **Step 4: Wire it into the menu**

Replace the existing `Set Texture Root (.paa)…` item in `entry.show_plugin_ui` with a
**Preferences…** item opening the window. The texture root is one of the two things the window
holds, so a separate menu item for it is now a second door to the same setting.

- [ ] **Step 5: Run the tests**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/preferences_texture_root.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/texture_resolution_source.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

- [ ] **Step 6: Check line endings, then commit**

```bash
git add scripts/a3ob/ui/preferences.py scripts/a3ob/ui/entry.py \
        tests/mayapy/preferences_texture_root.py
git commit -m "feat: a Preferences window for the texture root and alpha transparency"
```

---

### Task 5: retire the Materials panel

With editing in the Attribute Editor and preferences in their own window, nothing is left.

This also removes the Materials branch from the dock's live-refresh machinery:
`_materials_snapshot` (which builds a tuple over every material node of the selection on **each
scene change**), `_material_fields_focused` (which defers refreshes while a path field has focus)
and the `"Materials"` case in `_refresh_dirty_panels`. One of the polled panels disappears, and
with it the deferral hack that existed only because a refresh could overwrite what the user was
typing.

**Files:**
- Delete: `scripts/a3ob/ui/panels/materials.py`
- Modify: `scripts/a3ob/ui/dock.py`, `scripts/a3ob/ui/panels/__init__.py`, `scripts/a3ob/ui/watch.py`
- Modify: `scripts/a3ob/ui/actions/materials.py` (the dock-reading wrappers go)
- Modify: `tests/mayapy/p3d_workflow.py`, `tests/mayapy/dock_refresh_cost.py`
- Modify: `README.md`, and `CLAUDE.md` / `docs/` if they name the panel

- [ ] **Step 1: Sweep before deleting**

```bash
grep -rn "MaterialsPanelMixin\|_build_materials_tab\|material_texture\|material_rvmat\|material_list\|material_items\|_materials_snapshot\|_material_fields_focused\|refresh_material_metadata\|selected_material_metadata_item\|material_texture_path\|material_rvmat_path" \
  scripts/ tests/ plug-ins/ install/ docs/ CLAUDE.md README.md | grep -v __pycache__
```

Full result in your report. Note that `_selected_material_metadata_item`,
`_persist_selected_material_metadata` and `select_faces_with_material` are the dock-reading
wrappers Task 2 kept alive **for this panel only** — they go too, but `write_material_metadata`
and `select_faces_for_shading_group` stay, because the AE section calls them.

- [ ] **Step 2: Add the absence assertions**

In `assert_ui_redesign_helpers_load` in `tests/mayapy/p3d_workflow.py` — the function that
already positively asserts about twenty dock symbols and carries the retired-panel checks beside
them, so they cannot pass vacuously. It uses `if …: raise RuntimeError(…)`, not a `check()`
helper, and reaches methods through `dock_class`, because the mixin class names are not in its
runpy namespace.

Assert `_build_materials_tab`, `refresh_material_metadata` and `_materials_snapshot` are gone,
and that the surviving panel list has **five** entries.

- [ ] **Step 3: Run and witness the red**

- [ ] **Step 4: Delete**

```bash
git rm scripts/a3ob/ui/panels/materials.py
```

Then unwire `MaterialsPanelMixin` from `dock.py`'s base list, remove the `("Materials", …)` panel
entry, the widget attributes it owned, `_materials_snapshot`, `_material_fields_focused` and the
`"Materials"` poll branch. Check `watch.py` for a Materials hint the way Phase 3a Task 2 found a
dead `NAMED` one.

**Leave `scripts/a3ob/ui/actions/materials.py` itself in place** — it still holds
`write_material_metadata` and `select_faces_for_shading_group`, which the AE section needs.

- [ ] **Step 5: Prove the refresh cost went with it**

`dock_refresh_cost.py` exists because panels rebuild from the selected LOD and that scans every
objectSet. The Materials branch walked the selection's material nodes on **every scene change**.
Add a case asserting that no longer happens — the spec names this explicitly. Read how the file
measures cost today and follow it; if it cannot express this, say so rather than inventing a
measurement that proves nothing.

- [ ] **Step 6: Run the suite pieces**

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/panels_do_not_dirty_the_scene.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/ae_material_section.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```

- [ ] **Step 7: Update the docs**

The README panel table must lose its Materials row and drop to five panels. Its texture-root tip
currently says to set the root **in the Materials panel** — that is now the Preferences window.
Check `CLAUDE.md` and `docs/` too; Phase 1's final review found `CLAUDE.md` stale in three places
because no task owned it.

- [ ] **Step 8: Check line endings, then commit**

```bash
git diff --shortstat
git diff --shortstat --ignore-cr-at-eol
git add -A
git commit -m "refactor: retire the Materials panel"
```

---

## Decisions carried from the spec — do not relitigate

- **The attributes live on the `shadingEngine`, not on the material node.** In Hypershade one
  usually clicks the material, so the section appears only after selecting the shading group.
  This is a real cost of the move and is **accepted rather than hidden**.
- **Mirroring the attributes onto the material node is rejected.** It creates two places holding
  the same value — precisely the failure mode removed from weight storage in Phase 1. If the
  wrinkle proves painful in use, the follow-up is a template on the material node types that
  *reads through* to the connected shading engine — one source, two views — not a second copy.
- **Alpha → transparency stays off by default.**
- Whether the PAA decode cache (`a3ob_paa_cache_v3`) deserves controls in the Preferences window
  is **left open**. It is a real question, but it is about the cache, not about materials.

## Verification for the controller between tasks

```bash
python tests/run_all.py
```

Controller only. Expected after Task 5: the Phase 3c baseline of 58 plus four new files
(`texture_resolution_source`, `material_metadata_write`, `ae_material_section`,
`preferences_texture_root`), all green, with the byte gate printing real per-fixture lines.
