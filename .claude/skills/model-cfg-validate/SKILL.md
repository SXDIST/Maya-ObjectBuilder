---
name: model-cfg-validate
description: Validate and debug MayaObjectBuilder model.cfg parsing, writing, skeleton import/export, and Maya joint workflow tests.
---

# model-cfg-validate

Use this when the task mentions `model.cfg`, skeletons, bones, joints, import/export model config, or Russian requests like "проверь model.cfg", "импорт скелета", "экспорт скелета", "сломался cfg".

For non-trivial parser or skeleton workflow issues, prefer the `model-cfg-specialist` project subagent.

## First inspect

- `scripts/a3ob/formats/model_cfg.py`
- `scripts/a3ob/mayabridge/model_cfg_commands.py`
- `tests/mayapy/model_cfg_workflow.py`
- `tests/python/test_model_cfg.py`
- `plug-ins/MayaObjectBuilder.py` only if command registration is implicated.

## Core code paths

- `Config.read_file()`
- `Config.write_file()`
- `Config.skeletons()`
- `Config.skeleton_config()`
- `ImportModelCfgCommand.doIt()`
- `ExportModelCfgCommand.doIt()`
- Joint helpers such as `_selected_joint_or_null`, `_first_skeleton_root`, and `_collect_bones`.

## Commands (pure Python — no build step)

```bash
python tests/python/test_model_cfg.py
python -m py_compile scripts/a3ob/formats/model_cfg.py scripts/a3ob/mayabridge/model_cfg_commands.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Debug flow

1. Decide whether the failure is pure parser/writer or Maya command workflow.
2. For parser/writer failures, start with `model_cfg.py` and `tests/python/test_model_cfg.py`.
3. For Maya failures, start with `model_cfg_commands.py` and `tests/mayapy/model_cfg_workflow.py`.
4. Keep output stable unless the test explicitly expects a formatting change.
5. Re-run the model.cfg command sequence before reporting success.

## Output format

- Parse/write vs Maya command classification.
- Exact command that failed.
- Files/functions implicated.
- Minimal verification result.
