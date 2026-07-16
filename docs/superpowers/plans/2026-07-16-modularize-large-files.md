# Modularize Large Files Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the six largest source files into packages of ~100–250-line modules without changing behavior, public `a3ob*` command names, the attribute schema, or test results.

**Architecture:** Pure code relocation. Each oversized module becomes a package directory whose `__init__.py` re-exports the names its consumers already import, so `plug-ins/`, `a3ob.mayabridge.translator`, and the `runpy`-based mayapy tests keep working unchanged. `objectBuilderMenu.py` and `objectBuilderAutoLOD.py` stay as thin facades that re-export from the new packages. The dock class is split by panel into mixin classes.

**Tech Stack:** Python 3 (Maya 2027), PySide6, maya.cmds / maya.api.OpenMaya. Validation: `py_compile` + `tests/python/*` format tests + both `tests/mayapy/*` workflows + live-Maya smoke for UI steps.

## Global Constraints

- Do NOT change: `a3ob*` command names/flags, the `a3ob*` attribute schema, import/export logic, axis/UV conventions.
- Do NOT split `scripts/a3ob/formats/p3d.py` or `formats/model_cfg.py` (cohesive, test-covered).
- Move function/class bodies **verbatim** — no logic edits during relocation.
- Every package's `__init__.py` MUST re-export the exact names its consumers import (see each task).
- Low-level modules (scene, widgets, constants) MUST NOT import dock/actions at module top; import `_active_qt_dock` lazily inside functions where needed (avoid import cycles).
- Commit per package only after: `py_compile` clean + both mayapy workflows green (`p3d_workflow` = 14 `^OK ` lines, 0 tracebacks; `model_cfg_workflow` ends `OK model.cfg joints=18 root=Hip`). Stage precisely (`git add <the package + facade>`), never `git add -A`.
- Execution order is fixed low-risk → high-risk: commands → scene → autolod → import_/export → ui.
- Spec: `docs/superpowers/specs/2026-07-16-modularize-large-files-design.md`.

## Validation snippets (referenced by every task)

```bash
# PYCHECK
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py scripts/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py
# WORKFLOWS
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py > /tmp/wf.log 2>&1; echo "p3d exit=$? OK=$(grep -cE '^OK ' /tmp/wf.log) tb=$(grep -c Traceback /tmp/wf.log)"
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py 2>&1 | tail -1
```
Expected: PYCHECK silent (exit 0); `p3d exit=0 OK=14 tb=0`; `OK model.cfg joints=18 root=Hip`.

---

## Task 1: `commands.py` → `a3ob/mayabridge/commands/` package

**Files:**
- Create: `scripts/a3ob/mayabridge/commands/__init__.py`, `base.py`, `validate.py`, `mass.py`, `material.py`, `flag.py`, `components.py`, `lod.py`, `proxy.py`, `named_property.py`, `update_proxy.py`
- Delete: `scripts/a3ob/mayabridge/commands.py`
- Verify consumer: `plug-ins/MayaObjectBuilder.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `from a3ob.mayabridge.commands import (ValidateCommand, SetMassCommand, SetMaterialCommand, SetFlagCommand, FindComponentsCommand, CreateLODCommand, ProxyCommand, NamedPropertyCommand, UpdateProxyCommand)` keeps resolving.

- [ ] **Step 1: Inventory the module**

Run: `grep -nE "^class |^def |^[A-Z_]+ =" scripts/a3ob/mayabridge/commands.py`
Record each top-level class (the 9 `*Command`s), shared free functions, and module constants/imports. Note which free functions are called by 2+ commands (→ `base.py`) vs one command (→ that command's file).

- [ ] **Step 2: Create `base.py` with shared code**

Move the module's imports header, module constants, and every shared helper (e.g. `closed_face_islands`, `selected_components`, `create_material_nodes`, component/undo helpers used by more than one command) into `scripts/a3ob/mayabridge/commands/base.py` verbatim. Keep its own imports (`maya.api.OpenMaya`, `attributes`, `p3d`, etc.).

- [ ] **Step 3: Create one module per command**

For each command class, create `scripts/a3ob/mayabridge/commands/<name>.py` containing that class verbatim plus `from a3ob.mayabridge.commands.base import <helpers it uses>` and any direct Maya imports it needs. Mapping: `validate.py`←ValidateCommand, `mass.py`←SetMassCommand, `material.py`←SetMaterialCommand, `flag.py`←SetFlagCommand, `components.py`←FindComponentsCommand, `lod.py`←CreateLODCommand, `proxy.py`←ProxyCommand, `named_property.py`←NamedPropertyCommand, `update_proxy.py`←UpdateProxyCommand.

- [ ] **Step 4: Write `__init__.py` re-export**

```python
"""a3ob* MPxCommand implementations (one module per command)."""

from a3ob.mayabridge.commands.validate import ValidateCommand
from a3ob.mayabridge.commands.mass import SetMassCommand
from a3ob.mayabridge.commands.material import SetMaterialCommand
from a3ob.mayabridge.commands.flag import SetFlagCommand
from a3ob.mayabridge.commands.components import FindComponentsCommand
from a3ob.mayabridge.commands.lod import CreateLODCommand
from a3ob.mayabridge.commands.proxy import ProxyCommand
from a3ob.mayabridge.commands.named_property import NamedPropertyCommand
from a3ob.mayabridge.commands.update_proxy import UpdateProxyCommand

__all__ = [
    "ValidateCommand", "SetMassCommand", "SetMaterialCommand", "SetFlagCommand",
    "FindComponentsCommand", "CreateLODCommand", "ProxyCommand",
    "NamedPropertyCommand", "UpdateProxyCommand",
]
```

(Adjust the exact class names to those found in Step 1 if any differ.)

- [ ] **Step 5: Delete the old module**

Run: `git rm scripts/a3ob/mayabridge/commands.py`

- [ ] **Step 6: Verify the plugin still imports the classes**

Run: `grep -nE "commands|Command" plug-ins/MayaObjectBuilder.py | head`
Confirm it does `from a3ob.mayabridge.commands import ...` or `import a3ob.mayabridge.commands as ...` and uses class names re-exported in Step 4. If it imported from the old module path in a way the package doesn't satisfy, adjust the import to `from a3ob.mayabridge.commands import <Cls>`.

- [ ] **Step 7: Validate**

Run PYCHECK, then WORKFLOWS (see snippets). Expected: exit 0, `OK=14 tb=0`, `joints=18 root=Hip`.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/mayabridge/commands plug-ins/MayaObjectBuilder.py
git commit -m "refactor: split mayabridge/commands.py into a per-command package"
```

---

## Task 2: `scene_ops.py` → `a3ob/ui/scene/` package

**Files:**
- Create: `scripts/a3ob/ui/scene/__init__.py`, `attrs.py`, `lods.py`, `selections.py`, `materials.py`, `memory.py`
- Modify: `scripts/a3ob/ui/scene_ops.py` → facade
- Verify consumer: `scripts/objectBuilderMenu.py` (imports from `a3ob.ui.scene_ops`)

**Interfaces:**
- Consumes: `a3ob.ui.constants`.
- Produces: `from a3ob.ui.scene_ops import (...)` keeps resolving (facade re-exports the package).

- [ ] **Step 1: Group the 33 functions by domain**

Run: `grep -nE "^def " scripts/a3ob/ui/scene_ops.py`
Assign each to: `attrs.py` (`_node_exists`, `_attr_exists`, `_safe_get_attr`, `_valid_nodes`, `_ensure_string_attr`, `_normalize_dayz_path`, `_split_named_properties`, `_join_named_properties`), `lods.py` (`_is_lod_transform`, `_lod_transforms`, `_selected_lod_transform`, `_lod_name_from_transform`, `_lod_label`, `_lod_name_for_set`, `_set_lod_label`, `_set_kind`), `selections.py` (`_is_object_builder_set`, `_set_bool_attr`, `_hide_object_builder_set`, `_normalize_object_builder_sets`, `_selection_sets`, `_live_set_members`, `_set_member_count`, `_selection_set_details`, `_canonical_selection_components`, `_mesh_shapes_for_item`), `materials.py` (`_mesh_shapes_from_selection`, `_material_nodes_for_selection`, `_material_metadata_label`, `_set_material_metadata_on_node`), `memory.py` (`_scene_memory_lods`, `_memory_lod_parent`, `_is_group_container`).

- [ ] **Step 2: Create the domain modules**

Each module starts with `import re` (only where used) + `import maya.cmds as cmds` + `from a3ob.ui.constants import (...)` (only the constants it uses) + intra-package imports for helpers it calls (e.g. `selections.py` does `from a3ob.ui.scene.attrs import _node_exists, _attr_exists, _safe_get_attr, ...` and `from a3ob.ui.scene.lods import _set_lod_label, _set_kind`). Move bodies verbatim. Verify closure: every name a module uses is imported or defined there.

- [ ] **Step 3: Turn `scene_ops.py` into a facade**

Replace `scripts/a3ob/ui/scene_ops.py` contents with:

```python
"""Facade re-exporting the a3ob.ui.scene package (kept for import stability)."""

from a3ob.ui.scene.attrs import *          # noqa: F401,F403
from a3ob.ui.scene.lods import *           # noqa: F401,F403
from a3ob.ui.scene.selections import *     # noqa: F401,F403
from a3ob.ui.scene.materials import *      # noqa: F401,F403
from a3ob.ui.scene.memory import *         # noqa: F401,F403
```

Because these names are underscore-prefixed, `import *` will NOT pick them up. So instead each domain module MUST define `__all__` listing its (underscore-prefixed) public names, e.g. in `attrs.py`:
`__all__ = ["_node_exists", "_attr_exists", "_safe_get_attr", "_valid_nodes", "_ensure_string_attr", "_normalize_dayz_path", "_split_named_properties", "_join_named_properties"]`. `import *` honors `__all__` even for underscore names. Do this in all five modules.

`__init__.py` for the package mirrors the same `from ... import *` so `a3ob.ui.scene` is also importable.

- [ ] **Step 4: Validate**

Run PYCHECK + WORKFLOWS. The mayapy tests reach `_selection_sets`, `_live_set_members`, `_normalize_dayz_path`, `_canonical_selection_components`, `_clear_all_object_builder_sets` (the last one lives in objectBuilderMenu, not scene) through the objectBuilderMenu facade → scene_ops facade → package. Expected: `OK=14 tb=0`, `joints=18 root=Hip`.

- [ ] **Step 5: Commit**

```bash
git add scripts/a3ob/ui/scene scripts/a3ob/ui/scene_ops.py
git commit -m "refactor: split ui/scene_ops.py into an a3ob.ui.scene package by domain"
```

---

## Task 3: `objectBuilderAutoLOD.py` → `a3ob/ui/autolod/` + facade

**Files:**
- Create: `scripts/a3ob/ui/autolod/__init__.py`, `core.py`, `generators.py`
- Modify: `scripts/objectBuilderAutoLOD.py` → facade
- Verify consumers: `objectBuilderMenu` (`_auto_lod_module`), `tests/mayapy/p3d_workflow.py` (`runpy.run_path(objectBuilderAutoLOD.py)` reaching `generate_auto_lods`)

**Interfaces:**
- Produces: `objectBuilderAutoLOD.generate_auto_lods` still importable/reachable via `runpy`.

- [ ] **Step 1: Inventory**

Run: `grep -nE "^def |^class |^[A-Z_]+ =" scripts/objectBuilderAutoLOD.py`
`generate_auto_lods` (orchestration) → `core.py`; per-LOD generator helpers (`_generate_resolution_lods`, geometry/memory/fire/view builders, `geometry_snapshot`, etc.) → `generators.py`; shared constants/imports split accordingly.

- [ ] **Step 2: Create `generators.py` and `core.py`**

Move generator helpers to `generators.py`; move `generate_auto_lods` to `core.py` with `from a3ob.ui.autolod.generators import (...)`. Preserve behavior verbatim (including the `geometry_snapshot` duplicate-before-rename fix).

- [ ] **Step 3: `__init__.py` re-export**

```python
"""Auto-LOD generation for MayaObjectBuilder."""

from a3ob.ui.autolod.core import generate_auto_lods

__all__ = ["generate_auto_lods"]
```

- [ ] **Step 4: Facade `objectBuilderAutoLOD.py`**

Replace contents with a sys.path bootstrap (same pattern as objectBuilderMenu) + `from a3ob.ui.autolod import generate_auto_lods  # noqa: E402,F401`. Keep the module importable by bare name (`importlib.import_module("objectBuilderAutoLOD")`).

- [ ] **Step 5: Validate**

Run PYCHECK + WORKFLOWS. `p3d_workflow` exercises Auto LOD (`assert_auto_lod_generation`, `assert_auto_lod_nonmanifold_cleanup`). Expected `OK=14 tb=0`.

- [ ] **Step 6: Commit**

```bash
git add scripts/a3ob/ui/autolod scripts/objectBuilderAutoLOD.py
git commit -m "refactor: split objectBuilderAutoLOD into a3ob.ui.autolod, keep bare-name facade"
```

---

## Task 4: `mesh_import.py` → `import_/` and `mesh_export.py` → `export/`

**Files:**
- Create: `scripts/a3ob/mayabridge/import_/{__init__,importer,materials,locators,attributes}.py`
- Create: `scripts/a3ob/mayabridge/export/{__init__,exporter,taggs,locators}.py`
- Modify: `scripts/a3ob/mayabridge/mesh_import.py` and `mesh_export.py` → facades
- Verify consumers: `a3ob.mayabridge.translator`, `tests/mayapy/p3d_workflow.py`

**Interfaces:**
- Produces: `from a3ob.mayabridge.mesh_import import MayaMeshImport` and `... mesh_export import MayaMeshExport` keep resolving (facades).

- [ ] **Step 1: Inventory both modules**

Run: `grep -nE "^class |^def " scripts/a3ob/mayabridge/mesh_import.py scripts/a3ob/mayabridge/mesh_export.py`
Group import: `importer.py` (`MayaMeshImport`, `_import_lod`, `_create_transform`, `_name_to_object`, `_leaf`), `materials.py` (material/shading-group creation + assignment), `locators.py` (`create_locators_for_memory_lod`, `_create_single_locator`, `sanitized_name`, `MEMORY_LOCATOR_SCALE`), `attributes.py` (`set_lod_metadata`, `apply_uvs`, `apply_normals`, `core_to_maya_point`). Group export similarly: `exporter.py` (`MayaMeshExport`, `_export_mesh_lod`), `taggs.py` (`_add_uvset_taggs`, sharp/property/mass taggs), `locators.py` (`_collect_locators_from_memory_lod`, `_has_direct_locator_shape`).

- [ ] **Step 2: Create the import_ package**

Move bodies verbatim. Intra-package imports as needed (e.g. `importer.py` does `from a3ob.mayabridge.import_.materials import ...`, `from a3ob.mayabridge.import_.locators import create_locators_for_memory_lod, sanitized_name`, `from a3ob.mayabridge.import_.attributes import ...`). Watch for shared low-level helpers (`_create_transform`, `_name_to_object`, `_leaf`) used across submodules — put them in `importer.py` (or a small `_common.py`) and import where needed. Verify closure.

- [ ] **Step 3: Create the export package**

Same approach. `exporter.py` imports from `taggs.py`/`locators.py`.

- [ ] **Step 4: Facades**

`mesh_import.py`:
```python
"""Facade re-exporting the a3ob.mayabridge.import_ package."""
from a3ob.mayabridge.import_ import *   # noqa: F401,F403
```
with each import_ submodule defining `__all__` (including underscore names the tests need, e.g. `create_locators_for_memory_lod`, `MayaMeshImport`, `sanitized_name`), and `import_/__init__.py` re-exporting them. Same for `mesh_export.py` → `export/__init__` (`MayaMeshExport`, `_collect_locators_from_memory_lod` if referenced).

- [ ] **Step 5: Update translator import if needed**

Run: `grep -nE "mesh_import|mesh_export|MayaMesh" scripts/a3ob/mayabridge/translator.py`
The facades keep `from a3ob.mayabridge.mesh_import import MayaMeshImport` working, so no change expected. Confirm.

- [ ] **Step 6: Validate**

Run PYCHECK + WORKFLOWS + format tests (`python tests/python/test_p3d_roundtrip.py`). Expected all green; `OK=14 tb=0`. Also run the live-Maya Memory-LOD smoke (import `sample_1_character.p3d`, assert 66 locators) to confirm import path intact.

- [ ] **Step 7: Commit**

```bash
git add scripts/a3ob/mayabridge/import_ scripts/a3ob/mayabridge/export scripts/a3ob/mayabridge/mesh_import.py scripts/a3ob/mayabridge/mesh_export.py
git commit -m "refactor: split mesh_import/mesh_export into import_/ and export/ packages"
```

---

## Task 5: `objectBuilderMenu.py` → `a3ob/ui/` (widgets → panels → dock → actions → entry → facade)

This is the largest and riskiest task. Do it in the sub-steps below, running **PYCHECK + a live-Maya dock smoke** after each widget/dock sub-step and full WORKFLOWS before the commit.

**Files:**
- Create: `scripts/a3ob/ui/widgets.py`, `scripts/a3ob/ui/panels/{__init__,lod,metadata,named_properties,materials,selections,skeleton,validation}.py`, `scripts/a3ob/ui/dock.py`, `scripts/a3ob/ui/actions.py`, `scripts/a3ob/ui/entry.py`
- Modify: `scripts/objectBuilderMenu.py` → facade
- Verify consumers: `plug-ins/MayaObjectBuilder.py`, `tests/mayapy/p3d_workflow.py`

**Dock smoke (run after dock/panel sub-steps), in live Maya via MCP:**
```python
import importlib, sys
sys.path.insert(0, r"C:\Users\targaryen\orca\Maya-ObjectBuilder\scripts")
for m in list(sys.modules):
    if m.startswith("a3ob.ui") or m == "objectBuilderMenu": del sys.modules[m]
import objectBuilderMenu as ob
import maya.cmds as cmds
cmds.loadPlugin(r"C:\Users\targaryen\orca\Maya-ObjectBuilder\plug-ins\MayaObjectBuilder.py", quiet=True)
ob.hide_plugin_ui(); ob.show_plugin_ui()
assert ob._active_qt_dock() is not None
for a in ("lod_type_combo","mass_value_field","named_list","material_list","selection_list","proxy_path_field","model_cfg_import"):
    assert getattr(ob._active_qt_dock(), a) is not None, a
ob.hide_plugin_ui(); print("dock smoke OK")
```

- [ ] **Step 1: Extract `widgets.py`**

Move `_qt_icon`, `_qt_button`, `_icon_button`, `_hint`, `_picker_field`, `_panel_optionvar_key`, `_CollapsibleSection`, `_SELECTION_KIND_ICONS`, and `UI_MARGIN/UI_SPACING` (re-import from constants) into `scripts/a3ob/ui/widgets.py`. It imports `qt_widgets`/`qt_core`/`qt_gui` (replicate the guarded import block or import from a shared `_qt.py` — put the PySide6 guarded import in `widgets.py` and have others import `qt_widgets` etc. from it). In `objectBuilderMenu.py` replace these definitions with `from a3ob.ui.widgets import (...)`. Run PYCHECK.

- [ ] **Step 2: Extract panel mixins**

For each panel create `scripts/a3ob/ui/panels/<name>.py` with a mixin class holding that panel's `_build_*_section`/`_build_*_tab` method(s) and its refresh/getter methods, moved verbatim from `MayaObjectBuilderDock`. Mapping: `lod.py`←LOD Properties + Auto LOD + Memory Points builders + `_on_lod_*`, `_update_memory_points_visibility`, `refresh_lod_assignment` helpers; `metadata.py`←Mass&Flags + Proxies builders + getters; `named_properties.py`←named builders/refresh/getters; `materials.py`←material builders/refresh/getters; `selections.py`←selection builder/refresh/`selected_selection_set_node`/`set_selection_details`; `skeleton.py`←model.cfg builder + path getters; `validation.py`←validation builder. Each mixin class: `class LodPanelMixin:` etc., methods reference `self.*` and module-level helpers imported at top (`from a3ob.ui.widgets import ...`, `from a3ob.ui.scene_ops import ...`, and **lazy** `from a3ob.ui.actions import ...` inside methods to avoid cycles).

- [ ] **Step 3: Assemble `dock.py`**

`dock.py` defines `class MayaObjectBuilderDock(LodPanelMixin, MetadataPanelMixin, NamedPropertiesPanelMixin, MaterialsPanelMixin, SelectionsPanelMixin, SkeletonPanelMixin, ValidationPanelMixin, qt_widgets.QWidget)` with `__init__` (attribute init + `_build_ui` + `refresh_lod_assignment`), `_build_ui`, `_build_quick_actions`. Ensure no method-name collisions across mixins (grep each mixin's `def `). Run PYCHECK + dock smoke.

- [ ] **Step 4: Extract `actions.py`**

Move module-level action wrappers and business helpers: `_undo_chunk`, `assign_lod_to_selection`, `create_empty_lod`, `_remove_lod_from_selection`, `apply_mass_from_ui`, `clear_mass_from_ui`, `apply_flag_from_ui`, `create_proxy_from_ui`, `generate_auto_lods_from_ui`, `import_model_cfg_from_ui`, `export_model_cfg_from_ui`, `add_memory_point`, `add_point_to_selection`, selection/named/material CRUD wrappers, `_commit_named_property_fields`, `_remove_named_property`, `_set_named_property_value`, `_selected_named_property_lod`, `_refresh_named_properties`, `_refresh_material_metadata`, `_refresh_selection_manager`, `_update_selection_details`, `_selected_selection_set`, `_clear_selection_manager_state`, `_select_set_members`, `_rename_selection_set`, `_create_selection_set`, `_add_to_selection_set`, `_remove_from_selection_set`, `_delete_selection_set`, `_clear_all_object_builder_sets`, `find_components_from_ui`, `_selected_lod_definition`, `_lod_resolution_value`, `_lod_node_name`, `_refresh_lod_assignment_ui`, `_persist_selected_material_metadata`, `_material` helpers not in scene, memory helpers (`_resolve_memory_lod`, `_create_memory_locator`, `_shrink_locator`, `_promote_locator_to_group`, `_add_point_to_group`, etc.), `_refresh_context_ui`. Import from `a3ob.ui.scene_ops`, `a3ob.ui.widgets`; import `_active_qt_dock` from `a3ob.ui.entry` lazily inside functions. Run PYCHECK.

- [ ] **Step 5: Extract `entry.py`**

Move: the guarded PySide6/omui import block reuse, `_qt_dock_widget`/`_ui_script_jobs` singletons, `_active_qt_dock`, `_qt_workspace_parent`, `_build_qt_dock`, `_delete_qt_dock`, `_install_context_refresh_job`, `open_dock`, `show_plugin_ui`, `hide_plugin_ui`, `_remove_legacy_shelf_button`, `load_plugin`, `import_p3d`, `export_p3d`, `import_model_cfg`, `export_model_cfg`, `_validate_scene_no_flush`, `_validate_selection_no_flush`, `_prompt`, `_plugin_path`, `_ensure_script_path`, `_auto_lod_module`, `install`, `uninstall`, and the `MENU_NAME/PLUGIN_NAME/TRANSLATOR_NAME/DOCK_NAME/SCRIPT_PATH` constants. `entry.py` imports `MayaObjectBuilderDock` from `a3ob.ui.dock`. Run PYCHECK + dock smoke.

- [ ] **Step 6: Rewrite `objectBuilderMenu.py` as the facade**

Contents: sys.path bootstrap (existing pattern) + explicit re-exports covering every name the tests/plugin reach:

```python
import sys
from pathlib import Path

_scripts_dir = str(Path(globals().get("__file__") or "objectBuilderMenu.py").resolve().parent)
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)

from a3ob.ui.constants import *          # noqa: E402,F401,F403
from a3ob.ui.widgets import (            # noqa: E402,F401
    _qt_icon, _qt_button, _icon_button, _hint, _picker_field,
    _panel_optionvar_key, _CollapsibleSection,
)
from a3ob.ui.scene_ops import *          # noqa: E402,F401,F403
from a3ob.ui.dock import MayaObjectBuilderDock          # noqa: E402,F401
from a3ob.ui.actions import *            # noqa: E402,F401,F403
from a3ob.ui.entry import *              # noqa: E402,F401,F403
```

`actions.py` and `entry.py` MUST define `__all__` listing every public + underscore name the tests use (`import_p3d`, `export_p3d`, `import_model_cfg_from_ui`, `export_model_cfg_from_ui`, `generate_auto_lods_from_ui`, `open_dock`, `show_plugin_ui`, `hide_plugin_ui`, `_active_qt_dock`, `_refresh_context_ui`, `_clear_all_object_builder_sets`, `_selection_sets`-not-here, etc.). Cross-check against `grep -oE 'ui\["[^"]+"\]' tests/mayapy/p3d_workflow.py` to enumerate every name the runpy tests pull, and ensure each is re-exported.

- [ ] **Step 7: Full validation**

Run PYCHECK + WORKFLOWS + dock smoke + the Memory-LOD locator smoke + the Selections-manager smoke (active-LOD scoping). Expected: `OK=14 tb=0`, `joints=18 root=Hip`, `dock smoke OK`, 66 locators, selection scoping correct.

- [ ] **Step 8: Commit**

```bash
git add scripts/a3ob/ui scripts/objectBuilderMenu.py plug-ins/MayaObjectBuilder.py
git commit -m "refactor: split objectBuilderMenu into a3ob.ui package (widgets/panels/dock/actions/entry)"
```

---

## Task 6: Ship new packages + docs + final validation

**Files:**
- Modify: `install/install_maya.py`, `scripts/package_release.ps1`, `CLAUDE.md`

- [ ] **Step 1: Add anchor files to installer/packaging gates**

In `install/install_maya.py` `REQUIRED_PACKAGE_FILES` and `scripts/package_release.ps1` `$RequiredFiles`, add one anchor per new package: `scripts/a3ob/mayabridge/commands/__init__.py`, `scripts/a3ob/mayabridge/import_/__init__.py`, `scripts/a3ob/mayabridge/export/__init__.py`, `scripts/a3ob/ui/scene/__init__.py`, `scripts/a3ob/ui/autolod/__init__.py`, `scripts/a3ob/ui/widgets.py`, `scripts/a3ob/ui/dock.py`. (Trees are copied wholesale; these gates just fail fast if a package goes missing.)

- [ ] **Step 2: Update CLAUDE.md architecture**

Update the "High-level architecture" bullets and the key-task-entry-points table to point at the new module paths (`a3ob/mayabridge/commands/<cmd>.py`, `a3ob/ui/panels/<panel>.py`, `a3ob/ui/dock.py`, `a3ob/ui/scene/`, etc.). Note the facade pattern (`objectBuilderMenu.py`, `objectBuilderAutoLOD.py`, `mesh_import.py`, `mesh_export.py`, `scene_ops.py` are re-export facades).

- [ ] **Step 3: Full checklist validation**

Run PYCHECK, both format tests (`python tests/python/test_p3d_roundtrip.py` and `test_model_cfg.py`), WORKFLOWS, and the three live-Maya smokes (dock build, Memory-LOD 66 locators, Selections active-LOD scoping). Expected: everything green.

- [ ] **Step 4: Commit**

```bash
git add install/install_maya.py scripts/package_release.ps1 CLAUDE.md
git commit -m "chore: ship new a3ob subpackages in installer gates, document the module layout"
```

---

## Self-Review

- **Spec coverage:** ✔ every package in the spec has a task (commands→T1, scene→T2, autolod→T3, import_/export→T4, ui→T5, ship/docs→T6); p3d.py/model_cfg.py left untouched per spec.
- **Contract coverage:** ✔ each task defines the exact `__init__`/facade re-export that keeps its consumer working; Task 5 Step 6 cross-checks the runpy name list from the test file. Order matches spec (low→high risk).
- **Placeholder scan:** Steps that relocate bodies say "verbatim" and give the symbol→file mapping rather than repeating hundreds of lines — appropriate for a pure-relocation refactor; the *new* code (every `__init__`/facade) is shown in full. Inventory steps (`grep`) resolve exact symbol lists at execution time since the modules are large.
- **Type/name consistency:** re-export lists use the same class/function names across tasks; facades preserve the names `plug-ins/` and `tests/mayapy` already import (verified against the spec's "несущий контракт").
- **`__all__` gotcha:** flagged explicitly (underscore names need `__all__` for `import *` to re-export) in Tasks 2, 4, 5.
