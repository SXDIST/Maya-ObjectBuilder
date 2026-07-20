"""``Arma P3D`` translator logic (import/export bodies + option parsing).

Port of ``src/translators/P3DTranslator.cpp``. The actual ``MPxFileTranslator`` proxy
lives in the companion plug-in ``plug-ins/MayaObjectBuilderTranslator.py`` because
``MPxFileTranslator`` only exists in the Maya Python API 1.0, while the commands use
API 2.0 (the two cannot register from a single plug-in). That proxy is a thin shell
that calls :func:`do_read` / :func:`do_write` here; all real work stays in API 2.0.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from ..formats.p3d import MLOD
from .import_.importer import MayaMeshImport
from .export.exporter import MayaMeshExport, ExportOptions

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
    "autoLod=0", "autoLodOutput=quads", "autoLodReduction=aggressive", "autoLodFirst=LOD1",
    "autoLodResolution=1", "autoLodGeometry=1", "autoLodMemory=0", "autoLodFire=0",
    "autoLodView=0", "autoLodGeometryType=BOX", "autoLodFireQuality=2",
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


_AUTO_LOD_MENU_KEYS = {
    "autoLodOutput": "output",
    "autoLodReduction": "reduction",
    "autoLodFirst": "first_lod",
    "autoLodGeometryType": "geometry_type",
}
_AUTO_LOD_BOOL_KEYS = {
    "autoLodResolution": ("resolution", True),
    "autoLodGeometry": ("geometry", True),
    "autoLodMemory": ("memory", False),
    "autoLodFire": ("fire_geometry", False),
    "autoLodView": ("view_geometry", False),
}


def _auto_lod_settings(options):
    """Map the option string onto the dict autolod.helpers.settings documents."""
    settings = {}
    for key, name in _AUTO_LOD_MENU_KEYS.items():
        if key in options:
            settings[name] = options[key]
    for key, (name, fallback) in _AUTO_LOD_BOOL_KEYS.items():
        settings[name] = option_enabled(options, key, fallback)
    try:
        settings["fire_quality"] = int(options.get("autoLodFireQuality", 2))
    except (TypeError, ValueError):
        settings["fire_quality"] = 2
    return settings


def _selection_of(names):
    """Build an ``MSelectionList`` from generated node names for setActiveSelectionList."""
    selection = om.MSelectionList()
    for name in names:
        try:
            selection.add(name)
        except RuntimeError:
            pass
    return selection


def do_read(expanded_full_name, raw_name, options_string):
    """Import a P3D file. Raises on failure so the translator can report it."""
    options = parse_options(options_string)
    mlod = MLOD.read_file(expanded_full_name)
    if option_enabled(options, "firstLodOnly", False) and len(mlod.lods) > 1:
        mlod.lods = mlod.lods[:1]
    created = MayaMeshImport().import_mlod(mlod, raw_name)
    if option_enabled(options, "validateMeshes", False):
        om.MGlobal.executeCommand("a3obValidate")
    # Decode/assign .paa colour textures AFTER the import finishes — Maya's File > Import DG
    # context blocks creating and connecting the file texture node inline. The geometry is
    # already imported, so surface a scheduling failure loudly (mirror exporter.py) rather
    # than let the "Imported ... LOD count" info line print regardless.
    om.MGlobal.displayInfo("Imported P3D MLOD LOD count: %d" % len(created))
    try:
        cmds.evalDeferred("import a3ob.mayabridge.paatex as _pt; _pt.assign_pending_textures()", lowestPriority=True)
    except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
        om.MGlobal.displayError("P3D texture assignment scheduling failed: %s" % error)
        return False


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

    if not option_enabled(options, "autoLod", False):
        return MayaMeshExport().export_mlod(expanded_full_name, export_options)

    # Generated LODs are transient: they exist only long enough to be written. Undo is
    # suspended across the whole span so a Ctrl+Z after the export cannot resurrect nodes
    # that were deliberately removed, and cleanup runs in `finally` so a cancel or an
    # exception leaves the scene exactly as the user left it.
    from a3ob.mayabridge.autolod import generate_auto_lods
    from a3ob.mayabridge.undoctl import undo_suspended

    generated = []
    with undo_suspended():
        # generate_auto_lods() reuses a pre-existing "visuals"/"geometries"/"point_clouds"
        # group when one is already in the scene, and only self-cleans its OWN new group on
        # a mid-decimation cancel — a normal, successful run leaves those container groups
        # behind for the (usual) UI caller to keep. Export is not that caller: everything
        # generated here must be gone afterwards, container groups included. Snapshotting the
        # transforms before generation and diffing after lets cleanup remove exactly what
        # this call added — whether that is the full LOD stack or a group half-filled by an
        # exception partway through — without ever touching a group the user already had.
        before_transforms = set(cmds.ls(type="transform", long=True) or [])
        try:
            generated = generate_auto_lods(_auto_lod_settings(options)) or []
            if not generated:
                om.MGlobal.displayError(
                    "a3ob export: Auto LOD generated nothing — select exactly one source "
                    "mesh. No file was written.")
                return False
            om.MGlobal.setActiveSelectionList(_selection_of(generated),
                                              om.MGlobal.kReplaceList)
            return MayaMeshExport().export_mlod(expanded_full_name, export_options)
        finally:
            for node in generated:
                if cmds.objExists(node):
                    cmds.delete(node)
            leftover = set(cmds.ls(type="transform", long=True) or []) - before_transforms
            for node in leftover:
                if cmds.objExists(node):
                    cmds.delete(node)
