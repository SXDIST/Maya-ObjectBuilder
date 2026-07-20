---
name: p3d-validate
description: Run the full MayaObjectBuilder validation checklist: P3D roundtrip, model.cfg test, py_compile, and Maya 2027 mayapy workflows.
---

# p3d-validate

Use this when the user asks to validate the repo, run the full checklist, check that P3D import/export still works, or says in Russian: "проверь всё", "запусти тесты", "полная проверка", "валидация p3d".

This is a procedural workflow. Prefer the `validation-runner` project subagent when available, especially if the main chat should stay small.

## Rules

- Run from the repo root.
- The plugin is pure Python — there is no build step.
- Do not edit `Arma3ObjectBuilder-master/`; it is reference/test input only.
- Report concise pass/fail status per command, then the first relevant failure.
- If a command fails, stop unless the next command is needed to isolate the failure.

## Commands

```bash
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py tools/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Common failures

- `test_p3d_roundtrip` failure: inspect `scripts/a3ob/formats/p3d.py`, `scripts/a3ob/formats/binary.py`, `scripts/a3ob/mayabridge/export/exporter.py`, `scripts/a3ob/mayabridge/import_/importer.py`.
- `test_model_cfg` failure: inspect `scripts/a3ob/formats/model_cfg.py` and `scripts/a3ob/mayabridge/model_cfg_commands.py`.
- `py_compile` failure: inspect the exact Python file and line from the traceback.
- `mayapy` workflow failure: preserve the traceback and inspect the workflow assertion before changing plugin code.

## Output format

- `PASS` / `FAIL` table for each command.
- Failure summary with file/line references when available.
- Suggested next action, not a broad rewrite.
