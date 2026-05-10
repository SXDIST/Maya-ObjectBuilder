# Maya ObjectBuilder

Maya ObjectBuilder is an Autodesk Maya 2027 plugin for DayZ/Object Builder-style P3D asset workflows. It adds native Maya import/export support for P3D MLOD files and provides tools for editing Object Builder metadata directly in Maya.

The repository also contains the original Blender add-on source under `Arma3ObjectBuilder-master/` as a compatibility reference for Object Builder data structures and P3D behavior. That folder is not part of the Maya plugin runtime.

## Features

- `Arma P3D` file translator for Maya File > Import/Export.
- P3D MLOD import/export with LOD metadata preservation.
- Object Builder metadata editing from the Maya dock UI:
  - LOD assignment and empty LOD creation;
  - named selections and named properties;
  - texture and `.rvmat` material paths;
  - vertex mass and component flags;
  - proxy metadata;
  - validation helpers.
- Auto LOD generation from selected Maya geometry.
- `model.cfg` skeleton import/export workflow.
- Release installer that copies the runtime files into the Maya user folder, writes a Maya module file, loads the plugin, and enables autoload.

## Installation from a GitHub release

1. Download the latest `MayaObjectBuilder-v*-win64.zip` archive from GitHub Releases.
2. Extract the whole archive to any temporary folder.
3. Open Maya 2027.
4. Run the installer from the extracted release:
   - Preferred: drag `install/mayaObjectBuilderInstall.py` into Maya. This unique drop target avoids Maya module-cache collisions and calls the real installer by file path.
   - Fallback: open the Python tab in Maya Script Editor and run:

```python
INSTALLER_PATH = r"C:\path\to\MayaObjectBuilder-v0.2.0-win64\install\mayaObjectBuilderInstall.py"
exec(open(INSTALLER_PATH, encoding="utf-8").read())
```

The installer copies or updates only the runtime files in `Documents/maya/MayaObjectBuilder/`, writes `Documents/maya/modules/MayaObjectBuilder.mod`, loads `MayaObjectBuilder.mll` immediately, and enables plugin autoload for future Maya sessions. The installed runtime folder contains `plug-ins/` and `scripts/`; the release-only `install/` folder is not copied there. `install/install_maya.py` is packaged as the installer implementation used by the drag target.

To update an existing installation, extract the new release archive and run the installer again. The installer unloads the current plugin if it is loaded, refreshes the flat runtime folder in place, rewrites the module file, reloads the plugin, and keeps autoload enabled.

If Maya cannot unload or overwrite the plugin, restart Maya and run the installer again. Make sure you extracted the full release folder before running `install/install_maya.py`; the installer expects the neighboring `plug-ins/`, `scripts/`, `README.md`, and `LICENSE` files to be present.

## Using the plugin in Maya

After installation, Maya loads the plugin through the installed Maya module. You do not need to browse to a `build/` directory.

When the plugin loads, it creates the MayaObjectBuilder dock UI and adds the MayaObjectBuilder menu. Use Maya File > Import or File > Export and select the `Arma P3D` file type for P3D workflows.

Use the dock UI for:

- assigning P3D LOD types and resolutions;
- creating Object Builder selections and proxies;
- editing named properties, materials, mass, and flags;
- importing and exporting `model.cfg` skeleton data;
- generating auto LODs;
- running validation before export.

### Memory LOD workflow

The Memory LOD (`type = 9`) stores named 3D points used by DayZ as attachment sockets, bone references, and other positional markers. In Maya, each point is represented as a named **locator** parented under the Memory LOD transform.

**Creating memory points:**

1. Select the Memory LOD transform (or any object inside it) in the Outliner.
2. In the dock UI, go to the **LOD** tab → **Memory Points** section.
3. Click **Add Memory Point** and enter the point name (e.g. `Pelvis`, `weapon_L`, `Head`).
4. A locator is created at the world origin under the Memory LOD. Use Maya's standard move tools to position it.

To rename a point, select the locator transform in the Outliner and press **F2** (or Edit > Rename). The export uses the transform node's short name as the P3D selection name.

**Importing a P3D with a Memory LOD:**

During import, each single-vertex named selection in the Memory LOD is automatically converted into a locator positioned at the corresponding vertex. Multi-vertex selections (not typical in DayZ Memory LODs) are preserved only as transform metadata and are not shown as locators.

**Export:**

On P3D export, the plugin collects all locator-containing child transforms of the Memory LOD and writes each one as a vertex + named selection TAGG. Locator transforms tagged with `a3obIsProxy` are skipped. The exported point name is the Maya node's short name.

## Build from source

Requirements:

- Windows with Autodesk Maya 2027.
- Maya 2027 devkit available through `DEVKIT_LOCATION`, or at the default path used by `CMakeLists.txt`: `C:/maya_devkits/2027/devkitBase`.
- CMake and Visual Studio generator support for the configured build tree.

Configure and build from the repository root:

```bash
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON
cmake --build build --config Debug
```

Build a Release plugin:

```bash
cmake --build build --config Release
```

## Verify from source

Run the full validation checklist from the repository root:

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

For a single targeted check, run only the matching executable or `mayapy` workflow.

## Launch Maya with the Debug plugin

For manual development checks, build Debug and launch Maya with the Debug plugin explicitly loaded:

```bash
cmake --build build --config Debug
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Autodesk\Maya2027\bin\maya.exe' -ArgumentList @('-command', 'loadPlugin -quiet \"C:/Users/targaryen/source/repos/maya/dayz-object-builder/build/Debug/MayaObjectBuilder.mll\";')"
```

This avoids accidentally loading an installed, packaged, or Release copy while testing local changes.

## Package a release archive

Use the packaging script from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.2.0
```

The script builds the Release plugin, stages a module-friendly package under `dist/MayaObjectBuilder-v<version>-win64/`, creates `dist/MayaObjectBuilder-v<version>-win64.zip`, and writes a SHA256 checksum next to the archive.

The release package includes:

```text
MayaObjectBuilder-v<version>-win64/
  MayaObjectBuilder.mod
  README.md
  LICENSE
  plug-ins/MayaObjectBuilder.mll
  scripts/objectBuilderMenu.py
  scripts/objectBuilderAutoLOD.py
  scripts/mayaObjectBuilderP3DOptions.mel
  install/mayaObjectBuilderInstall.py
  install/install_maya.py
```

Generated `dist/` contents are release artifacts and are not meant to be committed.

## Repository layout

- `src/formats/` — pure P3D and `model.cfg` format code shared by the plugin and C++ tests.
- `src/maya/` — conversion between Maya DAG/mesh data and P3D MLOD structures.
- `src/translators/` — Maya file translator bridge for `Arma P3D` import/export.
- `src/commands/` — Maya commands for validation, metadata editing, proxies, LODs, mass/flags, and `model.cfg` workflows.
- `scripts/` — Maya Python dock/menu UI, auto LOD generation, and file translator option UI.
- `install/` — release installer run from the extracted zip inside Maya.
- `tests/cpp/` — standalone format roundtrip tests.
- `tests/mayapy/` — Maya integration workflows.

## Acknowledgements

Special thanks to [MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder). This project uses the original Blender add-on as a compatibility reference for Object Builder data structures, P3D behavior, and workflow expectations.
