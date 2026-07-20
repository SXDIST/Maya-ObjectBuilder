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
| 🎚️ **LOD tools** | Central LOD list, assign LOD type/resolution, create empty LODs |
| 🏷️ **Metadata editing** | Named selections & properties, materials, mass, flags, proxies |
| 🎨 **PBR textures** | Decode DayZ `.paa` textures (+ `.rvmat`) on import and wire base colour, normal & specular onto materials (`aiStandardSurface` / `blinn`) |
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
import sys; sys.path.insert(0, r"<path to this repo>/tools")
import dev_install
dev_install.install()
```

This writes `Documents/maya/modules/MayaObjectBuilder.mod` pointing at this repo, so Maya loads `plug-ins/` and `scripts/` directly from here. Run `dev_install.uninstall()` to remove the module file.

> [!IMPORTANT]
> Reloading the plugin picks up changes to ordinary modules — dock panels, actions, scene helpers — but **not to the `a3ob*` command classes**. A registered `MPxCommand` keeps executing the version it was registered with, so an edited `doIt` never runs until Maya restarts. Verify command changes under `mayapy` (`python tests/run_all.py --filter 'command*'`), and restart Maya before judging one by hand.

<details>
<summary>Headless variant (write the <code>.mod</code> without loading)</summary>

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'tools'); import dev_install; dev_install.install(load=False)"
```

</details>

---

## 🎛️ Using the plugin in Maya

After installation Maya loads the plugin through the installed module — no need to browse to any build directory. On load it creates the **MayaObjectBuilder dock** and adds the **MayaObjectBuilder menu**. For P3D files use Maya **File > Import / Export** and pick the **`Arma P3D`** file type.

The dock is a vertical stack of **collapsible panels** — each remembers its expanded/collapsed state:

| Panel | Purpose |
|-------|---------|
| ⚡ **Quick Actions** | Import/Export P3D · Auto LOD · Validate |
| 📋 **LODs** | Central list of every LOD in the scene — select, frame, rename, duplicate, delete, add new LODs |
| 🎚️ **LOD Properties** | Assign P3D LOD type & resolution to the selection |
| 🤖 **Auto LOD** | Generate resolution/geometry/memory/fire/view LODs from a mesh |
| ⚖️ **Mass & Flags** | Vertex mass and face/vertex component flags |
| 🏷️ **Named Properties** | Key/value properties stored on the selected LOD |
| 🎨 **Materials** | Texture (`.paa`) and `.rvmat` paths per material, the texture root, and the alpha→transparency toggle |
| 🗂️ **Selections** | Filter & maintain selections, proxies, and flag sets |
| 🔗 **Proxies** | Create/update proxy metadata |
| 📍 **Memory Points** | Named locators for the Memory LOD |
| ✅ **Validation** | Check LODs before export (whole scene or selection) |

> [!TIP]
> **Textures on import** — Maya can't read `.paa` directly, so the plugin decodes each texture to a cached PNG and wires it onto the material (base colour + reconstructed normal from `_nohq` + specular from `_smdi`/`.rvmat`). For the mod-relative paths in a P3D to resolve, set the **texture root** in the **Materials** panel (or the *Set Texture Root* menu item) to your unpacked mod / `P:` drive. Skeleton (`model.cfg`) import/export lives in the **MayaObjectBuilder menu**, not a dock panel.

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

There is **no build step**. One command runs everything from the repository root:

```bash
python tests/run_all.py
```

That is the 10 pure-Python format tests, `py_compile` over every `.py` on disk, the 25 Maya
integration workflows (each in its own process — `maya.standalone` cannot be initialized twice),
and the P3D byte gate. Useful flags:

```bash
python tests/run_all.py --only python      # no Maya needed
python tests/run_all.py --filter 'weight*'
python tests/run_all.py --mayapy "C:/path/to/mayapy.exe"   # or set $MAYAPY
```

**The P3D byte gate.** `tests/golden.py` records the SHA256 of exported fixtures and re-checks it,
so a refactor cannot silently change the file format — Object Builder opens a corrupted `.p3d`
without complaining. `run_all.py` runs it; on its own:

```bash
mayapy tests/golden.py verify
```

> [!WARNING]
> Never run `tests/golden.py capture` to make a failing gate pass. That overwrites the baseline
> with whatever the current code produces, which makes the check meaningless. Capture only when
> the byte output is *intended* to change, and say so in the commit.

> [!NOTE]
> Fixtures live under `Arma3ObjectBuilder-master/tests/inputs/`. Clone the reference add-on there
> if the folder is missing: `git clone https://github.com/MrClock8163/Arma3ObjectBuilder`
> The `.paa` tests skip cleanly without `tests/paa/*.paa`.

---

## 🚀 Launch Maya for manual checks

Register the dev module and launch Maya (no build):

```powershell
powershell -ExecutionPolicy Bypass -File tools/launch_maya_debug.ps1
```

This registers the edit-in-place module via `dev_install` and starts Maya 2027; the plugin autoloads from `plug-ins/MayaObjectBuilder.py`.

---

## 🗜️ Package a release archive

Plain file copy + zip — **no compilation**:

```powershell
powershell -ExecutionPolicy Bypass -File tools/package_release.ps1 -Version 0.1.0
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
| `scripts/a3ob/formats/` | Maya-independent format code (`p3d.py`, `binary.py`, `model_cfg.py`, `paa.py` texture decoder, `rvmat.py`, `serialize.py`) — runs under plain Python, no Maya |
| `scripts/a3ob/mayabridge/` | Maya glue (API 2.0): `attributes.py` (the `a3ob*` schema), Maya↔MLOD conversion (`import_/`, `export/`), `commands/`, `translator.py`, the `paatex/` `.paa`→material pipeline, and the leaf helpers `lodwalk.py`, `skinquery.py`, `progress.py`, `weightsync.py` |
| `scripts/a3ob/ui/` | Dock UI: `dock.py` + `panels/` (collapsible sections), `actions/` (scene business logic), `scene/` (Qt-free helpers), `autolod/`, `entry.py`, `_undo.py`, `constants.py`, `recent.py` |
| `scripts/objectBuilderMenu.py`, `objectBuilderAutoLOD.py` | Facades the plugin and the mayapy tests load **by path** — keep them |
| `plug-ins/MayaObjectBuilder.py` | Main scripted plugin (API 2.0): commands, dock, auto-loads the translator |
| `plug-ins/MayaObjectBuilderTranslator.py` | Companion plugin (API 1.0): the `Arma P3D` `MPxFileTranslator` |
| `tools/` | Developer-only: `dev_install.py`, `launch_maya_debug.ps1`, `package_release.ps1`. Deliberately **outside** `scripts/`, which Maya puts on `PYTHONPATH` — anything there is importable in every session |
| `install/` | Release installer run from the extracted zip inside Maya |
| `tests/python/` | No-Maya tests: format round-trips, the `a3ob*` schema lock, QEM invariants, the numpy-free fallback path |
| `tests/mayapy/` | Maya integration workflows; `_harness.py` holds the shared bootstrap and assertions |
| `tests/run_all.py`, `tests/golden.py` | The one-command runner and the P3D byte gate |

---

## 🙏 Acknowledgements

Special thanks to **[MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder)**. This project uses the original Blender add-on as a compatibility reference for Object Builder data structures, P3D behavior, and workflow expectations; the `.paa` texture decoder (`formats/paa.py`: DXT1/DXT5 + LZO1X) is ported from its `io/data_paa.py` and `io/compression.py`.

<div align="center">
<sub>Licensed under the <a href="LICENSE">MIT License</a>.</sub>
</div>
