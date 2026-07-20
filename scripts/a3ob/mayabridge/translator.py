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
    "firstLodOnly=0", "importTextures=1", "enclose=1", "groupBy=type",
    "absolutePaths=1", "additionalData=1", "customNormals=1", "flags=1",
    "namedProperties=1", "vertexMass=1", "selections=1", "uvSets=1", "materials=1",
    "sections=preserve", "translateSelections=0", "cleanupSelections=0",
    "proxyAction=separate", "relativePaths=1", "selectedOnly=0", "visibleOnly=1",
    "applyModifiers=1", "applyTransforms=1", "sortSections=1",
    "generateComponents=1", "collisions=fail", "warningsAreErrors=1",
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


def _resolve_selected_lod_paths():
    """The LOD paths export itself would resolve the active selection to.

    Mirrors ``MayaMeshExport.export_mlod``'s own selected_only resolution — upward from a
    mesh/component to its LOD transform, or downward from a folder into the LODs it holds
    — so validation can be pointed at the exact set of LODs export is about to walk."""
    from a3ob.mayabridge.export.parse import resolve_lod_paths

    selection = om.MGlobal.getActiveSelectionList()
    resolved = []
    seen = set()
    for index in range(selection.length()):
        try:
            selected_path = selection.getDagPath(index)
        except Exception:  # noqa: BLE001 - a non-DAG selection item, nothing to resolve
            continue
        for lod_path in resolve_lod_paths(selected_path):
            full_path_name = lod_path.fullPathName()
            if full_path_name in seen:
                continue
            seen.add(full_path_name)
            resolved.append(lod_path)
    return resolved


def _select_lod_paths(paths):
    selection = om.MSelectionList()
    for path in paths:
        try:
            selection.add(path)
        except RuntimeError:
            pass
    om.MGlobal.setActiveSelectionList(selection, om.MGlobal.kReplaceList)


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
    if option_enabled(options, "importTextures", True):
        try:
            cmds.evalDeferred("import a3ob.mayabridge.paatex as _pt; _pt.assign_pending_textures()", lowestPriority=True)
        except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
            om.MGlobal.displayError("P3D texture assignment scheduling failed: %s" % error)
            return False


def _confirm_damage(damages):
    """Ask before writing a file that will quietly differ from the scene.

    Batch mode cannot show a dialog and nobody is there to answer one, so a scripted
    export reports and proceeds rather than hanging forever on a prompt."""
    if cmds.about(batch=True):
        for row in damages:
            om.MGlobal.displayWarning("a3ob export: %s" % row.split("|", 2)[-1])
        return True
    listing = "\n".join("  - " + row.split("|", 2)[-1] for row in damages[:10])
    if len(damages) > 10:
        listing += "\n  ... and %d more" % (len(damages) - 10)
    answer = cmds.confirmDialog(
        title="Export anyway?",
        message="This export will be written, but will differ from your scene:\n\n%s"
                % listing,
        button=["Export anyway", "Cancel"], defaultButton="Cancel",
        cancelButton="Cancel", dismissString="Cancel")
    return answer == "Export anyway"


def _validate_or_refuse(selection_only):
    """Run ``a3obValidate`` and decide whether the export may proceed.

    ``om.MGlobal.executeCommand`` does not hand back a command's string array, so the
    command is invoked through ``maya.cmds`` instead. Under mayapy an ``MPxCommand``
    result comes back as a list; interactive Maya can hand back a bare scalar for a
    single-element result, so both shapes are normalised here.

    Any ``error`` row refuses outright. Any ``damage`` row asks first (or, in batch mode,
    reports and proceeds — see ``_confirm_damage``). Otherwise the export is clear."""
    issues = cmds.a3obValidate(selectionOnly=selection_only)
    if issues is None:
        issues = []
    elif isinstance(issues, str):
        issues = [issues]
    errors = [row for row in issues if row.startswith("error|")]
    damages = [row for row in issues if row.startswith("damage|")]

    if errors:
        om.MGlobal.displayError(
            "a3ob export: %d validation error(s); no file written. First: %s"
            % (len(errors), errors[0].split("|", 2)[-1]))
        return False

    if damages and not _confirm_damage(damages):
        om.MGlobal.displayWarning("a3ob export: cancelled; no file written.")
        return False

    return True


def do_write(expanded_full_name, options_string, export_active):
    """Export a P3D file. Returns True on success, False on handled failure."""
    options = parse_options(options_string)
    export_options = ExportOptions()
    export_options.selected_only = export_active or option_enabled(options, "selectedOnly", False)
    export_options.visible_only = option_enabled(options, "visibleOnly", True)
    export_options.apply_transforms = option_enabled(options, "applyTransforms", True)
    export_options.apply_modifiers = option_enabled(options, "applyModifiers", True)
    export_options.generate_components = option_enabled(options, "generateComponents", False)

    if not option_enabled(options, "autoLod", False):
        # Validation is unconditional: it used to be gated on three checkboxes that all
        # defaulted to off, and the result was thrown away even when they were on, so
        # nothing could ever stop a bad file being written. This is the plain export path,
        # so what gets validated is exactly the user's own selection/scene — the thing they
        # can actually go fix.
        #
        # `a3obValidate -selectionOnly` only looks at what is DIRECTLY in the selection
        # list — it does not walk up from a mesh/component to its LOD, or down from a
        # folder into the LODs it holds, the way export itself does. Left alone, that means
        # every "select the mesh and Export Selected" or "select the folder holding a
        # model's LODs" workflow — both routine, both exercised by the existing test suite —
        # would validate an empty LOD list and refuse to export something export would
        # otherwise have written happily. Resolving the selection through the exporter's own
        # `resolve_lod_paths` first, and re-pointing the active selection at the result,
        # makes validation see the same universe of LODs the export is about to walk. The
        # original selection is restored afterwards so this is invisible to the user and to
        # anything reacting to selection changes (the dock's context refresh).
        original_selection = om.MGlobal.getActiveSelectionList() if export_options.selected_only else None
        if export_options.selected_only:
            resolved = _resolve_selected_lod_paths()
            if resolved:
                _select_lod_paths(resolved)
        try:
            if not _validate_or_refuse(export_options.selected_only):
                return False
            return MayaMeshExport().export_mlod(expanded_full_name, export_options)
        finally:
            if original_selection is not None:
                om.MGlobal.setActiveSelectionList(original_selection, om.MGlobal.kReplaceList)

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
            # Validation runs here, AFTER generation and on the generated stack, not before
            # it. Before generation the selection is the plain source mesh — it has no LOD
            # transforms at all, so validating it would always fail with "no LOD transforms
            # found" and Auto LOD export could never succeed. What actually gets written is
            # the generated stack, so that is what has to be correct; a problem found here is
            # still actionable — through the source mesh or the Auto LOD settings — even
            # though the specific generated node reported is deleted moments later.
            if not _validate_or_refuse(True):
                return False
            return MayaMeshExport().export_mlod(expanded_full_name, export_options)
        finally:
            for node in generated:
                if cmds.objExists(node):
                    cmds.delete(node)
            leftover = set(cmds.ls(type="transform", long=True) or []) - before_transforms
            for node in leftover:
                if cmds.objExists(node):
                    cmds.delete(node)
