from pathlib import Path
import shutil
import sys
import traceback

import maya.cmds as cmds


PLUGIN_NAME = "MayaObjectBuilder"
PLUGIN_FILE = "MayaObjectBuilder.mll"
VERSION = "0.1.0"
REQUIRED_PACKAGE_FILES = [
    Path("plug-ins") / PLUGIN_FILE,
    Path("scripts") / "objectBuilderMenu.py",
    Path("scripts") / "objectBuilderAutoLOD.py",
    Path("scripts") / "mayaObjectBuilderP3DOptions.mel",
    Path("install") / "mayaObjectBuilderInstall.py",
    Path("install") / "install_maya.py",
    Path("README.md"),
    Path("LICENSE"),
]
RUNTIME_PACKAGE_DIRS = [Path("plug-ins"), Path("scripts")]


def _maya_documents_dir():
    maya_app_dir = cmds.internalVar(userAppDir=True)
    return Path(maya_app_dir).resolve()


def _package_root():
    installer_path = globals().get("INSTALLER_PATH") or globals().get("__file__")
    if not installer_path:
        raise RuntimeError("Set INSTALLER_PATH to this install_maya.py path before executing the installer")
    return Path(installer_path).resolve().parents[1]


def _install_root():
    return _maya_documents_dir() / PLUGIN_NAME


def _modules_dir():
    return _maya_documents_dir() / "modules"


def _copy_runtime_package(source, target):
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    for relative_dir in RUNTIME_PACKAGE_DIRS:
        shutil.copytree(source / relative_dir, target / relative_dir, ignore=ignore)


def _is_legacy_install_root(path):
    return (
        path.is_dir()
        and (path / "plug-ins" / PLUGIN_FILE).exists()
        and (path / "scripts" / "objectBuilderMenu.py").exists()
    )


def _cleanup_legacy_install_roots(target):
    for child in target.iterdir():
        if child.name in {"plug-ins", "scripts"}:
            continue
        if not _is_legacy_install_root(child):
            continue
        try:
            shutil.rmtree(child)
            print(f"Removed old versioned install folder: {child}")
        except Exception as error:
            print(f"Warning: could not remove old versioned install folder {child}: {error}")


def _module_text(root):
    module_root = root.as_posix()
    return "\n".join([
        f"+ {PLUGIN_NAME} {VERSION} {module_root}",
        "MAYA_PLUG_IN_PATH +:= plug-ins",
        "MAYA_SCRIPT_PATH +:= scripts",
        "PYTHONPATH +:= scripts",
        "",
    ])


def _write_module_file(root):
    modules_dir = _modules_dir()
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_file = modules_dir / f"{PLUGIN_NAME}.mod"
    module_file.write_text(_module_text(root), encoding="utf-8")
    return module_file


def _validate_package(source):
    missing = [path.as_posix() for path in REQUIRED_PACKAGE_FILES if not (source / path).exists()]
    if missing:
        raise RuntimeError("Release package is incomplete. Missing: " + ", ".join(missing))


def _unload_plugin():
    if not cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        return
    try:
        cmds.unloadPlugin(PLUGIN_NAME)
    except Exception as error:
        raise RuntimeError(
            f"Could not unload {PLUGIN_NAME}. Close busy scenes or restart Maya, then run the installer again. Maya reported: {error}"
        ) from error


def _load_plugin(plugin_path):
    try:
        cmds.loadPlugin(str(plugin_path))
        cmds.pluginInfo(PLUGIN_NAME, edit=True, autoload=True)
    except Exception as error:
        raise RuntimeError(f"Could not load installed plugin: {plugin_path}. Maya reported: {error}") from error


def install():
    source = _package_root()
    _validate_package(source)

    target = _install_root()
    _unload_plugin()
    _copy_runtime_package(source, target)
    module_file = _write_module_file(target)
    plugin_path = target / "plug-ins" / PLUGIN_FILE
    _load_plugin(plugin_path)
    _cleanup_legacy_install_roots(target)

    print(f"{PLUGIN_NAME} installed or updated at: {target}")
    print(f"Maya module file written to: {module_file}")
    print(f"{PLUGIN_NAME} loaded and enabled for autoload")
    return str(target)


def _run():
    print(f"Installing {PLUGIN_NAME} {VERSION}...")
    try:
        install()
    except Exception:
        print(f"{PLUGIN_NAME} installation failed.", file=sys.stderr)
        traceback.print_exc()
        raise
    print(f"{PLUGIN_NAME} installation complete. The menu and dock should now be available in Maya.")


def onMayaDroppedPythonFile(*_):
    _run()


if globals().get("__name__") in (None, "__main__"):
    _run()
