<div align="center">

# 🧩 Maya ObjectBuilder

**Native DayZ / Object Builder P3D asset workflows inside Autodesk Maya 2027 — in pure Python.**

[![Maya](https://img.shields.io/badge/Maya-2027-0696D7?logo=autodesk&logoColor=white)](https://www.autodesk.com/products/maya)
[![Pure Python](https://img.shields.io/badge/Pure-Python-3776AB?logo=python&logoColor=white)](#)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](#)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![No build step](https://img.shields.io/badge/Build-none-success)](#)

</div>

---

Maya ObjectBuilder is an Autodesk **Maya 2027** plugin for DayZ / Object Builder-style **P3D** asset workflows. It adds native Maya import/export for P3D MLOD files and tools for editing Object Builder metadata directly in Maya.

The plugin is written in **pure Python** (Maya Python API 2.0, with a tiny API-1.0 shell for the file translator) — **there is no compilation step**. Edit the Python and reload.

> [!NOTE]
> The repository also contains the original Blender add-on under `Arma3ObjectBuilder-master/` as a compatibility reference for Object Builder data structures and P3D behavior. That folder is **not** part of the Maya plugin runtime.

## Contents

- [✨ Features](#-features)
- [📦 Installation from a release](#-installation-from-a-github-release)
- [🛠️ Local development install](#️-local-development-install-edit-in-place)
- [🎛️ Using the plugin](#️-using-the-plugin-in-maya)
- [📍 Memory LOD workflow](#-memory-lod-workflow)
- [✅ Verify from source](#-verify-from-source)
- [🚀 Launch Maya for manual checks](#-launch-maya-for-manual-checks)
- [🗜️ Package a release](#️-package-a-release-archive)
- [🗂️ Repository layout](#️-repository-layout)
- [🙏 Acknowledgements](#-acknowledgements)

---

## ✨ Features

| | |
|---|---|
| 🔄 **P3D translator** | `Arma P3D` file type for Maya **File > Import / Export** |
| 🧱 **MLOD import/export** | Full LOD metadata preservation on round-trip |
| 🎚️ **LOD tools** | Assign LOD type/resolution, create empty LODs |
| 🏷️ **Metadata editing** | Named selections & properties, materials, mass, flags, proxies |
| ⚡ **Auto LOD** | Generate resolution / geometry / memory / fire / view LODs from a mesh |
| 🦴 **model.cfg** | Skeleton import/export workflow |
| ✅ **Validation** | Pre-export checks for the whole scene or the selection |
| 📥 **Installer** | Copies runtime files, writes a Maya module, loads + autoloads the plugin |

All editing happens from a **dockable UI of collapsible panels** (see [Using the plugin](#️-using-the-plugin-in-maya)).

---

## 📦 Installation from a GitHub release

1. Download the latest **`MayaObjectBuilder-v*-win64.zip`** from GitHub Releases.
2. Extract the **whole** archive to any temporary folder.
3. Open **Maya 2027**.
4. Run the installer from the extracted release:

   - **Preferred** — drag **`install/mayaObjectBuilderInstall.py`** into Maya. This unique drop target avoids Maya module-cache collisions and calls the real installer by file path.
   - **Fallback** — open the **Python** tab in the Script Editor and run:

     ```python
     INSTALLER_PATH = r"C:\path\to\MayaObjectBuilder-v0.1.0-win64\install\mayaObjectBuilderInstall.py"
     exec(open(INSTALLER_PATH, encoding="utf-8").read())
     ```

The installer copies/updates only the runtime files in `Documents/maya/MayaObjectBuilder/`, writes `Documents/maya/modules/MayaObjectBuilder.mod`, loads the `MayaObjectBuilder` plugin immediately, and enables autoload for future sessions. The installed folder contains `plug-ins/` and `scripts/`; the release-only `install/` folder is not copied there.

> [!TIP]
> The main `MayaObjectBuilder` plugin **auto-loads its companion** `MayaObjectBuilderTranslator` (which registers the `Arma P3D` translator), so you only ever manage a single "MayaObjectBuilder" plugin in Maya.

**Updating:** extract the new archive and run the installer again — it unloads the current plugin, refreshes the runtime folder in place, rewrites the module file, reloads, and keeps autoload on. If Maya cannot unload/overwrite the plugin, restart Maya and re-run. Make sure the full release folder was extracted — the installer expects the neighboring `plug-ins/`, `scripts/`, `README.md`, and `LICENSE`.

---

## 🛠️ Local development install (edit-in-place)

Work on the plugin straight from this repository — **no copy, no build**. Inside Maya or `mayapy`:

```python
import dev_install
dev_install.install()
```

This writes `Documents/maya/modules/MayaObjectBuilder.mod` pointing at this repo, so Maya loads `plug-ins/` and `scripts/` directly from here. Edit the Python, reload the plugin, done. Run `dev_install.uninstall()` to remove the module file.

<details>
<summary>Headless variant (write the <code>.mod</code> without loading)</summary>

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'scripts'); import dev_install; dev_install.install(load=False)"
```

</details>

---

## 🎛️ Using the plugin in Maya

After installation Maya loads the plugin through the installed module — no need to browse to any build directory. On load it creates the **MayaObjectBuilder dock** and adds the **MayaObjectBuilder menu**. For P3D files use Maya **File > Import / Export** and pick the **`Arma P3D`** file type.

The dock is a vertical stack of **collapsible panels** — each remembers its expanded/collapsed state:

| Panel | Purpose |
|-------|---------|
| ⚡ **Quick Actions** | Import/Export P3D · Auto LOD · Validate |
| 🎚️ **LOD Properties** | Assign P3D LOD type & resolution to the selection |
| 🤖 **Auto LOD** | Generate resolution/geometry/memory/fire/view LODs from a mesh |
| ⚖️ **Mass & Flags** | Vertex mass and face/vertex component flags |
| 🏷️ **Named Properties** | Key/value properties stored on the selected LOD |
| 🎨 **Materials** | Texture and `.rvmat` paths for the mesh's materials |
| 🗂️ **Selections** | Filter & maintain selections, proxies, and flag sets |
| 🔗 **Proxies** | Create/update proxy metadata |
| 📍 **Memory Points** | Named locators for the Memory LOD |
| 🦴 **Skeleton (model.cfg)** | Import/export skeleton data |
| ✅ **Validation** | Check LODs before export (whole scene or selection) |

### 📍 Memory LOD workflow

The Memory LOD (`type = 9`) stores named 3D points used by DayZ as attachment sockets, bone references, and other positional markers. In Maya each point is a named **locator** parented under the Memory LOD transform.

<details>
<summary><b>Creating memory points</b></summary>

1. Select the Memory LOD transform (or any object inside it) in the Outliner.
2. In the dock, expand the **Memory Points** panel (enabled only when a Memory LOD is selected).
3. Click **Add Memory Point** and enter the point name (e.g. `Pelvis`, `weapon_L`, `Head`).
4. A locator is created at the world origin under the Memory LOD. Use Maya's move tools to position it.

To rename a point, select the locator transform in the Outliner and press **F2** (or Edit > Rename). Export uses the transform node's short name as the P3D selection name.

</details>

<details>
<summary><b>Importing & exporting Memory LODs</b></summary>

**Import** — each single-vertex named selection in the Memory LOD is converted into a locator positioned at the corresponding vertex. Multi-vertex selections (atypical for DayZ Memory LODs) are preserved only as transform metadata and are not shown as locators.

**Export** — the plugin collects all locator-containing child transforms of the Memory LOD and writes each as a vertex + named selection TAGG. Locator transforms tagged with `a3obIsProxy` are skipped. The exported name is the Maya node's short name.

</details>

---

## ✅ Verify from source

There is **no build step**. Run the checklist from the repository root.

**Pure-Python format tests** (plain system Python, no Maya):

```bash
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
```

**Python syntax check:**

```bash
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py scripts/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py
```

**Maya integration workflows** (load the plugin, exercise import/export + commands + UI):

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

> [!NOTE]
> The format tests use fixtures under `Arma3ObjectBuilder-master/tests/inputs/`. Clone the reference add-on there if the folder is missing:
> `git clone https://github.com/MrClock8163/Arma3ObjectBuilder`

---

## 🚀 Launch Maya for manual checks

Register the dev module and launch Maya (no build):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/launch_maya_debug.ps1
```

This registers the edit-in-place module via `dev_install` and starts Maya 2027; the plugin autoloads from `plug-ins/MayaObjectBuilder.py`.

---

## 🗜️ Package a release archive

Plain file copy + zip — **no compilation**:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_release.ps1 -Version 0.1.0
```

Stages `dist/MayaObjectBuilder-v<version>-win64/`, creates the `.zip`, and writes a SHA256 checksum next to the archive.

<details>
<summary>Release package contents</summary>

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

</details>

---

## 🗂️ Repository layout

| Path | Responsibility |
|------|----------------|
| `scripts/a3ob/formats/` | Maya-independent format code (`binary.py`, `p3d.py`, `model_cfg.py`) — unit-testable with plain Python |
| `scripts/a3ob/mayabridge/` | Maya glue (API 2.0): attribute schema, Maya↔MLOD conversion, `a3ob*` commands, `model.cfg` commands, translator bodies |
| `scripts/a3ob/ui/` | UI support: `constants.py` (data tables) + `scene_ops.py` (Qt-free scene helpers) |
| `scripts/objectBuilderMenu.py` | Qt dock/menu UI (`MayaObjectBuilderDock`) + command wrappers |
| `scripts/objectBuilderAutoLOD.py` | Auto-LOD generator |
| `plug-ins/MayaObjectBuilder.py` | Main scripted plugin (API 2.0): commands, dock, auto-loads the translator |
| `plug-ins/MayaObjectBuilderTranslator.py` | Companion plugin (API 1.0): the `Arma P3D` `MPxFileTranslator` |
| `install/` | Release installer run from the extracted zip inside Maya |
| `tests/python/` | Pure-Python format roundtrip tests |
| `tests/mayapy/` | Maya integration workflows |

---

## 🙏 Acknowledgements

Special thanks to **[MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder)**. This project uses the original Blender add-on as a compatibility reference for Object Builder data structures, P3D behavior, and workflow expectations.

<div align="center">
<sub>Licensed under the <a href="LICENSE">MIT License</a>.</sub>
</div>
