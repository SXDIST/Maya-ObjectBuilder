---
name: plugin-smoke
description: Smoke test MayaObjectBuilder plugin loading, command registration, P3D translator registration, and Python UI entrypoints in Maya 2027 mayapy.
---

# plugin-smoke

Use this when the user asks to check Maya plugin load/unload, UI dock/menu behavior, command registration, translator registration, or says in Russian: "проверь плагин", "запусти Maya smoke", "не грузится mll", "не видно команды".

For UI or command wiring investigations, prefer the `maya-ui-maintainer` project subagent.

## First inspect

- `scripts/objectBuilderMenu.py`
- `scripts/mayaObjectBuilderP3DOptions.mel`
- `plug-ins/MayaObjectBuilder.py`
- `scripts/a3ob/mayabridge/commands.py`
- `plug-ins/MayaObjectBuilderTranslator.py` and `scripts/a3ob/mayabridge/translator.py` if translator registration is missing.

## Compile check (pure Python — no build step)

```bash
python -m py_compile plug-ins/MayaObjectBuilder.py scripts/objectBuilderMenu.py
```

## mayapy smoke snippet

Run from repo root:

```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import sys; from pathlib import Path; import maya.standalone; maya.standalone.initialize(name='python'); import maya.cmds as cmds; root=Path.cwd(); sys.path.insert(0, str(root/'scripts')); plugin=str(root/'plug-ins'/'MayaObjectBuilder.py'); cmds.loadPlugin(plugin, quiet=True); print('loaded', cmds.pluginInfo('MayaObjectBuilder', q=True, loaded=True)); print('commands', cmds.pluginInfo('MayaObjectBuilder', q=True, command=True)); translators=cmds.translator(q=True, list=True) or []; print('p3d translators', [t for t in translators if 'P3D' in t or 'Arma' in t]); import objectBuilderMenu as ui; print('ui module', bool(ui)); cmds.unloadPlugin('MayaObjectBuilder'); print('unloaded', not cmds.pluginInfo('MayaObjectBuilder', q=True, loaded=True)); maya.standalone.uninitialize()"
```

## Common failures

- Plugin cannot load: check Python import/syntax errors, script path setup, and `initializePlugin()` in `plug-ins/MayaObjectBuilder.py`.
- Commands missing: check `initializePlugin()` registration and matching deregistration.
- Translator missing: check the `Arma P3D` translator registration in `plug-ins/MayaObjectBuilderTranslator.py` and file type name.
- Python import fails: check `scripts/objectBuilderMenu.py`, script path setup, and py_compile output.
- UI dock issues in full Maya may not reproduce in mayapy; say so explicitly and use a GUI smoke only when requested.

## Output format

- Compile-check status.
- Plugin load status.
- Registered command list.
- Registered P3D translator list.
- UI module import status.
- Unload status.
