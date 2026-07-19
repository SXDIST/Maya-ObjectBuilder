---
name: maya-debug-launch
description: Register the MayaObjectBuilder dev module (edit-in-place) and launch interactive Maya 2027 with the pure-Python plugin autoloaded from plug-ins/MayaObjectBuilder.py for manual inspection.
---

# maya-debug-launch

Use this when the user wants to open Maya for manual plugin checks, or says in Russian: "открой Maya с плагином", "запусти Maya с плагином", "хочу проверить плагин в Maya".

Prefer the `maya-debug-launcher` project subagent.

The plugin is pure Python — there is no compilation step. Register this repo as a Maya module
(edit-in-place) and open interactive Maya with the plugin loaded.

## Plugin path

The plugin loads from this repo, no copy:

```text
plug-ins/MayaObjectBuilder.py
```

## Preferred launch command

Does dev_install (writes the `.mod`) + launches Maya, no build:

```bash
powershell -ExecutionPolicy Bypass -File tools/launch_maya_debug.ps1
```

## Alternative manual steps

```bash
# 1. Register the repo as a Maya module (edit-in-place)
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'tools'); import dev_install; dev_install.install(load=False)"
# 2. Launch interactive Maya (plugin autoloads from plug-ins/MayaObjectBuilder.py)
"/c/Program Files/Autodesk/Maya2027/bin/maya.exe"
```

## Rules

- Register the dev module first (`launch_maya_debug.ps1` or `dev_install.install`).
- Load the plugin from this repo's `plug-ins/MayaObjectBuilder.py` — no build, no `.mll`.
- Do not use a packaged/installed end-user copy under `Documents/maya/`.
- Do not kill existing Maya processes unless explicitly asked.
- This workflow launches interactive Maya; mayapy smoke tests are only diagnostic fallback.
- After Maya opens, tell the user manual GUI verification is ready.

## Output format

- Dev module registration status.
- Exact plugin path targeted.
- Launch command used.
- Manual checks to perform in Maya.
