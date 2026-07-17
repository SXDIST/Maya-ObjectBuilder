"""Companion ``Arma P3D`` file translator plug-in (Maya Python API 1.0).

``MPxFileTranslator`` exists only in API 1.0, whereas the main ``MayaObjectBuilder``
plug-in registers its commands through API 2.0 (the two cannot be registered from a
single plug-in). This tiny API-1.0 shell registers the translator and delegates all
real work to :mod:`a3ob.mayabridge.translator`, which is pure API 2.0.

The main plug-in loads and unloads this companion automatically, so users still deal
with a single "MayaObjectBuilder" plug-in.
"""

import inspect
import os
import sys

import maya.OpenMaya as om
import maya.OpenMayaMPx as ompx

try:
    _PLUGIN_FILE = __file__
except NameError:
    _PLUGIN_FILE = inspect.getsourcefile(lambda: 0)


def _ensure_scripts_on_path():
    plugin_dir = os.path.dirname(os.path.abspath(_PLUGIN_FILE))
    scripts_dir = os.path.join(os.path.dirname(plugin_dir), "scripts")
    if os.path.isdir(scripts_dir) and scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)


_ensure_scripts_on_path()

from a3ob.mayabridge import translator as t  # noqa: E402


class P3DTranslator(ompx.MPxFileTranslator):
    def __init__(self):
        ompx.MPxFileTranslator.__init__(self)

    def haveReadMethod(self):
        return True

    def haveWriteMethod(self):
        return True

    def haveReferenceMethod(self):
        return False

    def haveNamespaceSupport(self):
        return True

    def canBeOpened(self):
        # P3D is an import/export interchange format, not a Maya scene: never let a .p3d
        # become the open scene file. Otherwise File > Open (or opening a recent .p3d)
        # makes it the current file, and Ctrl+S then re-writes the .p3d through this
        # translator — silently corrupting a model that Object Builder can no longer open.
        return False

    def defaultExtension(self):
        return "p3d"

    def filter(self):
        return "*.p3d"

    def identifyFile(self, file_object, buffer, size):
        if size >= 4 and buffer[:4] == "MLOD":
            return ompx.MPxFileTranslator.kIsMyFileType
        name = file_object.name()
        if name.lower().endswith(".p3d"):
            return ompx.MPxFileTranslator.kCouldBeMyFileType
        return ompx.MPxFileTranslator.kNotMyFileType

    def reader(self, file_object, options_string, access_mode):
        try:
            t.do_read(file_object.expandedFullName(), file_object.name(), options_string)
        except Exception as error:  # noqa: BLE001
            om.MGlobal.displayError("P3D import failed: %s" % error)
            raise

    def writer(self, file_object, options_string, access_mode):
        export_active = access_mode == ompx.MPxFileTranslator.kExportActiveAccessMode
        if not t.do_write(file_object.expandedFullName(), options_string, export_active):
            raise RuntimeError("P3D export failed")


def _creator():
    return ompx.asMPxPtr(P3DTranslator())


def initializePlugin(mobject):
    plugin = ompx.MFnPlugin(mobject, "MayaObjectBuilder", "0.1.0", "Any")
    plugin.registerFileTranslator(
        t.TRANSLATOR_NAME,
        None,
        _creator,
        t.OPTION_SCRIPT,
        t.DEFAULT_OPTIONS,
        False,
    )


def uninitializePlugin(mobject):
    plugin = ompx.MFnPlugin(mobject)
    plugin.deregisterFileTranslator(t.TRANSLATOR_NAME)
