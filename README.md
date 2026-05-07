# Maya ObjectBuilder

Maya ObjectBuilder is an Autodesk Maya 2027 plugin for DayZ/Object Builder-style asset workflows. It provides a native Maya bridge for importing, exporting, validating, and editing P3D MLOD assets and related metadata used by Object Builder-compatible pipelines.

## Current scope

- Maya 2027 C++ plugin built as `MayaObjectBuilder.mll`.
- Native `Arma P3D` file translator for Maya File > Import/Export workflows.
- P3D LOD mesh import/export with Object Builder metadata preservation.
- LOD assignment, named properties, proxy metadata, material metadata, vertex mass, face/vertex flags, selections, and validation tools.
- `model.cfg` skeleton import/export MVP.

The repository also contains the original Blender add-on source under `Arma3ObjectBuilder-master/` as a reference implementation and compatibility baseline.

## Installation from GitHub release

1. Download the latest `MayaObjectBuilder-v*-win64.zip` archive from GitHub Releases.
2. Extract the archive to any temporary folder.
3. Open Maya 2027.
4. Open the Python tab in Maya Script Editor and run:

```python
INSTALLER_PATH = r"C:\path\to\MayaObjectBuilder-v0.1.0-win64\install\install_maya.py"
exec(open(INSTALLER_PATH).read())
```

The installer copies the plugin package into your Maya user folder, writes a Maya module file, loads `MayaObjectBuilder.mll` immediately, and enables plugin autoload so it is available after restarting Maya.

## Using the plugin in Maya

After installation, Maya loads the plugin through the installed Maya module. You do not need to browse to a `build/` directory.

When the plugin loads, it creates the MayaObjectBuilder dock UI and adds the MayaObjectBuilder menu. The plugin intentionally does not create a shelf button.

Use Maya File > Import or File > Export and select the `Arma P3D` file type for P3D workflows. The dock UI is used for Object Builder metadata editing, LOD assignment, `model.cfg` tools, selections, materials, proxies, mass/flags, and validation.

## Build from source

Configure and build from the repository root:

```bash
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON
cmake --build build --config Release
```

## Package a GitHub release archive

Use the packaging script from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

This builds the Release plugin, stages a module-friendly package under `dist/MayaObjectBuilder-v0.1.0-win64/`, creates `dist/MayaObjectBuilder-v0.1.0-win64.zip`, and writes a SHA256 checksum file next to the archive.

## Verify from source

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Acknowledgements

Special thanks to [MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder). This project uses the original Blender add-on as a compatibility reference for Object Builder data structures, P3D behavior, and workflow expectations.
