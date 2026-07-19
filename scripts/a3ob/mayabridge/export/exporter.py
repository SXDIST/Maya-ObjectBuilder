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
    import maya.cmds as cmds
    if not (cmds.ls(type="joint") or []):
        return []  # nothing rigged here; a static model is expected to have no weights

    unweighted = []
    for _sort_key, dag_path in lod_entries:
        mesh_path = _find_first_mesh_path(dag_path)
        if mesh_path is None:
            continue
        history = cmds.listHistory(mesh_path.fullPathName(), pruneDagObjects=True) or []
        if cmds.ls(history, type="skinCluster"):
            continue
        if attr.get_string(dag_path.node(), A.BAKED_WEIGHTS):
            continue
        unweighted.append(dag_path.partialPathName())

    if unweighted:
        om.MGlobal.displayWarning(
            "P3D export: %d LOD(s) have no skin weights and none baked (%s). The scene has a "
            "skeleton, so this is probably not intended — deleting joints removes the "
            "skinCluster and its weights. Use a3obBakeSkin BEFORE deleting a rig."
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
            for i in range(selection.length()):
                try:
                    selected_path = selection.getDagPath(i)
                except Exception:
                    continue
                lod_path = _resolve_lod_path(selected_path)
                if lod_path is None:
                    continue
                full_path = lod_path.fullPathName()
                if full_path in exported_paths:
                    continue
                exported_paths.add(full_path)
                lod_entries.append((_lod_sort_key(lod_path), lod_path))
            if not lod_entries and selected_names:
                om.MGlobal.displayError("P3D export failed: selection does not contain an Object Builder LOD, LOD mesh, or mesh component: " + ", ".join(selected_names))
                return False
        else:
            it = om.MItDag(om.MItDag.kDepthFirst, om.MFn.kTransform)
            while not it.isDone():
                transform_path = it.getPath()
                node = transform_path.node()
                if attr.get_bool(node, A.IS_LOD):
                    if not (options.visible_only and not transform_path.isVisible()):
                        lod_entries.append((_lod_sort_key(transform_path), om.MDagPath(transform_path)))
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
        try:
            with Progress(len(lod_entries)) as progress, BinaryWriter(path) as writer:
                mlod.begin_write(writer, len(lod_entries))
                for index, (_sort_key, dag_path) in enumerate(lod_entries):
                    if progress.cancelled():
                        interrupted = True
                        break
                    lod = _export_mesh_lod(dag_path, options)
                    mlod.write_lod(writer, lod)
                    progress.step(index + 1)
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
