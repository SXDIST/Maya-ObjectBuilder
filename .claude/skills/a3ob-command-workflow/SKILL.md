---
name: a3ob-command-workflow
description: Work on MayaObjectBuilder a3ob* commands, validation behavior, LOD creation, mass, flags, proxies, and UI command wrappers.
---

# a3ob-command-workflow

Use this when the task mentions `a3obValidate`, `a3obCreateLOD`, `a3obSetMass`, `a3obSetFlag`, `a3obProxy`, command registration, validation rules, or Russian requests like "команды a3ob", "валидация меша", "масса", "флаги", "прокси", "создание LOD".

For implementation-heavy command changes, prefer the `a3ob-command-maintainer` project subagent.

## First inspect

- `src/commands/StubCommands.cpp`
- `src/PluginMain.cpp`
- `scripts/objectBuilderMenu.py`
- `tests/mayapy/p3d_workflow.py`

## Focus areas

- `a3obValidate`: mesh/LOD checks and `MItMeshPolygon` validation loop.
- `a3obCreateLOD`: transform attributes `a3obLodType`, `a3obResolution`, `a3obResolutionSignature`.
- `a3obSetMass`: mass assignment expected by P3D export.
- `a3obSetFlag`: objectSet flag metadata.
- `a3obProxy`: proxy selection metadata and path behavior.
- `src/PluginMain.cpp::initializePlugin()`: registration and deregistration symmetry.
- `scripts/objectBuilderMenu.py`: UI wrappers should match command flags and expected names.

## Workflow

1. Locate the exact command implementation and its UI/test caller.
2. Check whether behavior is command-only, UI wrapper, exporter/importer metadata, or registration.
3. Prefer modifying the owning command over adding Python-side compensating behavior.
4. Add or update mayapy coverage in `tests/mayapy/p3d_workflow.py` when behavior changes.
5. Run targeted Python compile and mayapy workflow before reporting success.

## Verification commands

```bash
cmake --build build --config Debug
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

## Output format

- Command changed or inspected.
- UI/test callers checked.
- Registration impact.
- Verification result.
