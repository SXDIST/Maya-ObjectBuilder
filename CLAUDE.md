# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Maya 2027 plugin (`MayaObjectBuilder`) for DayZ/Object Builder P3D workflows, written in **pure Python** (Maya Python API 2.0, with a tiny API‑1.0 shell for the file translator). There is no compilation step — edit the Python and reload. The Blender add‑on under `Arma3ObjectBuilder-master/` is a format/compatibility reference only (gitignored, clone from https://github.com/MrClock8163/Arma3ObjectBuilder); do not edit it.

The plugin was ported 1:1 from a former C++ `.mll`. Command names, flags and the on‑scene `a3ob*` attribute schema are preserved, so existing scenes keep round‑tripping.

## Common commands

Run from the repository root.

```bash
# Register this repo as a Maya module (edit-in-place, no copy). Run inside Maya/mayapy:
#   import dev_install; dev_install.install()
# or headless to just write the .mod:
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'scripts'); import dev_install; dev_install.install(load=False)"

# Pure-Python format tests (no Maya)
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py

# Python syntax checks
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py scripts/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py

# Maya workflow tests (load the plugin, exercise import/export + commands + UI)
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py

# Package release archive (plain file copy + zip, no build)
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

Full validation after code changes: both `tests/python` format tests → `py_compile` → both `tests/mayapy` workflows.

## High-level architecture

Two layers, split by whether they need Maya:

- **`scripts/a3ob/formats/`** — Maya-independent file format code, unit-testable with a plain
  system Python interpreter. `binary.py` (little-endian reader/writer), `p3d.py` (MLOD/LOD/TAGG,
  the `LodResolution` signature codec, coordinate + UV conventions), `model.cfg` parser/writer in
  `model_cfg.py`.
- **`scripts/a3ob/mayabridge/`** — the Maya glue (`maya.api.OpenMaya` = API 2.0). `attributes.py`
  (the single `a3ob*` attribute schema + helpers), `mesh_import.py` / `mesh_export.py` (Maya DAG ↔
  MLOD conversion), `commands.py` (the nine `a3ob*` `MPxCommand`s), `model_cfg_commands.py` (skeleton
  import/export), `translator.py` (import/export bodies + option parsing).

- **`scripts/a3ob/ui/`** — UI support package extracted from the dock monolith. `constants.py`
  (pure data tables: `LOD_DEFINITIONS`, `LOD_TYPE_NAMES`, `KNOWN_NAMED_PROPS`, `UI_MARGIN/SPACING`,
  `RESOLUTION_LOD_TYPE`/`MEMORY_LOD_TYPE`, no deps) and `scene_ops.py` (Qt-free Maya-scene helpers:
  attr/path utils, LOD-transform helpers, selection-set reads, memory-LOD and material helpers).
  `objectBuilderMenu.py` imports both and re-exports the `scene_ops` names so the runpy-based mayapy
  tests keep reaching them. Dock routers stay in `objectBuilderMenu.py` (they depend on the live
  dock singleton), so `scene_ops` never imports the dock — no import cycle.

- **`plug-ins/MayaObjectBuilder.py`** — the main scripted plugin (API 2.0). Registers the eleven
  `a3ob*` commands, sources the MEL option box, opens the Python dock UI, and loads/unloads the
  companion translator plugin.
- **`plug-ins/MayaObjectBuilderTranslator.py`** — companion plugin (API 1.0). Registers the
  `Arma P3D` `MPxFileTranslator` and delegates all work to `a3ob.mayabridge.translator`.
  `MPxFileTranslator` exists only in API 1.0, while the commands need API 2.0, so the two cannot
  register from a single plugin — hence the split. The main plugin auto-loads this one, so users
  deal with a single "MayaObjectBuilder" plugin.
- **`scripts/objectBuilderMenu.py`** — the Qt dock/menu UI (accordion-panel dock via
  `MayaObjectBuilderDock`) and command-wrapper layer. Drives everything through `cmds.a3ob*` and the
  file translator; imports data/scene helpers from `a3ob.ui.constants` / `a3ob.ui.scene_ops`.
- **`scripts/objectBuilderAutoLOD.py`** — the auto-LOD generator.
- **`scripts/mayaObjectBuilderP3DOptions.mel`** — Maya File > Import/Export option box.
- **`scripts/dev_install.py`** — writes `Documents/maya/modules/MayaObjectBuilder.mod` pointing at
  this repo (edit-in-place local install). `install/` holds the drag-into-Maya end-user installer.
- `tests/python/` — pure-Python format tests. `tests/mayapy/` — Maya integration workflows.

## Installation model

- **Local dev:** `scripts/dev_install.py` writes a `.mod` in `Documents/maya/modules/` whose module
  root is this repo, so Maya loads `plug-ins/` and `scripts/` from here with no copy. A committed
  `MayaObjectBuilder.mod` (root `.`) also makes the repo a drop-in module on `MAYA_MODULE_PATH`.
- **End users:** drag `install/mayaObjectBuilderInstall.py` into Maya. It copies `plug-ins/` +
  `scripts/` into `Documents/maya/MayaObjectBuilder/`, writes the `.mod`, and loads with autoload.

## Key task entry points

| Task | Primary files/functions |
|------|--------------------------|
| P3D export | `scripts/a3ob/mayabridge/mesh_export.py`, especially `_export_mesh_lod()` and `_add_uvset_taggs()` |
| P3D import | `scripts/a3ob/mayabridge/mesh_import.py`, especially `apply_uvs()`, `apply_normals()`, `MayaMeshImport._assign_materials()` |
| P3D binary format | `scripts/a3ob/formats/p3d.py`, especially `LOD.read/write`, the `*TaggData` classes, `LodResolution` |
| P3D translator | `scripts/a3ob/mayabridge/translator.py` (`do_read`/`do_write`) + `plug-ins/MayaObjectBuilderTranslator.py` |
| `a3ob*` commands | `scripts/a3ob/mayabridge/commands.py`; validation is in `ValidateCommand`, components in `closed_face_islands()` |
| `model.cfg` | `scripts/a3ob/formats/model_cfg.py` and `scripts/a3ob/mayabridge/model_cfg_commands.py` |
| Attribute schema | `scripts/a3ob/mayabridge/attributes.py` (long+short `a3ob*` names) |
| UI dock/menu | `scripts/objectBuilderMenu.py`, especially `show_plugin_ui()` and `MayaObjectBuilderDock` |
| Command registration | `plug-ins/MayaObjectBuilder.py`, `initializePlugin()` / `uninitializePlugin()` |
| Format reference | `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/data_p3d.py` (read-only) |

## Port-specific gotchas (Maya Python API differences vs the former C++)

- `MPxFileTranslator` is API‑1.0 only → the translator lives in the companion plugin (above).
- `MSyntax.addFlag` accepts only ONE argument type per flag; the long flag name `set` is reserved.
  `a3obNamedProperty -set` therefore takes a single `"key=value"` string and its long alias is
  `-setproperty` (short `-s` unchanged).
- Under `mayapy` standalone, `MPxCommand.setResult` values come back from `cmds` as a 1-element
  list (unlike the C++ scalar). Consumers (`objectBuilderMenu`, `objectBuilderAutoLOD`, the workflow
  tests) unwrap `[name] -> name`.
- `cmds.createNode(..., skipSelect=True)` is used where an active component selection must survive
  (the C++ used `MDagModifier`, which did not change selection).
- Material shaders are made with `cmds.createNode("lambert")` (not `shadingNode`), which returns
  `None` during File > Import.
- Node names are scrubbed to `[A-Za-z0-9_]` before creation (Maya raises on illegal names during
  File > Import); node names are not part of the P3D export contract.

## P3D format invariants

- P3D faces are triangles or quads only.
- Triangles write 16 bytes of zero padding after vertices; quads do not.
- N-gons are triangulated in `_export_mesh_lod()` through Maya triangle extraction.
- UVs are stored in both face data and the `#UVSet#` TAGG.
- UV V is inverted on write and read as `1 - v`.
- `#UVSet#` TAGG ids are 0-based; id `0` is the primary Object Builder UV set.
- Export reads Maya's active UV set through `MFnMesh.getUVs()` without a set name.
- Maya Y-up to P3D position writes `(x, z, y)`; normals write as `-x, -z, -y`.
- P3D → Maya point is `(x, z, -y)`; the two conventions are inverses.
- TAGG structure is `active byte + null-terminated name + uint32 length + data`.

## Maya metadata attributes

| Attribute | Node type | Purpose |
|-----------|-----------|---------|
| `a3obLodType`, `a3obResolution`, `a3obResolutionSignature` | transform | LOD type/resolution metadata |
| `a3obSourceVertices`, `a3obVertexSourceIndices` | transform | Source vertices preserved from import |
| `a3obUVSetTaggs`, `a3obUVSetTaggCount` | transform | Imported UVSet TAGG preservation |
| `a3obSharpEdges`, `a3obHasSharpEdges` | transform | Sharp edge TAGG preservation |
| `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, `a3obFlagValue` | objectSet | Object Builder selections, proxies, and flags |
| `a3obTechnicalSet`, `hiddenInOutliner` | objectSet | Technical set hiding/management |
| `a3obTexture`, `a3obMaterial` | shader | Texture and `.rvmat` paths |
| `a3obSkeletonName` | joint | Skeleton root name (model.cfg) |

Full long+short name schema lives in `scripts/a3ob/mayabridge/attributes.py`. Note: the proxy flag
short name is unified to `a3px` on write; `a3pr` (the legacy import short name) is still read.

## Memory LOD locator workflow

Memory LOD (`a3obLodType = 9`) points are Maya **locators** parented under the Memory LOD transform.
Each locator transform's short name becomes the P3D named selection name.

- **Export** (`_collect_locators_from_memory_lod` in `mesh_export.py`): when the Memory LOD has no
  mesh child but has locator-containing child transforms, each is exported as one vertex + one
  `SelectionTaggData` TAGG. Proxy transforms are skipped.
- **Import** (`create_locators_for_memory_lod` in `mesh_import.py`): single-vertex named selections
  in a face-less Memory LOD are reconstructed as locators; multi-vertex selections become a group.
- **UI**: `add_memory_point()` in `objectBuilderMenu.py` creates a locator under the selected Memory
  LOD.

## Do not touch without a specific task

- `Arma3ObjectBuilder-master/` — reference only (gitignored; clone if missing).
- `dist/`, `build/` — generated artifacts; installer sources live in `install/` and release
  packaging uses `scripts/package_release.ps1`.
- Blender test workflows — require Blender and are not part of the normal validation checklist.
