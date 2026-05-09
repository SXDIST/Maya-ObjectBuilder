---
name: p3d-validate
description: Run the full MayaObjectBuilder validation checklist: Debug build, P3D roundtrip, model.cfg test, py_compile, and Maya 2027 mayapy workflows.
---

# p3d-validate

Use this when the user asks to validate the repo, run the full checklist, check that P3D import/export still works, or says in Russian: "проверь всё", "запусти тесты", "полная проверка", "валидация p3d".

This is a procedural workflow. Prefer the `validation-runner` project subagent when available, especially if the main chat should stay small.

## Rules

- Run from the repo root.
- Do not change CMake generator settings.
- Do not edit `Arma3ObjectBuilder-master/`; it is reference/test input only.
- Report concise pass/fail status per command, then the first relevant failure.
- If a command fails, stop unless the next command is needed to isolate the failure.

## Commands

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Common failures

- Build failure: inspect the changed C++ file first, then `src/PluginMain.cpp` if registration broke.
- `p3d_roundtrip` failure: inspect `src/formats/P3D.cpp`, `src/formats/P3D.h`, `src/maya/MayaMeshExport.cpp`, `src/maya/MayaMeshImport.cpp`.
- `model_cfg_test` failure: inspect `src/formats/ModelCfg.cpp` and `src/commands/ModelCfgCommands.cpp`.
- `py_compile` failure: inspect the exact Python file and line from the traceback.
- `mayapy` workflow failure: preserve the traceback and inspect the workflow assertion before changing plugin code.

## Output format

- `PASS` / `FAIL` table for each command.
- Failure summary with file/line references when available.
- Suggested next action, not a broad rewrite.
