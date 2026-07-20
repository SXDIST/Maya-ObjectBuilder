---
name: refactor
description: Refactor MayaObjectBuilder source code — extract helpers, reduce duplication, rename for clarity, split large files — without changing observable behavior or public APIs.
---

# refactor

Use this when the task is to improve code maintainability without adding features, or when
the user says: "рефактори", "почисти код", "вынеси в функцию", "переименуй", "разбей на
части", "убери дублирование", "упрости функцию", "extract helper", "rename", "split class".

---

## What this skill refactors

**Format & Maya-bridge code (`scripts/a3ob/`)**
- Extract shared helpers from large functions in `mayabridge/export/exporter.py`,
  `mayabridge/import_/importer.py`, `mayabridge/commands/` (package), and `formats/p3d.py`.
- Rename local variables, parameters, and private helpers for clarity.
- Split long functions (>80 lines) into focused sub-functions.
- Remove duplicated attribute-read and status-check boilerplate across command classes.
- Prefer comprehensions, `enumerate`, and early returns where they remove noise.

**Python UI (`scripts/objectBuilderMenu.py`, `scripts/objectBuilderAutoLOD.py`)**
- Extract repeated Qt widget-building sequences into private builder methods.
- Split mixed-responsibility methods (UI construction + business logic) into separate layers.
- Rename unclear local variables and helper functions.
- Collapse verbose `if/elif` chains into table-driven dispatch where the pattern is clear.

**MEL options (`scripts/mayaObjectBuilderP3DOptions.mel`)**
- Minor cleanup only: remove dead code, clarify procedure names. No structural changes.

**Tests (`tests/mayapy/`, `tests/python/`)**
- Extract shared setup/teardown into reusable helpers.
- Improve assertion messages so failures name the invariant they check.
- Rename test sections to match the behavior they cover.

---

## What this skill does NOT refactor

| Off-limits | Why |
|---|---|
| `Arma3ObjectBuilder-master/` | Read-only format reference. Never edit. |
| `a3ob*` attribute long/short names in `scripts/a3ob/mayabridge/attributes.py` | The on-scene metadata schema. Renaming breaks round-tripping of existing scenes. |
| `dist/`, `build/` | Generated artifacts. |
| Registered command names: `a3obValidate`, `a3obCreateLOD`, `a3obSetMass`, `a3obSetFlag`, `a3obProxy`, `a3obSetMaterial`, `a3obFindComponents`, `a3obNamedProperty`, `a3obUpdateProxy` | Maya registers these at load time. Renaming breaks every user MEL/Python script that calls them. |
| P3D translator name `Arma P3D` | Registered with Maya's file translator system. Renaming breaks File > Import/Export. |
| P3D binary format structure and invariants | Changing byte layout, TAGG structure, axis conventions, or UV inversion logic silently corrupts files in Object Builder. |
| Public Python entrypoints called from MEL or tests | `show_plugin_ui()`, `MayaObjectBuilderDock`, functions invoked from `mayaObjectBuilderP3DOptions.mel`. Renaming breaks the load chain. |
| Behavior | Refactoring must never change observable output, error messages, or command behavior. |

---

## Best targets (high value / low risk)

1. **`scripts/objectBuilderMenu.py`** — repeated Qt widget construction, UI and
   logic mixed in the same methods. Extract private `_build_*` helpers per panel. Highest impact.
2. **`scripts/a3ob/mayabridge/commands/`** (one module per command class) — attribute-read and
   status-check patterns duplicated across `doIt()` implementations. Extract shared module-level helpers.
3. **`scripts/a3ob/mayabridge/export/exporter.py`** — `_export_mesh_lod()` is long. Extract
   material-collection, face-data, and TAGG-writing sub-functions.
4. **`scripts/a3ob/mayabridge/import_/importer.py`** — `apply_uvs()` and `_assign_materials()` are long.
   Extract per-set UV application and per-face material assignment into focused helpers.
5. **`tests/mayapy/p3d_workflow.py`** — shared import/export setup repeated per test
   section. Extract `setup_test_scene()` and `assert_lod_metadata()` helpers.

---

## Style conventions (no linter config exists in repo)

The plugin is pure Python (Maya Python API 2.0). There is no C++ or build step.

**Python**
- PEP 8. `snake_case` for functions and variables. `PascalCase` for classes.
- f-strings for all string formatting.
- No trailing `_` unless shadowing a builtin.
- No comments unless the WHY is non-obvious.
- Do not add type annotations during refactoring unless the function is being touched for
  another reason and the annotation makes the signature unambiguous.

**General**
- No docstrings on methods whose name already describes them.
- No added features, no new error handling, no backwards-compat shims.
- Three similar lines is better than a premature abstraction — only extract when there are
  at least three callers or the function body exceeds ~60 lines.

---

## Role

This skill **improves maintainability without changing behavior**. It is not a bug-fix skill,
not a feature skill, and not a style-enforcement pass. Its job is to make the next edit
easier and safer. The behavior contract is: all tests that pass before the refactor must
still pass after it.

---

## Workflow

1. **Read the target completely.** Read the full function or class before touching anything.
2. **Name the smell.** Long function / duplication / unclear name / mixed responsibility /
   deep nesting. Be specific.
3. **Plan the minimal change** that fixes only that smell. Do not fix adjacent smells in the
   same pass unless they are in the extracted code.
4. **Check public API surface** before renaming: grep for the symbol across `plug-ins/`,
   `scripts/`, `tests/`, and `.mel` files. If anything external calls it, do not rename it.
5. **Implement.** Prefer Edit over Write. Make one logical change per file.
6. **Verify.** Run the commands for the changed layer (see below).
7. **Report** what changed, why, and the verification result.

---

## First inspect

```
scripts/a3ob/mayabridge/commands/
scripts/a3ob/mayabridge/export/exporter.py
scripts/a3ob/mayabridge/import_/importer.py
scripts/objectBuilderMenu.py
```

---

## Verification commands (pure Python — no build step)

**After any format or Maya-bridge change (`scripts/a3ob/`):**
```bash
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
python -m py_compile $(git ls-files 'scripts/a3ob/*.py')
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

**After any UI/MEL change:**
```bash
python -m py_compile scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

**After test file change only:**
```bash
python -m py_compile tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
```

---

## Output format

- Smell identified (type + location).
- Symbol search result (safe to rename or not).
- Files changed with function/line references.
- Verification result per command.
- Behavior unchanged: yes / no + explanation if no.
