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
python tests/python/test_paa.py          # PAA decoder; skips cleanly if tests/paa/*.paa are absent

# Python syntax checks (compile every .py that exists on disk — robust to package renames)
python -m py_compile $(find scripts plug-ins tests -name '*.py')

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
  the `LodResolution` signature codec, coordinate + UV conventions), `model_cfg.py` (`model.cfg`
  parser/writer), `paa.py` (DayZ `.paa` texture decoder — DXT1/DXT5 + LZO1X, with numpy/`python-lzo`
  fast paths and pure-Python fallbacks), `rvmat.py` (`.rvmat` material-config parser).
- **`scripts/a3ob/mayabridge/`** — the Maya glue (`maya.api.OpenMaya` = API 2.0). `attributes.py`
  (the single `a3ob*` attribute schema + helpers); `import_/` and `export/` packages (Maya DAG ↔ MLOD
  conversion — `import_/{convert/,builders,importer}` where `convert/` is itself a package
  (`mesh`, `names`); `export/{parse,taggs/,exporter}` where `taggs/` is a package
  (`data`, `lodexport`, `memory`); `mesh_import.py`/`mesh_export.py` are kept as re-export facades);
  `commands/` package (one module per `a3ob*` `MPxCommand` + a shared `helpers/` package —
  `base`, `geometry`, `primitives`, `scene`, `sets`; `__init__` re-exports the classes and the
  `COMMANDS` list); `model_cfg_commands.py` (skeleton import/export); `translator.py` (import/export
  bodies + option parsing); `paatex/` package (resolve/decode/cache DayZ `.paa` textures and wire
  them onto Maya materials — `settings`, `resolve`, `decode`, `channels`, `materials`; `__init__`
  re-exports the public API).

- **`scripts/a3ob/ui/`** — the dock UI package (split from the former `objectBuilderMenu.py`
  monolith). `_qt.py` (guarded PySide6/shiboken/OpenMayaUI import layer), `widgets.py` (Qt helpers +
  `_CollapsibleSection`), `dock.py` (`MayaObjectBuilderDock` widget, assembled from the panel
  mixins), `panels/` package (one mixin per dock section — `lod`, `lod_list`, `metadata`,
  `named_properties`, `materials`, `selections`, `validation`), `actions/` package (action wrappers +
  scene business logic by domain — `files`, `lod`, `materials`, `memory`, `metadata`, `named`,
  `selections`, `_common`), `entry.py` (menu/dock lifecycle/install + singletons), `constants.py`
  (pure data tables), `recent.py` (recent-path history backing store), `scene/` package (Qt-free scene
  helpers by domain: attrs/lods/selections/materials/memory), `autolod/` package (auto-LOD
  generators). The `actions ↔ entry ↔ dock` cycle is broken by a lazy dock import inside
  `entry._build_qt_dock`; `objectBuilderMenu.py` is a thin facade re-exporting everything the plugin
  and the runpy-based mayapy tests reach.

- **`plug-ins/MayaObjectBuilder.py`** — the main scripted plugin (API 2.0). Registers the eleven
  `a3ob*` commands, sources the MEL option box, opens the Python dock UI, and loads/unloads the
  companion translator plugin.
- **`plug-ins/MayaObjectBuilderTranslator.py`** — companion plugin (API 1.0). Registers the
  `Arma P3D` `MPxFileTranslator` and delegates all work to `a3ob.mayabridge.translator`.
  `MPxFileTranslator` exists only in API 1.0, while the commands need API 2.0, so the two cannot
  register from a single plugin — hence the split. The main plugin auto-loads this one, so users
  deal with a single "MayaObjectBuilder" plugin.
- **`scripts/objectBuilderMenu.py`** — thin facade over the `a3ob.ui` package (see above), kept so
  the plugin and the runpy-based mayapy tests keep importing UI names from this path.
- **`scripts/objectBuilderAutoLOD.py`** — facade over `a3ob.ui.autolod` (auto-LOD generator).
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
| P3D export | `scripts/a3ob/mayabridge/export/` (`exporter.py` `_export_mesh_lod()`; `taggs/data.py` TAGG builders, `taggs/lodexport.py` per-LOD assembly, `taggs/memory.py` locators) |
| P3D import | `scripts/a3ob/mayabridge/import_/` (`importer.py` `MayaMeshImport`, `convert/mesh.py` `apply_uvs()`/`apply_normals()`, `convert/names.py` naming/serializers, `builders.py` object sets) |
| P3D binary format | `scripts/a3ob/formats/p3d.py`, especially `LOD.read/write`, the `*TaggData` classes, `LodResolution` |
| P3D translator | `scripts/a3ob/mayabridge/translator.py` (`do_read`/`do_write`) + `plug-ins/MayaObjectBuilderTranslator.py` |
| `a3ob*` commands | `scripts/a3ob/mayabridge/commands/` (one module per command; `ValidateCommand` in `validate.py`, `closed_face_islands()` in `helpers/geometry.py`); `__init__` exports `COMMANDS` |
| PAA texture decode | `scripts/a3ob/formats/paa.py` (`decode_largest_mip()`, `PAA_File`, DXT1/DXT5 + `lzo1x_decompress`) |
| `.rvmat` parsing | `scripts/a3ob/formats/rvmat.py` (`parse_rvmat_file()`) |
| Texture → material wiring | `scripts/a3ob/mayabridge/paatex/` (`materials.assign_paa_texture()`/`assign_pending_textures()`/`preferred_shader_type()`, `resolve.resolve_paa_path()`, `decode.decode_normal_png()`/`decode_smdi_png()`) |
| Texture root / alpha UI | `scripts/a3ob/ui/panels/materials.py`; menu entry via `scripts/a3ob/ui/entry.py` |
| `model.cfg` | `scripts/a3ob/formats/model_cfg.py` and `scripts/a3ob/mayabridge/model_cfg_commands.py` |
| Attribute schema | `scripts/a3ob/mayabridge/attributes.py` (long+short `a3ob*` names) |
| UI dock/menu | `scripts/a3ob/ui/dock.py` (`MayaObjectBuilderDock`), `entry.py` (`show_plugin_ui()`); `objectBuilderMenu.py` is a facade |
| Command registration | `plug-ins/MayaObjectBuilder.py`, `initializePlugin()` / `uninitializePlugin()` |
| Format reference | `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/{data_p3d,data_paa,compression}.py` (read-only) |

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
- Material shaders and texture `file` nodes are made with `cmds.createNode(...)` (not `shadingNode`,
  which returns `None` during File > Import). The shader type is chosen by
  `paatex.preferred_shader_type()` — `aiStandardSurface` when Arnold (`mtoa`) is loaded, else `blinn`,
  else `lambert`.
- Node names are scrubbed to `[A-Za-z0-9_]` before creation (Maya raises on illegal names during
  File > Import); node names are not part of the P3D export contract.
- Maya can't read `.paa`; textures are decoded to cached PNGs (`a3ob.formats.paa`) and wired as
  `file` nodes. Because File > Import's DG context blocks inline file-node creation/connection,
  `translator.do_read` defers the texturing via
  `cmds.evalDeferred("import a3ob.mayabridge.paatex as _pt; _pt.assign_pending_textures()", lowestPriority=True)`.
- `numpy` and `python-lzo` are optional accelerators for the PAA decoder; both have pure-Python
  fallbacks (`paa.py` picks the fast path at import), so the `formats/` layer stays dependency-free
  for the `tests/python` interpreter.

## P3D format invariants

- P3D faces are triangles or quads only.
- Triangles write 16 bytes of zero padding after vertices; quads do not.
- N-gons are triangulated in `_export_mesh_lod()` through Maya triangle extraction.
- UVs are stored in both face data and the `#UVSet#` TAGG.
- UV V is inverted on write and read as `1 - v`.
- `#UVSet#` TAGG ids are 0-based; id `0` is the primary Object Builder UV set.
- Export reads Maya's active UV set through `MFnMesh.getUVs()` without a set name.
- Axis conversion (an inverse pair, round-trip tested): import P3D core point `(x, y, z)` → Maya
  `(x, z, -y)` (`convert/names.py` `core_to_maya_point`); export Maya `(x, y, z)` → P3D core
  `(x, -z, y)` (`export/parse.py` `maya_to_core_point`). Vectors/normals use the same swap and are
  normalized. Separately, `p3d.py` reads/writes each core vector's three floats in `x, z, y` file
  order (a Y/Z swap at the on-disk layer).
- TAGG structure is `active byte + null-terminated name + uint32 length + data`.

## PAA / texture invariants

- Decoded pixel rows are **bottom-to-top** (OpenGL/MImage convention); `paatex/decode.py`
  `_write_png()` flips them to top-to-bottom on write. A vertical-flip bug (PNGs were upside-down,
  so geometry sampled mirrored rows and the texture "smeared") was fixed by dropping an extra
  `np.flipud`; the cache dir is bumped to `a3ob_paa_cache_v3`. Verified byte-for-byte against the
  game's own `_co.png`.
- Alpha → transparency is **opt-in** (`MayaObjectBuilder_paa_alpha_transparency` optionVar, default
  off) and only applied to genuine bimodal cut-out masks (`_alpha_is_cutout`) — a DayZ `_ca` alpha is
  often a data channel, not a geometry cut-out, so wiring it would make solid armour see-through.
- DayZ `_smdi` channel layout: R unused (constant 1.0), **G = per-texel specular level**,
  **B = glossiness**; wired as G → `specularColor` and `1 - B` → `specularRoughness`. Feeding the raw
  RGB (R=1) blew the surface out with a red-tinted spec.
- `_nohq` is **DXT5nm**: normal.X in alpha, normal.Y in green, Z reconstructed; decoded to a
  tangent-space normal PNG and wired through `aiNormalMap` (Arnold only).
- Texture paths resolve against the texture-root optionVar (`MayaObjectBuilder_texture_root`), then
  `P:/`, then a bounded basename search; `.rvmat` stage textures (via `rvmat.py`) drive the exact
  colour/normal/spec channels, falling back to `_nohq`/`_smdi` siblings of the colour texture.
- DXT decode is numpy-vectorised with a byte-identical pure-Python fallback; LZO has an optional
  `python-lzo` C fast path. `assign_pending_textures()` prefetches every channel decode across a model
  in a `ThreadPoolExecutor` (path resolution + cache dir warmed on the main thread first).

## Maya metadata attributes

| Attribute | Node type | Purpose |
|-----------|-----------|---------|
| `a3obLodType`, `a3obResolution`, `a3obResolutionSignature` | transform | LOD type/resolution metadata |
| `a3obSourceVertices`, `a3obVertexSourceIndices` | transform | Source vertices preserved from import |
| `a3obUVSetTaggs`, `a3obUVSetTaggCount` | transform | Imported UVSet TAGG preservation |
| `a3obSharpEdges`, `a3obHasSharpEdges` | transform | Sharp edge TAGG preservation |
| `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, `a3obFlagValue` | objectSet | Object Builder selections, proxies, and flags |
| `a3obTechnicalSet`, `hiddenInOutliner` | objectSet | Technical set hiding/management |
| `a3obTexture`, `a3obMaterial` | shader | Texture (`.paa`) and `.rvmat` paths; drive the PAA pipeline — resolved against the texture-root optionVar and decoded on import, and the attrs `assign_pending_textures()` scans |
| `a3obSkeletonName` | joint | Skeleton root name (model.cfg) |

Full long+short name schema lives in `scripts/a3ob/mayabridge/attributes.py`. Note: the proxy flag
short name is unified to `a3px` on write; `a3pr` (the legacy import short name) is still read.

## Memory LOD locator workflow

Memory LOD (`a3obLodType = 9`) points are Maya **locators** parented under the Memory LOD transform.
Each locator transform's short name becomes the P3D named selection name.

- **Export** (`_collect_locators_from_memory_lod` in `export/taggs/memory.py`, surfaced through the
  `mesh_export.py` facade): when the Memory LOD has no mesh child but has locator-containing child
  transforms, each is exported as one vertex + one `SelectionTaggData` TAGG. Proxy transforms are
  skipped.
- **Import** (`create_locators_for_memory_lod` in `import_/builders.py`, invoked from
  `import_/importer.py`, surfaced through the `mesh_import.py` facade): single-vertex named selections
  in a face-less Memory LOD are reconstructed as locators; multi-vertex selections become a group.
- **UI**: `add_memory_point()` in `ui/actions/memory.py` (facade `objectBuilderMenu.py`) creates a
  locator under the selected Memory LOD.

## Do not touch without a specific task

- `Arma3ObjectBuilder-master/` — reference only (gitignored; clone if missing).
- `dist/`, `build/` — generated artifacts; installer sources live in `install/` and release
  packaging uses `scripts/package_release.ps1`.
- Blender test workflows — require Blender and are not part of the normal validation checklist.
