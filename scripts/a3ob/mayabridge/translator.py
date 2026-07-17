"""``Arma P3D`` translator logic (import/export bodies + option parsing).

Port of ``src/translators/P3DTranslator.cpp``. The actual ``MPxFileTranslator`` proxy
lives in the companion plug-in ``plug-ins/MayaObjectBuilderTranslator.py`` because
``MPxFileTranslator`` only exists in the Maya Python API 1.0, while the commands use
API 2.0 (the two cannot register from a single plug-in). That proxy is a thin shell
that calls :func:`do_read` / :func:`do_write` here; all real work stays in API 2.0.
"""

import maya.api.OpenMaya as om

from ..formats.p3d import MLOD
from .mesh_import import MayaMeshImport
from .mesh_export import MayaMeshExport, ExportOptions

TRANSLATOR_NAME = "Arma P3D"
OPTION_SCRIPT = "mayaObjectBuilderP3DOptions"

# Mirrors the former C++ kP3DDefaultOptions. Only a handful are consulted here; the
# rest are UI-facing defaults for the MEL option box.
DEFAULT_OPTIONS = ";".join([
    "firstLodOnly=0", "validateMeshes=0", "enclose=1", "groupBy=type",
    "absolutePaths=1", "additionalData=1", "customNormals=1", "flags=1",
    "namedProperties=1", "vertexMass=1", "selections=1", "uvSets=1", "materials=1",
    "sections=preserve", "translateSelections=0", "cleanupSelections=0",
    "proxyAction=separate", "relativePaths=1", "selectedOnly=0", "visibleOnly=1",
    "exportValidateMeshes=0", "applyModifiers=1", "applyTransforms=1", "sortSections=1",
    "generateComponents=1", "collisions=fail", "validateLods=0", "warningsAreErrors=1",
    "renumberComponents=0", "forceLowercase=1", "exportTranslateSelections=0",
])


def parse_options(options_string):
    options = {}
    for entry in options_string.split(";"):
        pair = entry.split("=")
        if len(pair) == 2:
            options[pair[0]] = pair[1]
    return options


def option_enabled(options, key, fallback):
    value = options.get(key)
    if value is None:
        return fallback
    return value == "1" or value == "true"


def do_read(expanded_full_name, raw_name, options_string):
    """Import a P3D file. Raises on failure so the translator can report it."""
    options = parse_options(options_string)
    mlod = MLOD.read_file(expanded_full_name)
    if option_enabled(options, "firstLodOnly", False) and len(mlod.lods) > 1:
        mlod.lods = mlod.lods[:1]
    created = MayaMeshImport().import_mlod(mlod, raw_name)
    if option_enabled(options, "validateMeshes", False):
        om.MGlobal.executeCommand("a3obValidate")
    om.MGlobal.displayInfo("Imported P3D MLOD LOD count: %d" % len(created))


def do_write(expanded_full_name, options_string, export_active):
    """Export a P3D file. Returns True on success, False on handled failure."""
    options = parse_options(options_string)
    export_options = ExportOptions()
    export_options.selected_only = export_active or option_enabled(options, "selectedOnly", False)
    export_options.visible_only = option_enabled(options, "visibleOnly", True)
    export_options.apply_transforms = option_enabled(options, "applyTransforms", True)
    export_options.apply_modifiers = option_enabled(options, "applyModifiers", True)
    export_options.generate_components = option_enabled(options, "generateComponents", False)

    if (option_enabled(options, "validateMeshes", False)
            or option_enabled(options, "exportValidateMeshes", False)
            or option_enabled(options, "validateLods", False)):
        command = "a3obValidate -selectionOnly" if export_options.selected_only else "a3obValidate"
        om.MGlobal.executeCommand(command)

    return MayaMeshExport().export_mlod(expanded_full_name, export_options)
