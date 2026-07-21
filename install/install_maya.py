from pathlib import Path
import shutil
import sys
import traceback

import maya.cmds as cmds


PLUGIN_NAME = "MayaObjectBuilder"
PLUGIN_FILE = "MayaObjectBuilder.py"
TRANSLATOR_PLUGIN_FILE = "MayaObjectBuilderTranslator.py"
VERSION = "0.1.0"
REQUIRED_PACKAGE_FILES = [
    Path("plug-ins") / PLUGIN_FILE,
    Path("plug-ins") / TRANSLATOR_PLUGIN_FILE,
    Path("scripts") / "objectBuilderMenu.py",
    Path("scripts") / "objectBuilderAutoLOD.py",
    Path("scripts") / "mayaObjectBuilderP3DOptions.mel",
    Path("scripts") / "a3ob" / "__init__.py",
    Path("scripts") / "a3ob" / "formats" / "p3d.py",
    Path("scripts") / "a3ob" / "mayabridge" / "commands" / "__init__.py",
    Path("scripts") / "a3ob" / "mayabridge" / "import_" / "__init__.py",
    Path("scripts") / "a3ob" / "mayabridge" / "export" / "__init__.py",
    Path("scripts") / "a3ob" / "ui" / "constants.py",
    Path("scripts") / "a3ob" / "ui" / "scene" / "__init__.py",
    Path("scripts") / "a3ob" / "mayabridge" / "autolod" / "__init__.py",
    Path("scripts") / "a3ob" / "ui" / "dock.py",
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
    # NOTE: tools/dev_install.py has its own _modules_dir/_module_text writing the same .mod
    # format. Keep both. This file is dragged into Maya and run standalone, so it may import
    # only the stdlib and maya.cmds — importing a shared helper out of the repo would break
    # the one thing it is for. Change the .mod format and you must edit BOTH.
    return _maya_documents_dir() / "modules"


def _copy_runtime_package(source, target):
    # Remove only the directories this package OWNS. `target` is
    # <userAppDir>/MayaObjectBuilder, which also holds references/ (the user's saved reference
    # assets) and whatever else they keep there — an rmtree of the whole root deleted those on
    # every upgrade. The per-directory removal keeps the reason the rmtree existed: a file a
    # previous version shipped and this one dropped must not survive as an orphan.
    target.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    for relative_dir in RUNTIME_PACKAGE_DIRS:
        destination = target / relative_dir
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source / relative_dir, destination, ignore=ignore)


# kind -> (optionVar, file stem). DUPLICATED from a3ob.mayabridge.references.KINDS on purpose:
# this file is dragged into Maya and run standalone, so it may import only the stdlib and
# maya.cmds. Change KINDS and you must edit this too.
REFERENCE_ASSETS = [
    ("MayaObjectBuilder_ref_male_body", "dayz_male_body"),
    ("MayaObjectBuilder_ref_female_body", "dayz_female_body"),
    ("MayaObjectBuilder_ref_skeleton", "dayz_skeleton"),
]


def _seed_reference_assets(source):
    """Copy shipped reference assets into the user's Maya folder and point the optionVars there.

    Never overwrites: a user who customised their body must not lose it to an upgrade, and a
    user whose optionVar points somewhere else entirely must keep pointing there. An absent
    assets/ directory is a normal state (a git clone, or a build with the assets pruned) and
    must not fail the install."""
    shipped = source / "assets" / "references"
    if not shipped.is_dir():
        return []
    destination_dir = _maya_documents_dir() / PLUGIN_NAME / "references"
    destination_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for option_var, stem in REFERENCE_ASSETS:
        asset = shipped / f"{stem}.ma"
        if not asset.is_file():
            continue
        destination = destination_dir / asset.name
        if not destination.exists():
            shutil.copy2(asset, destination)
            written.append(destination)
        existing = cmds.optionVar(query=option_var) if cmds.optionVar(exists=option_var) else ""
        if not existing or not Path(existing).is_file():
            cmds.optionVar(stringValue=(option_var, destination.as_posix()))
    return written


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
    seeded = _seed_reference_assets(source)
    if seeded:
        print(f"Reference assets installed: {', '.join(p.name for p in seeded)}")
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
