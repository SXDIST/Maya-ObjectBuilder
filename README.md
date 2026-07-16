# Maya ObjectBuilder

Maya ObjectBuilder is an Autodesk Maya 2027 plugin for DayZ/Object Builder-style P3D asset workflows. It adds native Maya import/export support for P3D MLOD files and provides tools for editing Object Builder metadata directly in Maya.

The plugin is written in **pure Python** (Maya Python API 2.0, with a tiny API-1.0 shell for the file translator). There is no compilation step — edit the Python and reload.

The repository also contains the original Blender add-on source under `Arma3ObjectBuilder-master/` as a compatibility reference for Object Builder data structures and P3D behavior. That folder is not part of the Maya plugin runtime.

## Features

- `Arma P3D` file translator for Maya File > Import/Export.
- P3D MLOD import/export with LOD metadata preservation.
- Object Builder metadata editing from the Maya dock UI (accordion panels):
  - LOD type/resolution assignment and empty LOD creation;
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
INSTALLER_PATH = r"C:\path\to\MayaObjectBuilder-v0.1.0-win64\install\mayaObjectBuilderInstall.py"
exec(open(INSTALLER_PATH, encoding="utf-8").read())
```

The installer copies or updates only the runtime files in `Documents/maya/MayaObjectBuilder/`, writes `Documents/maya/modules/MayaObjectBuilder.mod`, loads the `MayaObjectBuilder` plugin immediately, and enables plugin autoload for future Maya sessions. The installed runtime folder contains `plug-ins/` and `scripts/`; the release-only `install/` folder is not copied there. `install/install_maya.py` is packaged as the installer implementation used by the drag target.

To update an existing installation, extract the new release archive and run the installer again. The installer unloads the current plugin if it is loaded, refreshes the flat runtime folder in place, rewrites the module file, reloads the plugin, and keeps autoload enabled.

If Maya cannot unload or overwrite the plugin, restart Maya and run the installer again. Make sure you extracted the full release folder before running `install/install_maya.py`; the installer expects the neighboring `plug-ins/`, `scripts/`, `README.md`, and `LICENSE` files to be present.

The main `MayaObjectBuilder` plugin auto-loads its companion `MayaObjectBuilderTranslator` plugin (which registers the `Arma P3D` file translator), so you only ever manage a single "MayaObjectBuilder" plugin in Maya.

## Local development install (edit-in-place)

For working on the plugin from this repository without copying files, register the repo as a Maya module. Inside Maya or `mayapy`:

```python
import dev_install
dev_install.install()
```

This writes `Documents/maya/modules/MayaObjectBuilder.mod` pointing at this repository, so Maya loads `plug-ins/` and `scripts/` directly from here. Edit the Python, reload the plugin, and your changes take effect — no copy, no build. Run `dev_install.uninstall()` to remove the module file.

Headless variant (writes the `.mod` without loading):

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'scripts'); import dev_install; dev_install.install(load=False)"
```

## Using the plugin in Maya

After installation, Maya loads the plugin through the installed Maya module. You do not need to browse to a build directory.

When the plugin loads, it creates the MayaObjectBuilder dock UI and adds the MayaObjectBuilder menu. Use Maya File > Import or File > Export and select the `Arma P3D` file type for P3D workflows.

The dock is a vertical stack of collapsible panels (each remembers its expanded/collapsed state):

- **Quick Actions** — Import/Export P3D, Auto LOD, Validate.
- **LOD Properties** — assign P3D LOD type and resolution to the selection.
- **Auto LOD** — generate resolution/geometry/memory/fire/view LODs from a mesh.
- **Mass & Flags** — vertex mass and face/vertex component flags.
- **Named Properties** — key/value properties stored on the selected LOD.
- **Materials** — texture and `.rvmat` paths for the mesh's materials.
- **Selections** — filter and maintain Object Builder selections, proxies, and flag sets.
- **Proxies** — create/update proxy metadata.
- **Memory Points** — named locators for the Memory LOD (see below).
- **Skeleton (model.cfg)** — import/export skeleton data.
- **Validation** — check LODs before export (whole scene or selection).

### Memory LOD workflow

The Memory LOD (`type = 9`) stores named 3D points used by DayZ as attachment sockets, bone references, and other positional markers. In Maya, each point is represented as a named **locator** parented under the Memory LOD transform.

**Creating memory points:**

1. Select the Memory LOD transform (or any object inside it) in the Outliner.
2. In the dock UI, expand the **Memory Points** panel (it is only enabled when a Memory LOD is selected).
3. Click **Add Memory Point** and enter the point name (e.g. `Pelvis`, `weapon_L`, `Head`).
4. A locator is created at the world origin under the Memory LOD. Use Maya's standard move tools to position it.

To rename a point, select the locator transform in the Outliner and press **F2** (or Edit > Rename). The export uses the transform node's short name as the P3D selection name.

**Importing a P3D with a Memory LOD:**

During import, each single-vertex named selection in the Memory LOD is automatically converted into a locator positioned at the corresponding vertex. Multi-vertex selections (not typical in DayZ Memory LODs) are preserved only as transform metadata and are not shown as locators.

**Export:**

On P3D export, the plugin collects all locator-containing child transforms of the Memory LOD and writes each one as a vertex + named selection TAGG. Locator transforms tagged with `a3obIsProxy` are skipped. The exported point name is the Maya node's short name.

## Verify from source

There is no build step. Run the validation checklist from the repository root.

Pure-Python format tests (plain system Python, no Maya):

```bash
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
```

Python syntax check:

```bash
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py scripts/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py
```

Maya integration workflows (load the plugin, exercise import/export + commands + UI):

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

The format tests use the fixtures under `Arma3ObjectBuilder-master/tests/inputs/`. Clone the reference add-on there if the folder is missing (`git clone https://github.com/MrClock8163/Arma3ObjectBuilder`).

## Launch Maya for manual checks

For interactive development, register the dev module and launch Maya (no build):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/launch_maya_debug.ps1
```

This registers the edit-in-place module via `dev_install` and starts Maya 2027; the plugin autoloads from `plug-ins/MayaObjectBuilder.py`.

## Package a release archive

Use the packaging script from the repository root (plain file copy + zip, no compilation):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

The script stages a module-friendly package under `dist/MayaObjectBuilder-v<version>-win64/`, creates `dist/MayaObjectBuilder-v<version>-win64.zip`, and writes a SHA256 checksum next to the archive.

The release package includes:

```text
MayaObjectBuilder-v<version>-win64/
  MayaObjectBuilder.mod
  README.md
  LICENSE
  plug-ins/MayaObjectBuilder.py
  plug-ins/MayaObjectBuilderTranslator.py
  scripts/objectBuilderMenu.py
  scripts/objectBuilderAutoLOD.py
  scripts/mayaObjectBuilderP3DOptions.mel
  scripts/a3ob/**            (formats, mayabridge, ui packages)
  install/mayaObjectBuilderInstall.py
  install/install_maya.py
```

Generated `dist/` contents are release artifacts and are not meant to be committed.

## Repository layout

- `scripts/a3ob/formats/` — Maya-independent file format code (`binary.py`, `p3d.py`, `model_cfg.py`), unit-testable with plain Python.
- `scripts/a3ob/mayabridge/` — the Maya glue (API 2.0): attribute schema, Maya↔MLOD mesh conversion, the `a3ob*` commands, `model.cfg` commands, and the translator bodies.
- `scripts/a3ob/ui/` — UI support: `constants.py` (data tables) and `scene_ops.py` (Qt-free Maya-scene helpers).
- `scripts/objectBuilderMenu.py` — the Qt dock/menu UI (`MayaObjectBuilderDock`) and command-wrapper layer.
- `scripts/objectBuilderAutoLOD.py` — the auto-LOD generator.
- `plug-ins/MayaObjectBuilder.py` — main scripted plugin (API 2.0): registers commands, opens the dock, auto-loads the translator.
- `plug-ins/MayaObjectBuilderTranslator.py` — companion plugin (API 1.0): the `Arma P3D` `MPxFileTranslator`.
- `install/` — release installer run from the extracted zip inside Maya.
- `tests/python/` — pure-Python format roundtrip tests.
- `tests/mayapy/` — Maya integration workflows.

## Acknowledgements

Special thanks to [MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder). This project uses the original Blender add-on as a compatibility reference for Object Builder data structures, P3D behavior, and workflow expectations.
