---
name: model-cfg-validate
description: Validate and debug MayaObjectBuilder model.cfg parsing, writing, skeleton import/export, and Maya joint workflow tests.
---

# model-cfg-validate

Use this when the task mentions `model.cfg`, skeletons, bones, joints, import/export model config, or Russian requests like "проверь model.cfg", "импорт скелета", "экспорт скелета", "сломался cfg".

For non-trivial parser or skeleton workflow issues, prefer the `model-cfg-specialist` project subagent.

## First inspect

- `src/formats/ModelCfg.cpp`
- `src/formats/ModelCfg.h`
- `src/commands/ModelCfgCommands.cpp`
- `src/commands/ModelCfgCommands.h`
- `tests/mayapy/model_cfg_workflow.py`
- `src/PluginMain.cpp` only if command registration is implicated.

## Core code paths

- `a3ob::cfg::Config::readFile()`
- `a3ob::cfg::Config::writeFile()`
- `a3ob::cfg::Config::skeletons()`
- `a3ob::cfg::Config::skeletonConfig()`
- `ImportModelCfgCommand::doIt()`
- `ExportModelCfgCommand::doIt()`
- Joint helpers such as `selectedJointOrNull`, `firstSkeletonRoot`, and `collectBones`.

## Commands

```bash
cmake --build build --config Debug
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Debug flow

1. Decide whether the failure is pure parser/writer or Maya command workflow.
2. For parser/writer failures, start with `ModelCfg.cpp` and the C++ test.
3. For Maya failures, start with `ModelCfgCommands.cpp` and `tests/mayapy/model_cfg_workflow.py`.
4. Keep output stable unless the test explicitly expects a formatting change.
5. Re-run the model.cfg command sequence before reporting success.

## Output format

- Parse/write vs Maya command classification.
- Exact command that failed.
- Files/functions implicated.
- Minimal verification result.
