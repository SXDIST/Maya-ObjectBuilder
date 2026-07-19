# Contributing

Thanks for your interest in improving Maya ObjectBuilder.

## Scope

This repository focuses on the pure-Python Maya 2027 plugin at the repository root. The bundled Blender add-on under `Arma3ObjectBuilder-master/` is kept as a compatibility reference unless a task explicitly targets it.

## Development setup

There is no build step. Register the repository as an edit-in-place Maya module and work directly from it. Inside Maya or `mayapy`:

```python
import sys; sys.path.insert(0, r"<path to this repo>/tools")
import dev_install
dev_install.install()
```

Edit the Python under `plug-ins/` and `scripts/`, reload the plugin in Maya, and your changes take effect. See `README.md` for the headless variant and `tools/launch_maya_debug.ps1` for launching Maya with the dev module.

## Verification before a pull request

Run the full validation checklist from the repository root:

```bash
# Pure-Python format tests (no Maya)
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py

# Python syntax check
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py tools/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py

# Maya integration workflows
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```

For a single targeted check, run only the matching `mayapy` workflow or format test.

## Pull request guidelines

- Keep changes focused and explain the workflow impact.
- Preserve DayZ/Object Builder compatibility — the `a3ob*` command names, their flags, and the on-scene `a3ob*` attribute schema are a contract that existing `.ma`/`.p3d` scenes depend on.
- Add or update regression coverage for importer/exporter behavior changes.
- Do not commit generated artifacts (`dist/`, `build/`, `__pycache__/`), local fixtures, credentials, or private game assets.
