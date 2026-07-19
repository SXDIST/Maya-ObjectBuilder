"""MayaObjectBuilder scripted plugin (pure Python).

Replaces the former C++ ``MayaObjectBuilder.mll``. Registers the ``Arma P3D`` file
translator and the eleven ``a3ob*`` commands, sources the MEL option box, and opens
the Python dock UI on load / hides it on unload.

Loadable exactly like the old ``.mll`` (``loadPlugin``, autoload, ``pluginInfo``); the
Maya module ``.mod`` puts this file on ``MAYA_PLUG_IN_PATH`` and the sibling ``scripts/``
on ``PYTHONPATH``.
"""

import inspect
import os
import sys

import maya.api.OpenMaya as om

maya_useNewAPI = True

VENDOR = "MayaObjectBuilder"
VERSION = "0.1.0"
REQUIRED_API_VERSION = "Any"

# Maya does not always define ``__file__`` for a loaded plugin module, so resolve this
# file's path through the code object instead (works under loadPlugin and mayapy).
try:
    _PLUGIN_FILE = __file__
except NameError:
    _PLUGIN_FILE = inspect.getsourcefile(lambda: 0)


def _scripts_dir():
    plugin_dir = os.path.dirname(os.path.abspath(_PLUGIN_FILE))
    return os.path.join(os.path.dirname(plugin_dir), "scripts")


def _ensure_scripts_on_path():
    """Make sure the sibling ``scripts/`` dir (holding the ``a3ob`` package and the
    UI module) is importable, whether loaded from the repo or an installed module."""
    scripts_dir = _scripts_dir()
    if os.path.isdir(scripts_dir) and scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


_ensure_scripts_on_path()

from a3ob.mayabridge import commands as a3ob_commands          # noqa: E402
from a3ob.mayabridge import model_cfg_commands as a3ob_cfg      # noqa: E402

_ALL_COMMANDS = a3ob_commands.COMMANDS + a3ob_cfg.COMMANDS

# The file translator lives in an API-1.0 companion plug-in (MPxFileTranslator is not
# in API 2.0). The main plug-in loads/unloads it so users deal with one plug-in.
_TRANSLATOR_PLUGIN = "MayaObjectBuilderTranslator"


def _source_option_script():
    """Source the MEL translator option box if it can be located next to scripts/."""
    mel_path = os.path.join(_scripts_dir(), "mayaObjectBuilderP3DOptions.mel")
    if os.path.isfile(mel_path):
        posix = mel_path.replace("\\", "/")
        try:
            om.MGlobal.sourceFile(posix)
        except Exception:
            pass


def _call_ui(function_name):
    try:
        import objectBuilderMenu
        getattr(objectBuilderMenu, function_name)()
    except Exception as error:  # noqa: BLE001 - UI is optional (e.g. under mayapy/standalone)
        om.MGlobal.displayWarning("MayaObjectBuilder UI %s skipped: %s" % (function_name, error))


def _load_translator_plugin():
    import maya.cmds as cmds
    try:
        if not cmds.pluginInfo(_TRANSLATOR_PLUGIN, query=True, loaded=True):
            path = os.path.join(os.path.dirname(os.path.abspath(_PLUGIN_FILE)), _TRANSLATOR_PLUGIN + ".py")
            cmds.loadPlugin(path if os.path.isfile(path) else _TRANSLATOR_PLUGIN)
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayWarning("MayaObjectBuilder translator load skipped: %s" % error)


def _unload_translator_plugin():
    import maya.cmds as cmds
    try:
        if cmds.pluginInfo(_TRANSLATOR_PLUGIN, query=True, loaded=True):
            cmds.unloadPlugin(_TRANSLATOR_PLUGIN)
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayWarning("MayaObjectBuilder translator unload skipped: %s" % error)


def _syntax_is_safe(command):
    """Build a command's MSyntax once here, where a failure is survivable.

    Maya calls the syntax creator lazily, on the command's FIRST dispatch, from a C++
    callback that cannot absorb a Python exception — so a bad flag (a reserved long name
    like "set" or "fix" makes MSyntax.addFlag raise) takes the whole session down and the
    user loses unsaved work. Calling it here turns that into a skipped command plus an
    error in the script editor."""
    try:
        command.syntax()
        return True
    except Exception as error:  # noqa: BLE001
        om.MGlobal.displayError(
            "MayaObjectBuilder: command %s not registered — its syntax() failed: %s"
            % (getattr(command, "kName", command), error))
        return False


def initializePlugin(plugin):
    fn = om.MFnPlugin(plugin, VENDOR, VERSION, REQUIRED_API_VERSION)

    _source_option_script()

    for command in _ALL_COMMANDS:
        if not _syntax_is_safe(command):
            continue
        fn.registerCommand(command.kName, command.creator, command.syntax)

    _load_translator_plugin()
    _call_ui("show_plugin_ui")
    om.MGlobal.displayInfo("MayaObjectBuilder loaded")


def uninitializePlugin(plugin):
    fn = om.MFnPlugin(plugin)

    _call_ui("hide_plugin_ui")
    _unload_translator_plugin()

    for command in reversed(_ALL_COMMANDS):
        try:
            fn.deregisterCommand(command.kName)
        except Exception as error:  # noqa: BLE001
            om.MGlobal.displayWarning("deregisterCommand %s: %s" % (command.kName, error))

    om.MGlobal.displayInfo("MayaObjectBuilder unloaded")
