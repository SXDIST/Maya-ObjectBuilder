# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

This repository contains two related Object Builder toolchains:

- The active Autodesk Maya 2027 plugin at the repository root. It builds `MayaObjectBuilder.mll`, registers the `Arma P3D` file translator and `a3ob*` commands, and targets DayZ/Object Builder-style P3D workflows.
- The original Blender add-on under `Arma3ObjectBuilder-master/`, used as a compatibility reference for P3D, `model.cfg`, Object Builder metadata, and workflow behavior.

The Maya plugin is a C++17/CMake project with a DCC-independent format layer, a thin Maya API integration layer, a PySide6/OpenMayaUI dock UI, and `mayapy` workflow regressions.

## Common commands

Run Maya plugin commands from the repository root.

```bash
# Configure the Maya 2027 plugin with Visual Studio 2026 and pure C++ tests enabled
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON

# Build the Debug plugin and tests
cmake --build build --config Debug

# Build only a pure C++ test executable
cmake --build build --target p3d_roundtrip --config Debug
cmake --build build --target model_cfg_test --config Debug

# Run pure C++ fixture tests
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg

# Check Python syntax for the Maya UI and mayapy workflows
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py

# Smoke-test plugin load, command registration, and unload in Maya 2027
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone; maya.standalone.initialize(name='python'); import maya.cmds as cmds; p=r'C:\\Users\\targaryen\\source\\repos\\maya\\dayz-object-builder\\build\\Debug\\MayaObjectBuilder.mll'; cmds.loadPlugin(p); print(cmds.pluginInfo('MayaObjectBuilder', q=True, command=True)); cmds.unloadPlugin('MayaObjectBuilder'); maya.standalone.uninitialize()"

# Run Maya integration regressions
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py

# Include private/local DayZ P3D fixtures in the P3D workflow when available
DAYZ_P3D_FIXTURES=/path/to/dayz/p3d "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py

# Build Release before packaging or final release verification
cmake --build build --config Release

# Create a release archive
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

Interactive Maya UI reload during development:

```python
if cmds.workspaceControl("MayaObjectBuilderWorkspaceControl", exists=True):
    cmds.deleteUI("MayaObjectBuilderWorkspaceControl")
exec(open(r"C:\Users\targaryen\source\repos\maya\dayz-object-builder\scripts\objectBuilderMenu.py").read())
```

Launch full Maya 2027 with the Debug plugin for manual checks:

```bash
"/c/Program Files/Autodesk/Maya2027/bin/maya.exe" -script "C:/Users/targaryen/source/repos/maya/dayz-object-builder/build/launch_maya_debug_plugin.mel"
```

Run Blender add-on tests from `Arma3ObjectBuilder-master/`. These require Blender because the add-on imports `bpy`.

```bash
blender -b -noaudio --python tests/p3d.py
blender -b -noaudio --python tests/mcfg.py
```

Full Maya verification checklist for plugin changes:

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

- `CMakeLists.txt` uses C++17, `cmake/pluginEntry.cmake`, and Maya devkit fallback `C:/maya_devkits/2027/devkitBase`. It links `OpenMaya`, `OpenMayaAnim`, `OpenMayaUI`, and `Foundation`.
- `src/formats/` is the DCC-independent format layer. `BinaryIO.*` provides little-endian binary helpers; `P3D.*` parses/writes P3D MLOD/P3DM data; `ModelCfg.*` parses/writes the current `model.cfg` skeleton MVP.
- `src/PluginMain.cpp` registers plugin entry points, the `Arma P3D` translator, and commands such as `a3obValidate`, `a3obSetMass`, `a3obSetMaterial`, `a3obSetFlag`, `a3obFindComponents`, `a3obCreateLOD`, `a3obProxy`, `a3obNamedProperty`, `a3obUpdateProxy`, `a3obImportModelCfg`, and `a3obExportModelCfg`.
- `src/translators/P3DTranslator.*` is the Maya `MPxFileTranslator` bridge. `reader()` parses P3D with the core format layer and hands it to Maya import; `writer()` exports Maya LOD transforms back to P3D. `filter()` keeps `Arma P3D` visible in Maya's native Import/Export file type lists.
- `src/maya/MayaMeshImport.*` and `src/maya/MayaMeshExport.*` convert between parsed P3D LODs and Maya meshes, including Object Builder/P3D core-space to Maya Y-up axis conversion, LOD metadata, UVs, normals, materials, selections/proxies, mass/flags, named properties, TAGGs, and source vertex preservation.
- `src/commands/StubCommands.*` contains LOD, metadata, proxy, selection, mass, flag, material, component-finding, named property, and validation command implementations.
- `src/commands/ModelCfgCommands.*` imports `model.cfg` skeletons into Maya joint hierarchies and exports selected/root skeleton joints back to `model.cfg`.
- `tests/cpp/` contains pure C++ regression executables. `tests/mayapy/` contains Maya workflow regressions for plugin load, commands, P3D import/export/reimport, UI smoke coverage, hidden Object Builder metadata sets, and `model.cfg` joint import/export.

## Maya UI architecture

`scripts/objectBuilderMenu.py` owns the interactive Maya UI. Plugin load calls `show_plugin_ui()` to create a `MayaObjectBuilderWorkspaceControl` dock near Maya side panels; plugin unload calls `hide_plugin_ui()` to remove the dock, menu, and tracked `scriptJob` refresh callbacks. The plugin intentionally does not create a shelf button.

The preferred UI path is PySide6/OpenMayaUI when available:

- guarded dynamic imports load `maya.OpenMayaUI`, `shiboken6`, `PySide6.QtWidgets`, and `PySide6.QtCore`;
- `MayaObjectBuilderDock` is parented into the Maya `workspaceControl` through `MQtUtil` and `shiboken6.wrapInstance`;
- `_active_qt_dock()` uses `shiboken6.isValid` and catches stale wrapper access because Maya can delete the underlying C++ widget before Python globals are cleared;
- legacy `maya.cmds` layout builders remain as fallback when Qt is unavailable.

Current dock structure:

- Quick Actions for P3D/model.cfg/validation entry points;
- `LOD` for Object Builder LOD assignment and empty LOD creation;
- `Files` for P3D dialog shortcuts and `model.cfg` file pickers;
- `Metadata` for mass, face/vertex flags, and proxy metadata;
- `Properties` for named properties on Object Builder LODs;
- `Materials` for DayZ texture and `.rvmat` metadata;
- `Selections` for Object Builder selections, proxy sets, and face/vertex flag sets;
- `Validation` for scene and selection validation.

## Object Builder metadata and selections

- Object Builder selections, proxy selections, and vertex/face flag sets are stored as Maya `objectSet` nodes with compatibility attrs such as `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, and `a3obFlagValue`.
- These technical sets are hidden from the normal Maya Outliner with `hiddenInOutliner` and marked with `a3obTechnicalSet`; manage them through the plugin `Selections` tab instead of the Outliner.
- `scripts/objectBuilderMenu.py::_canonical_selection_components()` converts user-created Object Builder selections into exportable vertex membership. Mesh/shape selections expand to all vertices; face selections convert to vertices; export derives face coverage when all face vertices are selected.
- `scripts/objectBuilderMenu.py::_normalize_object_builder_sets()` hides/marks older Object Builder sets during Selection Manager refresh so existing scenes can be cleaned up without reimporting.
- Export remains tolerant of old/non-canonical scenes: `src/maya/MayaMeshExport.cpp` reads `.vtx[...]`, `.f[...]`, and whole mesh/shape/transform set members scoped to the current exported mesh.

## Current Maya plugin behavior

- Visual Studio 2026 generator is known to work: `Visual Studio 18 2026` with `-A x64`.
- `MayaObjectBuilder.mll` builds and loads in Maya 2027 via `mayapy`.
- P3D support includes DayZ/Object Builder LOD metadata, UVs, normals, material metadata, selections/proxies, mass, vertex/face flags, named properties, core TAGGs, source vertex preservation, generated DayZ-style metadata regression coverage, hidden metadata-set regression coverage, and DayZ-safe validation checks.
- P3D mesh scale policy is centimeter-based for Maya/Object Builder workflows: Maya mesh coordinates are exported to raw P3D coordinates without meter conversion, and P3D coordinates are imported back without linear scaling. Keep only axis conversion and transform baking at this boundary. `tests/mayapy/p3d_workflow.py` includes raw binary P3D extent checks so export scale is not validated only by reimporting with the same plugin.
- P3D import/export is handled through Maya's native File > Import/Export dialogs with the `Arma P3D` translator options. The dock complements this with workflow tools rather than replacing Maya's file dialogs.
- `model_cfg_test` and `tests/mayapy/model_cfg_workflow.py` validate the current `model.cfg` skeleton MVP against `Arma3ObjectBuilder-master/tests/inputs/model.cfg`.
- RTM, ASC, and TBCSV are intentionally out of scope for the current Maya plugin plan.

## Release packaging and installation

- End-user install docs should point to the GitHub release archive and `install/install_maya.py`, not to `build/Debug` or `build/Release` plugin paths.
- `scripts/package_release.ps1` builds the Release plugin, stages `dist/MayaObjectBuilder-v<version>-win64/`, creates `dist/MayaObjectBuilder-v<version>-win64.zip`, and writes a SHA256 checksum.
- The release package layout is `plug-ins/MayaObjectBuilder.mll`, `scripts/objectBuilderMenu.py`, `scripts/mayaObjectBuilderP3DOptions.mel`, `install/install_maya.py`, `MayaObjectBuilder.mod`, `README.md`, and `LICENSE`.
- `install/install_maya.py` installs the extracted package into the user's Maya documents folder, writes `Documents/maya/modules/MayaObjectBuilder.mod`, loads the plugin immediately, and enables Maya plugin autoload for restart persistence.
- `scripts/objectBuilderMenu.py` must keep release-aware plugin lookup: packaged `plug-ins/MayaObjectBuilder.mll` first, then local `build/Release`, then local `build/Debug` for development.

## Repository/community files

- Root-level `README.md`, `LICENSE`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `.github/ISSUE_TEMPLATE/` files are maintained for GitHub Community Standards.
- `README.md` includes an acknowledgements block linking to `https://github.com/MrClock8163/Arma3ObjectBuilder` as the original Blender/Object Builder reference project.

## Blender add-on reference notes

- `Arma3ObjectBuilder/__init__.py` is the Blender add-on entry point. It defines `bl_info`, add-on preferences, icon loading, module registration order, and top-level `register()` / `unregister()`.
- Registration order matters. New Blender classes in feature modules should be exposed through that module's own `register()` / `unregister()` and added to the top-level module list if the module is new.
- Subpackages use hot-reload guards in their `__init__.py` files. When adding a new module under `io/`, `props/`, or `ui/`, update the package `__init__.py` imports and reload block.
- `io/` contains file format data models plus import/export implementations. The pattern is `data_<format>.py`, `import_<format>.py`, and `export_<format>.py`.
- `io/config/` handles `model.cfg` tokenizing, parsing, derapification, and config data structures.
- `props/`, `ui/`, and `utilities/` contain Blender-facing state, operators/panels, and shared helpers for geometry, LODs, masses, materials, proxies, rigging, validation, compatibility, and logging.
- Blender operator entry points used by tests include `bpy.ops.a3ob.import_p3d`, `bpy.ops.a3ob.export_p3d`, `bpy.ops.a3ob.import_mcfg`, and `bpy.ops.a3ob.export_mcfg`.
- Many Blender add-on modules import `bpy`; avoid assuming they can run under system Python outside Blender.

## Development notes

- Keep new Maya plugin files at the repository root under `src/`, `tests/`, `scripts/`, `install/`, and similar top-level folders; do not recreate a nested `MayaObjectBuilder/` project directory.
- Prioritize DayZ P3D/Object Builder compatibility. Use the Blender add-on as a format/workflow reference, but avoid Arma-3-only assumptions in validation or metadata normalization.
- For Maya plugin changes, build with CMake/Visual Studio 2026 and validate load/unload with Maya 2027 `mayapy` before reporting success.
- For P3D format changes, run `p3d_roundtrip` against `Arma3ObjectBuilder-master/tests/inputs/p3d` and the Maya P3D workflow regression.
- For UI lifecycle changes, verify both Qt dock behavior and legacy fallback assumptions: dock close/reopen, plugin unload/reload, stale wrapper handling, and scriptJob cleanup.
- For metadata selection changes, verify mesh/face/vertex selection export, Object Builder set hiding via `a3obTechnicalSet`/`hiddenInOutliner`, Selection Manager visibility, and P3D roundtrip.
- When changing Blender UI or operator registration, validate by loading the add-on in Blender or running the relevant background Blender test command.
- The Blender add-on has optional integration with Arma 3 Tools via user preferences and Windows registry lookup; not all development tasks require Arma 3 Tools installed.
