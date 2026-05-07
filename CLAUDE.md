# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This repository contains the original Arma 3 Object Builder Blender add-on under `Arma3ObjectBuilder-master/Arma3ObjectBuilder/` and a new Autodesk Maya 2027 C++/CMake plugin implementation at the repository root.

The Blender add-on is a Python extension for importing, exporting, and editing Arma 3 content formats such as P3D, ASC, RTM, PAA, `model.cfg`, and Terrain Builder object lists. It targets Blender through `bpy`; legacy `bl_info` metadata lists Blender 2.90+, while `blender_manifest.toml` declares the Blender 4.2+ extension manifest for version 2.5.1.

The Maya plugin is being developed as a C++ core format layer plus a thin Maya API integration layer for DayZ/Object Builder-style workflows. It builds `MayaObjectBuilder.mll`, registers the `Arma P3D` file translator and `a3ob*` commands, parses/writes P3D MLOD files in pure C++, and imports/exports P3D LOD meshes with Object Builder metadata preservation.

## Common commands

Run Maya plugin commands from the repository root.

```bash
# Configure the Maya 2027 plugin with Visual Studio 2026
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON

# Build the full Maya plugin and pure C++ tests
cmake --build build --config Debug

# Build only the pure C++ P3D roundtrip test
cmake --build build --target p3d_roundtrip --config Debug

# Run the P3D roundtrip fixture test
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip

# Run the pure C++ model.cfg fixture test
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg

# Smoke-test plugin load, command registration, and unload in Maya 2027
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone; maya.standalone.initialize(name='python'); import maya.cmds as cmds; p=r'C:\\Users\\targaryen\\source\\repos\\maya\\dayz-object-builder\\build\\Debug\\MayaObjectBuilder.mll'; cmds.loadPlugin(p); print(cmds.pluginInfo('MayaObjectBuilder', q=True, command=True)); cmds.unloadPlugin('MayaObjectBuilder'); maya.standalone.uninitialize()"

# Run the Maya P3D import/export workflow regression
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py

# Optionally include private/local DayZ P3D fixtures in the same workflow
DAYZ_P3D_FIXTURES=/path/to/dayz/p3d "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py

# Run the Maya model.cfg joint import/export workflow regression
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py

# Install/open the MayaObjectBuilder dock UI in an interactive Maya Python session
exec(open(r"C:\\Users\\targaryen\\source\\repos\\maya\\dayz-object-builder\\scripts\\objectBuilderMenu.py").read())

# Reload the dock UI after editing objectBuilderMenu.py in an interactive Maya Python session
if cmds.workspaceControl("MayaObjectBuilderWorkspaceControl", exists=True):
    cmds.deleteUI("MayaObjectBuilderWorkspaceControl")
exec(open(r"C:\\Users\\targaryen\\source\\repos\\maya\\dayz-object-builder\\scripts\\objectBuilderMenu.py").read())
```

Run Blender add-on commands from `Arma3ObjectBuilder-master/`.

```bash
# Run all available Blender-backed tests
blender -b -noaudio --python tests/p3d.py
blender -b -noaudio --python tests/mcfg.py

# Run only the P3D import/export tests
blender -b -noaudio --python tests/p3d.py

# Run only the model.cfg tests
blender -b -noaudio --python tests/mcfg.py
```

There is no `pyproject.toml`, `requirements.txt`, package manager config, or dedicated lint/type-check command for the Blender add-on. Blender tests are plain `unittest` scripts executed inside Blender so that `bpy` and registered `a3ob` operators are available.

Full Maya verification checklist:

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
cmake --build build --config Release
```

## Maya plugin architecture

- `CMakeLists.txt` follows the local Maya devkit pattern from `collider-tools`: it uses `C:/maya_devkits/2027/devkitBase` as the fallback `DEVKIT_LOCATION`, includes `cmake/pluginEntry.cmake`, and calls `build_plugin()`.
- `src/PluginMain.cpp` registers the plugin entry points, the `Arma P3D` file translator, and the commands: `a3obValidate`, `a3obSetMass`, `a3obSetMaterial`, `a3obSetFlag`, `a3obCreateLOD`, `a3obProxy`, `a3obNamedProperty`, `a3obUpdateProxy`, `a3obImportModelCfg`, and `a3obExportModelCfg`.
- `src/commands/StubCommands.*` contains the command implementations for LOD creation/marking, mass metadata including selected vertex mass edits, material metadata assignment, flag objectSets, proxy placeholders/selections, named property edits, proxy metadata updates, and scene validation.
- `src/commands/ModelCfgCommands.*` imports `model.cfg` skeletons into Maya joint hierarchies and exports selected/root skeleton joints back to `model.cfg`.
- `src/formats/` is the DCC-independent C++ format core. `BinaryIO.*` provides little-endian binary helpers; `P3D.*` parses and writes P3D MLOD/P3DM data; `ModelCfg.*` parses/writes the current model.cfg skeleton MVP.
- `src/translators/P3DTranslator.*` is the Maya `MPxFileTranslator` bridge. `reader()` parses P3D with the core format layer and hands it to the Maya import layer; `writer()` exports Maya LOD transforms back to P3D.
- `src/maya/MayaMeshImport.*` and `src/maya/MayaMeshExport.*` convert between parsed P3D LODs and Maya transforms/meshes, including LOD metadata, UVs, normals, material metadata, selections/proxies, mass/flags, TAGGs, and source vertex preservation.
- `scripts/objectBuilderMenu.py` installs the interactive Maya dock UI. It opens a `MayaObjectBuilderWorkspaceControl` tab near the right-side Attribute Editor/Channel Box area, adds a small `MOB` shelf button plus a minimal fallback menu, auto-refreshes on Maya selection changes through a `SelectionChanged` scriptJob, and exposes dock tabs for file I/O, LOD properties, named properties, proxy access, selections, material metadata, mass, flags, and validation.
- `tests/cpp/p3d_roundtrip.cpp` and `tests/cpp/model_cfg_test.cpp` are pure C++ regression executables; `tests/mayapy/p3d_workflow.py` validates plugin commands and P3D import/export/reimport in Maya; `tests/mayapy/model_cfg_workflow.py` validates model.cfg joint import/export.

## Current Maya plugin status

- Visual Studio 2026 generator is known to work: `Visual Studio 18 2026` with `-A x64`.
- `MayaObjectBuilder.mll` builds and loads in Maya 2027 via `mayapy`.
- The pure C++ roundtrip test passes on `sample_1_character.p3d` and `sample_2_crate.p3d` with structural and TAGG summary checks.
- Maya import/export/reimport workflow passes on the P3D fixtures through `tests/mayapy/p3d_workflow.py`; the same workflow optionally includes local DayZ `.p3d` fixtures from `DAYZ_P3D_FIXTURES`, `tests/inputs/dayz_p3d`, or `local/dayz_p3d` when present.
- P3D support includes LOD metadata, UVs, normals, material metadata, selections/proxies, mass, vertex/face flags, named properties, core TAGGs, source vertex preservation, generated DayZ-style metadata regression coverage, and DayZ-safe validation checks.
- The Maya UI is now a docked Object Builder-style tool rather than a top-menu workflow. The dock includes context-aware LOD editing, common named property presets, proxy path/index editing, typed selection-set creation, inline material/mass/flag tools, and selection list filtering/member counts.
- `model_cfg_test` and `tests/mayapy/model_cfg_workflow.py` validate the current model.cfg skeleton MVP against `Arma3ObjectBuilder-master/tests/inputs/model.cfg`.
- RTM, ASC, and TBCSV are intentionally out of scope for the current Maya plugin plan.

## Blender add-on architecture

- `Arma3ObjectBuilder/__init__.py` is the add-on entry point. It defines `bl_info`, global add-on preferences, icon loading, the ordered `modules` tuple, and the top-level `register()` / `unregister()` functions.
- Registration order matters. New Blender classes in feature modules should be exposed through that module's own `register()` / `unregister()` and then added to the top-level `modules` tuple if the module is new.
- Subpackages use hot-reload guards in their `__init__.py` files. When adding a new module under `io/`, `props/`, or `ui/`, update the package `__init__.py` imports and reload block so iterative Blender development keeps working.
- `io/` contains file format data models plus import/export implementations. The pattern is `data_<format>.py` for parsed structures, `import_<format>.py` for Blender import, and `export_<format>.py` for export.
- `io/config/` handles `model.cfg` tokenizing, parsing, derapification, and config data structures.
- `props/` defines Blender `PropertyGroup` state attached to objects, materials, actions, and scenes.
- `ui/` contains Blender operators, panels, and menus for import/export screens and tool panels. Operators use the `a3ob.*` namespace used by the tests.
- `utilities/` contains shared Blender-facing helpers for geometry structure, LODs, masses, materials, proxies, rigging, validation, compatibility, logging, and similar cross-cutting add-on behavior.
- `scripts/` contains standalone utility scripts for conversions and batch operations; these are separate from normal add-on registration.
- `tests/inputs/` stores Blender/P3D/model.cfg sample fixtures. Test outputs are written under `tests/outputs/`.

## Development notes

- Keep new Maya plugin files at the repository root under `src/`, `tests/`, and similar top-level folders; do not recreate a nested `MayaObjectBuilder/` project directory.
- Prioritize DayZ P3D/Object Builder compatibility. Use the Arma 3 Blender add-on as a format/workflow reference, but avoid Arma-3-only assumptions in validation or metadata normalization.
- For Maya plugin changes, build with CMake/Visual Studio 2026 and validate load/unload with Maya 2027 `mayapy` before reporting success.
- For P3D format changes, run `p3d_roundtrip` against `Arma3ObjectBuilder-master/tests/inputs/p3d`.
- Many Blender add-on modules import `bpy`; avoid assuming files can be executed with system Python outside Blender.
- Keep Blender import/export behavior aligned with existing operator entry points because tests call `bpy.ops.a3ob.import_p3d`, `bpy.ops.a3ob.export_p3d`, `bpy.ops.a3ob.import_mcfg`, and `bpy.ops.a3ob.export_mcfg`.
- When changing Blender UI or operator registration, validate by loading the add-on in Blender or running the relevant background Blender test command.
- The Blender add-on has optional integration with Arma 3 Tools via user preferences and Windows registry lookup; not all development tasks require Arma 3 Tools installed.
