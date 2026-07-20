"""Maya DAG/mesh -> P3D MLOD conversion (OpenMaya 2.0).

Port of ``src/maya/MayaMeshExport.cpp``. Two passes: collect LOD transforms (+ sort
keys) then export and stream-write each LOD one at a time. N-gons are triangulated
through Maya so Object Builder (tri/quad only) can save them. Memory LODs with no mesh
are reconstructed from locators.

Coordinate convention: Maya (Y-up) -> P3D (Z-up) point ``(x, y, z) -> (x, -z, y)``;
vectors are normalized first.
"""

import os

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.formats import p3d
from a3ob.mayabridge.progress import Progress
from a3ob.formats.binary import BinaryWriter


from a3ob.mayabridge.export.parse import *  # noqa: F401,F403
from a3ob.mayabridge.export.taggs import *  # noqa: F401,F403

def _warn_about_missing_weights(lod_entries):
    """Say something when a rigged-looking scene is about to export without any weights.

    Deleting the skeleton deletes the skinCluster and every weight with it, and the export
    then wrote a perfectly valid file containing no bone selections at all — silently. The
    file only looks wrong once it is open in Object Builder, or worse, in game.

    Returns the LOD names that lack weights, so this stays testable without capturing log
    output (MGlobal cannot be monkey-patched)."""
    if not (cmds.ls(type="joint") or []):
        return []  # nothing rigged here; a static model is expected to have no weights

    unweighted = []
    for _sort_key, lod_path in lod_entries:
        mesh_path = _find_first_mesh_path(lod_path)
        if mesh_path is None:
            continue
        history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
        if cmds.ls(history, type="skinCluster"):
            continue
        unweighted.append(lod_path.partialPathName())

    if unweighted:
        om.MGlobal.displayWarning(
            "P3D export: %d LOD(s) have no skin weights (%s). The scene has a skeleton, so "
            "this is probably not intended — deleting joints removes the skinCluster and its "
            "weights with it."
            % (len(unweighted), ", ".join(unweighted[:4])))
    return unweighted


class ExportOptions:
    __slots__ = ("selected_only", "visible_only", "apply_transforms", "apply_modifiers", "generate_components")

    def __init__(self, selected_only=False, visible_only=True, apply_transforms=True, apply_modifiers=True, generate_components=False):
        self.selected_only = selected_only
        self.visible_only = visible_only
        self.apply_transforms = apply_transforms
        self.apply_modifiers = apply_modifiers
        self.generate_components = generate_components


class MayaMeshExport:
    def export_mlod(self, path, options=None):
        if options is None:
            options = ExportOptions()

        lod_entries = []  # (sort_key, MDagPath)

        if options.selected_only:
            selection = om.MGlobal.getActiveSelectionList()
            exported_paths = set()
            selected_names = selection.getSelectionStrings() if hasattr(selection, "getSelectionStrings") else []
            for selection_index in range(selection.length()):
                try:
                    selected_path = selection.getDagPath(selection_index)
                except Exception:
                    continue
                for lod_path in resolve_lod_paths(selected_path):
                    full_path_name = lod_path.fullPathName()
                    if full_path_name in exported_paths:
                        continue
                    exported_paths.add(full_path_name)
                    lod_entries.append((_lod_sort_key(lod_path), lod_path))
            if not lod_entries and selected_names:
                om.MGlobal.displayError("P3D export failed: selection does not contain an Object Builder LOD, LOD mesh, or mesh component: " + ", ".join(selected_names))
                return False
        else:
            it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
            while not it.isDone():
                # This walks every transform; only the ones marked A.IS_LOD become LOD paths,
                # so the pre-check variables are neutrally named.
                candidate_path = it.getPath()
                candidate_node = candidate_path.node()
                if attr.get_bool(candidate_node, A.IS_LOD):
                    lod_path = candidate_path
                    if not (options.visible_only and not lod_path.isVisible()):
                        lod_entries.append((_lod_sort_key(lod_path), om.MDagPath(lod_path)))
                it.next()

        if not lod_entries:
            om.MGlobal.displayError(
                "P3D export failed: select an Object Builder LOD or its mesh"
                if options.selected_only else
                "P3D export failed: no transforms with a3obIsLOD found")
            return False

        lod_entries.sort(key=lambda entry: entry[0])
        _warn_about_missing_weights(lod_entries)

        mlod = p3d.MLOD()
        # Progress + Esc, Maya's own mechanism. A heavy character is dozens of LODs and
        # hundreds of thousands of faces; without this Maya just looks frozen.
        interrupted = False
        # Walked once per export instead of once per LOD (30 LODs x 80 sets was 2400
        # DG round-trips). Reused as-is so DG order — which decides TAGG order — is preserved.
        object_builder_sets = _object_builder_set_objects()
        try:
            with Progress(len(lod_entries)) as progress, BinaryWriter(path) as writer:
                mlod.begin_write(writer, len(lod_entries))
                for lod_index, (_sort_key, lod_path) in enumerate(lod_entries):
                    if progress.cancelled():
                        interrupted = True
                        break
                    lod = _export_mesh_lod(lod_path, options, object_builder_sets)
                    mlod.write_lod(writer, lod)
                    progress.step(lod_index + 1)
        except Exception as error:  # noqa: BLE001 - mirror C++ catch-all
            om.MGlobal.displayError("P3D export failed: %s" % error)
            return False

        if interrupted:
            # The header already claims the full LOD count, so a half-written file is not a
            # valid P3D — remove it rather than leave something Object Builder will choke on.
            try:
                os.remove(path)
            except OSError:
                pass
            om.MGlobal.displayWarning("P3D export cancelled; %s was not written" % path)
            return False

        om.MGlobal.displayInfo("Exported P3D MLOD LOD count: %d" % len(lod_entries))
        return True


__all__ = [
    "ExportOptions",
    "MayaMeshExport",
]
