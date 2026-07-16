"""Local development install: register this repo as a Maya module (edit-in-place).

Writes ``Documents/maya/modules/MayaObjectBuilder.mod`` pointing straight at this
repository, so Maya loads ``plug-ins/`` and ``scripts/`` from here with no copying.
Edit the Python in the repo, reload the plugin, and Maya picks it up.

Run inside Maya (or mayapy) — e.g. from the Script Editor::

    import dev_install; dev_install.install()

or in this session's shell with the ``!`` prefix::

    ! "/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0, r'<repo>/scripts'); import dev_install; dev_install.install(load=False)"
"""

from pathlib import Path

import maya.cmds as cmds

PLUGIN_NAME = "MayaObjectBuilder"
VERSION = "0.1.0"


def _repo_root():
    return Path(__file__).resolve().parents[1]


def _modules_dir():
    return Path(cmds.internalVar(userAppDir=True)).resolve() / "modules"


def _module_text(root):
    return "\n".join([
        "+ %s %s %s" % (PLUGIN_NAME, VERSION, root.as_posix()),
        "MAYA_PLUG_IN_PATH +:= plug-ins",
        "MAYA_SCRIPT_PATH +:= scripts",
        "PYTHONPATH +:= scripts",
        "",
    ])


def install(load=True):
    root = _repo_root()
    modules_dir = _modules_dir()
    modules_dir.mkdir(parents=True, exist_ok=True)
    module_file = modules_dir / (PLUGIN_NAME + ".mod")
    module_file.write_text(_module_text(root), encoding="utf-8")
    print("MayaObjectBuilder dev module written: %s" % module_file)
    print("  -> %s" % root)

    if load:
        plugin_path = root / "plug-ins" / (PLUGIN_NAME + ".py")
        if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
            cmds.unloadPlugin(PLUGIN_NAME)
        cmds.loadPlugin(str(plugin_path))
        cmds.pluginInfo(PLUGIN_NAME, edit=True, autoload=True)
        print("MayaObjectBuilder loaded from repo and set to autoload")
    return module_file


def uninstall():
    module_file = _modules_dir() / (PLUGIN_NAME + ".mod")
    if cmds.pluginInfo(PLUGIN_NAME, query=True, loaded=True):
        cmds.unloadPlugin(PLUGIN_NAME)
    if module_file.exists():
        module_file.unlink()
        print("Removed %s" % module_file)


if __name__ == "__main__":
    install(load=False)
