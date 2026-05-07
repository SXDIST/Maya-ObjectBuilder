# Contributing

Thanks for your interest in improving Maya ObjectBuilder.

## Scope

This repository focuses on the Maya 2027 plugin at the repository root. The bundled Blender add-on under `Arma3ObjectBuilder-master/` is kept as a compatibility reference unless a task explicitly targets it.

## Development setup

Configure and build from the repository root:

```bash
cmake -S . -B build -G "Visual Studio 18 2026" -A x64 -DMAYA_OBJECT_BUILDER_BUILD_TESTS=ON
cmake --build build --config Debug
```

## Verification before a pull request

For Maya plugin changes, run the relevant checks:

```bash
cmake --build build --config Debug
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

## Pull request guidelines

- Keep changes focused and explain the workflow impact.
- Preserve DayZ/Object Builder compatibility.
- Add or update regression coverage for importer/exporter behavior changes.
- Do not commit generated build artifacts, local fixtures, credentials, or private game assets.
