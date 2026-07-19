"""Keep the stored copy of skin weights current.

Weights live in the skinCluster, which Maya deletes together with the joints — so a
stored copy is what lets a model survive losing its rig. Baking by hand means
remembering to do it; syncing on scene save means the stored copy is simply always
current.

Scene save is the sync point on purpose. Doing it during export would make an
operation that looks read-only mutate the user's scene, while a save is already
expected to write.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds

from a3ob.mayabridge import attributes as attr
from a3ob.mayabridge.attributes import A
from a3ob.mayabridge import skinweights as sw

_callback_ids = []


def sync_all_lods():
    """Refresh a3obBakedWeights on every LOD that still has a live skinCluster.

    Returns how many LODs were updated. LODs without a skinCluster are left alone:
    their stored weights are the only copy left and must not be cleared."""
    from a3ob.mayabridge.commands.skin import read_skin

    updated = 0
    for lod in cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []:
        shapes = cmds.listRelatives(lod, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        if not shapes:
            continue
        selection = om.MSelectionList()
        selection.add(shapes[0])
        mesh_path = selection.getDagPath(0)
        skin = read_skin(mesh_path)
        if skin is None:
            continue
        skin_fn, weights, influence_count, _neighbours = skin
        names = [p.partialPathName().split("|")[-1].split(":")[-1]
                 for p in skin_fn.influenceObjects()]
        text = sw.bake_string(names, weights, influence_count)
        if not text:
            continue
        node = om.MSelectionList()
        node.add(lod)
        store_bake(node.getDependNode(0), text)
        updated += 1
    return updated


def store_bake(transform, text):
    """Write ``text`` as the LOD's baked weights, keeping the copy it replaces.

    Sync runs on every save from whatever skinCluster is live, which is right until the live
    one is a rig that was just re-bound: the fresh bind's defaults then overwrite a good bake
    and the only copy is gone. There is no reliable way to tell a deliberate re-bake from
    that accident — a fresh bind looks like any other rig — so instead of guessing, the
    previous value is always kept and ``a3obBakeSkin -restore -previous`` can reach it."""
    if not text:
        return False
    existing = attr.get_string(transform, A.BAKED_WEIGHTS) or ""
    if existing == text:
        return False
    if existing:
        attr.set_string(transform, A.BAKED_WEIGHTS_PREVIOUS, existing)
    attr.set_string(transform, A.BAKED_WEIGHTS, text)
    return True


def _on_before_save(*_args):
    try:
        sync_all_lods()
    except Exception:  # noqa: BLE001 - a sync failure must never block saving the scene
        pass


def install():
    """Sync before every scene save. Idempotent."""
    if _callback_ids:
        return
    _callback_ids.append(
        om.MSceneMessage.addCallback(om.MSceneMessage.kBeforeSave, _on_before_save))


def uninstall():
    """Remove the callback. MUST run on plugin unload — a surviving callback fires
    into freed Python objects and takes Maya down."""
    while _callback_ids:
        try:
            om.MMessage.removeCallback(_callback_ids.pop())
        except Exception:  # noqa: BLE001 - already gone, or Maya is tearing down
            pass


__all__ = ["sync_all_lods", "install", "uninstall"]
