---
name: maya-debug-launch
description: Build the Debug MayaObjectBuilder plugin and launch interactive Maya 2027 with build/Debug/MayaObjectBuilder.mll explicitly loaded for manual inspection.
---

# maya-debug-launch

Use this when the user wants a Debug build followed by opening Maya for manual plugin checks, or says in Russian: "собери debug и открой Maya", "запусти Maya с плагином", "хочу проверить плагин в Maya".

Prefer the `maya-debug-launcher` project subagent.

## Build first

```bash
cmake --build build --config Debug
```

## Plugin path

Always target the Debug plugin directly:

```text
C:/Users/targaryen/source/repos/maya/dayz-object-builder/build/Debug/MayaObjectBuilder.mll
```

## Preferred launch command

```bash
powershell.exe -NoProfile -Command "Start-Process -FilePath 'C:\Program Files\Autodesk\Maya2027\bin\maya.exe' -ArgumentList @('-command', 'loadPlugin -quiet \"C:/Users/targaryen/source/repos/maya/dayz-object-builder/build/Debug/MayaObjectBuilder.mll\";')"
```

## Alternative direct launch

```bash
"/c/Program Files/Autodesk/Maya2027/bin/maya.exe" -command "loadPlugin -quiet \"C:/Users/targaryen/source/repos/maya/dayz-object-builder/build/Debug/MayaObjectBuilder.mll\";"
```

## Rules

- Run the Debug build first.
- Do not use Release, packaged `plug-ins/`, or installed copies.
- Do not rely on `build/launch_maya_debug_plugin.mel` unless it exists at runtime.
- Do not kill existing Maya processes unless explicitly asked.
- This workflow launches interactive Maya; mayapy smoke tests are only diagnostic fallback.
- After Maya opens, tell the user manual GUI verification is ready.

## Output format

- Debug build status.
- Exact plugin path targeted.
- Launch command used.
- Manual checks to perform in Maya.
