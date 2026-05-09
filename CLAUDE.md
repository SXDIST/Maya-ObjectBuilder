# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Maya 2027 plugin (`MayaObjectBuilder.mll`) for DayZ/Object Builder P3D workflows. The Blender add-on under `Arma3ObjectBuilder-master/` is a format/compatibility reference only; do not edit it.

## Common commands

Run commands from the repository root.

```bash
# Configure build tree when needed
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON

# Debug build used for development and validation
cmake --build build --config Debug

# Release build used by packaging flow
cmake --build build --config Release

# C++ format tests
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg

# Python syntax checks
python -m py_compile scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py

# Maya workflow tests
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py

# Package release archive
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

Full validation after code changes: Debug build → `p3d_roundtrip` → `model_cfg_test` → `py_compile` → both `mayapy` workflows.

Use the individual C++ executables or individual `mayapy` scripts above as single-test runs.

## High-level architecture

- `CMakeLists.txt` builds one Maya 2027 plugin target and, when `MAYA_OBJECT_BUILDER_BUILD_TESTS=ON`, two standalone C++ test executables. The pure format layer is shared by the plugin and tests.
- `src/PluginMain.cpp` is the plugin entry point. It registers the `Arma P3D` file translator, all `a3ob*` commands, `model.cfg` commands, sources the MEL options script, opens the Python dock UI on load, and hides it on unload.
- `src/translators/P3DTranslator.cpp` bridges Maya File > Import/Export to the format and Maya layers. Import reads `a3ob::p3d::MLOD` then calls `MayaMeshImport`; export builds `ExportOptions`, optionally runs `a3obValidate`, then calls `MayaMeshExport`.
- `src/formats/` contains file-format code independent of Maya: `BinaryIO.*`, `P3D.*`, and `ModelCfg.*`. This layer is what the C++ tests exercise directly.
- `src/maya/MayaMeshImport.*` and `src/maya/MayaMeshExport.*` convert between Maya DAG/mesh data and P3D MLOD structures, including LOD metadata, selections, UVs, normals, mass, flags, proxies, named properties, and materials.
- `src/commands/StubCommands.*` implements most `a3ob*` Maya commands for validation and Object Builder metadata editing. `src/commands/ModelCfgCommands.*` handles `model.cfg` skeleton import/export commands.
- `scripts/objectBuilderMenu.py` is the Maya dock/menu UI and command wrapper layer. It loads the plugin, opens import/export dialogs, drives LOD assignment, selections, named properties, materials, mass/flags, proxies, model.cfg actions, and auto LOD UI. `scripts/objectBuilderAutoLOD.py` contains the auto-LOD generation logic used by that UI.
- `scripts/mayaObjectBuilderP3DOptions.mel` provides Maya file translator options UI/defaults for P3D import/export.
- `tests/cpp/` contains standalone format tests. `tests/mayapy/` contains Maya integration workflows that load the compiled plugin and exercise import/export plus command/UI-facing behavior.

## Claude automation

Use repo-local skills instead of keeping routine workflow context in the main chat.

| Command | When to use | Default agent |
|---------|-------------|---------------|
| `/p3d-validate` | Full Debug build, P3D roundtrip, model.cfg, py_compile, and mayapy workflow validation | `validation-runner` |
| `/p3d-debug` | P3D import/export, TAGG, LOD, UV, selections/proxies, mass/flags, Object Builder compatibility | `p3d-architect` |
| `/model-cfg-validate` | `model.cfg` parser/writer, skeleton import/export, and joint workflow | `model-cfg-specialist` |
| `/plugin-smoke` | `.mll` loading, command/translator registration, Python UI entrypoints | `maya-ui-maintainer` |
| `/a3ob-command-workflow` | `a3ob*` commands: validate/createLOD/mass/flag/proxy and UI wrappers | `a3ob-command-maintainer` |
| `/commit-write` | Safe git commit only after explicit user request | `commit-writer` |
| `/release-build` | Release archive build when packaging prerequisites exist | `release-builder` |
| `/maya-debug-launch` | Debug build and Maya 2027 launch with explicit `build/Debug/MayaObjectBuilder.mll` load | `maya-debug-launcher` |

Model policy:
- Opus 4.7 for deep P3D/Object Builder format and cross-file debugging.
- Sonnet for implementation, Maya UI/plugin wiring, `model.cfg`, `a3ob*` commands, commits, releases, and launch workflows.
- Haiku for procedural verification and short pass/fail reporting.

Workflow constraints:
- `/commit-write` never pushes and never commits without an explicit request for the current scope.
- `/release-build` packages `install/install_maya.py` and runtime scripts including `scripts/objectBuilderAutoLOD.py`; if a release prerequisite is missing, report blockers instead of simulating a release.
- `/maya-debug-launch` must force the Debug plugin path and must not load a Release or packaged plugin copy.

## Key task entry points

| Task | Primary files/functions |
|------|--------------------------|
| P3D export | `src/maya/MayaMeshExport.cpp`, especially `exportMeshLOD()` and `addUVSetTaggs()` |
| P3D import | `src/maya/MayaMeshImport.cpp`, especially `applyUVs()`, `applyNormals()`, and `assignMaterials()` |
| P3D binary format | `src/formats/P3D.cpp`, especially `LOD::read()`, `LOD::write()`, and `*TaggData::read/write` |
| P3D translator | `src/translators/P3DTranslator.cpp`, especially `reader()`, `writer()`, and `identifyFile()` |
| `a3ob*` commands | `src/commands/StubCommands.cpp`; validation is in the `a3obValidate` `MItMeshPolygon` loop |
| `model.cfg` | `src/formats/ModelCfg.*` and `src/commands/ModelCfgCommands.*` |
| UI dock/menu | `scripts/objectBuilderMenu.py`, especially `show_plugin_ui()` and `MayaObjectBuilderDock` |
| Command registration | `src/PluginMain.cpp`, `initializePlugin()` and `uninitializePlugin()` |
| Format reference | `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/data_p3d.py` as read-only reference |

## P3D format invariants

- P3D faces are triangles or quads only.
- Triangles write 16 bytes of zero padding after vertices; quads do not.
- N-gons are triangulated in `exportMeshLOD()` through Maya triangle extraction.
- UVs are stored in both face data and the `#UVSet#` TAGG.
- UV V is inverted on write and read as `1 - v`.
- `#UVSet#` TAGG ids are 0-based; id `0` is the primary Object Builder UV set.
- Export reads Maya's active UV set through `meshFn.getUVs()` without a set name.
- Maya Y-up to P3D position writes `(x, z, y)`; normals write as `-x, -z, -y`.
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

## Do not touch without a specific task

- `Arma3ObjectBuilder-master/` — reference only.
- `CMakeLists.txt` and `cmake/` — build configuration is known-working.
- `dist/` release outputs — generated artifacts; installer sources live in `install/` and release packaging uses `scripts/package_release.ps1`.
- Blender test workflows — require Blender and are not part of the normal validation checklist.
