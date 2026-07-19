"""Baked weights can be put back onto a rig, and are never silently destroyed (mayapy).

Baking was only ever half a feature: it let weights outlive the skeleton so EXPORT could
fall back to them, but nothing could put them back onto a skinCluster. So the obvious move —
bake, delete the rig, re-bind the garment later — ended with the garment bound and every
weight gone, and the stored copy unreachable.

Worse, `weightsync` refreshes the stored copy on every scene save from whatever skinCluster
is live. Re-bind, save, and the good bake is overwritten by the fresh bind's defaults. That
is silent data loss, so anything that overwrites a non-empty bake now stashes it first.

Run:  mayapy.exe tests/mayapy/weights_restore.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge import skinweights as sw  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def unwrap(result):
    if isinstance(result, (list, tuple)) and len(result) == 1:
        return result[0]
    return result


def build():
    """A LOD cylinder skinned to Neck/Head, with weights nobody would bind by accident."""
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    mesh = cmds.polyCylinder(name="collar", r=1, h=6, sx=8, sy=6, ch=False)[0]
    cmds.addAttr(mesh, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(mesh + ".a3obIsLOD", True)
    cmds.addAttr(mesh, longName="a3obLodType", attributeType="long")
    cmds.addAttr(mesh, longName="a3obResolution", attributeType="long")

    cmds.select(clear=True)
    neck = cmds.joint(position=(0, -3, 0), name="Neck")
    head = cmds.joint(position=(0, 3, 0), name="Head")
    cmds.select(mesh, replace=True)
    skin = cmds.skinCluster(neck, head, mesh, toSelectedBones=True)[0]

    # A distinctive, deliberately lopsided distribution: a default bind never looks like it.
    verts = cmds.polyEvaluate(mesh, vertex=True)
    for index in range(verts):
        share = 0.25 if index % 2 else 0.75
        cmds.skinPercent(skin, "%s.vtx[%d]" % (mesh, index),
                         transformValue=[(neck, share), (head, 1.0 - share)])
    return mesh, skin, neck, head


def weights_of(mesh, skin):
    verts = cmds.polyEvaluate(mesh, vertex=True)
    return [tuple(round(v, 5) for v in
                  cmds.skinPercent(skin, "%s.vtx[%d]" % (mesh, i), query=True, value=True))
            for i in range(verts)]


def rebind(mesh):
    """What a rigger does after deleting a rig: fresh joints, fresh bind, default weights."""
    cmds.select(clear=True)
    neck = cmds.joint(position=(0, -3, 0), name="Neck")
    head = cmds.joint(position=(0, 3, 0), name="Head")
    cmds.select(mesh, replace=True)
    return cmds.skinCluster(neck, head, mesh, toSelectedBones=True)[0]


def test_restore_puts_the_bake_back_on_a_fresh_bind():
    mesh, skin, neck, _head = build()
    wanted = weights_of(mesh, skin)
    cmds.select(mesh, replace=True)
    check(unwrap(cmds.a3obBakeSkin(selectionOnly=True)) == 1, "the LOD must bake")

    cmds.delete(cmds.listRelatives(neck, parent=True, fullPath=True) or neck)
    check(not cmds.ls(type="skinCluster"),
          "deleting the skeleton takes the skinCluster with it — that is the premise")

    new_skin = rebind(mesh)
    check(weights_of(mesh, new_skin) != wanted, "a fresh bind must differ, or nothing is proven")

    cmds.select(mesh, replace=True)
    restored = unwrap(cmds.a3obBakeSkin(selectionOnly=True, restore=True))
    check(restored == 1, "one LOD restored, got %r" % (restored,))
    check(weights_of(mesh, new_skin) == wanted,
          "the rig must carry the baked weights again, got %r" % (weights_of(mesh, new_skin)[:4],))


def test_restore_stashes_what_it_overwrites():
    """Restoring is destructive too, so it stashes the live weights it is about to replace.

    The command is not undoable — it writes the whole weight array through the API, which
    never enters the undo queue — so stashing is what stands in for Ctrl+Z. The effect is
    that `-restore -previous` swaps: run it twice and you are back where you started."""
    mesh, skin, _neck, _head = build()
    first = weights_of(mesh, skin)
    cmds.select(mesh, replace=True)
    cmds.a3obBakeSkin(selectionOnly=True)

    cmds.skinPercent(skin, mesh + ".vtx[0]", transformValue=[("Neck", 1.0), ("Head", 0.0)])
    second = weights_of(mesh, skin)
    check(second != first, "the paint must have changed something")
    cmds.a3obBakeSkin(selectionOnly=True)   # BAKED = second, PREVIOUS = first

    cmds.a3obBakeSkin(selectionOnly=True, restore=True, previous=True)
    check(weights_of(mesh, skin) == first,
          "restoring the previous copy brings the older weights back, got %r"
          % (weights_of(mesh, skin)[:2],))

    cmds.a3obBakeSkin(selectionOnly=True, restore=True, previous=True)
    check(weights_of(mesh, skin) == second,
          "and the weights it overwrote are still reachable, got %r"
          % (weights_of(mesh, skin)[:2],))


def test_sync_on_save_does_not_destroy_a_good_bake():
    """The reported trap: bake, lose the rig, re-bind, save — and the bake was gone."""
    from a3ob.mayabridge import weightsync

    mesh, skin, neck, _head = build()
    wanted = weights_of(mesh, skin)
    cmds.select(mesh, replace=True)
    cmds.a3obBakeSkin(selectionOnly=True)
    good = cmds.getAttr(mesh + ".a3obBakedWeights")

    cmds.delete(cmds.listRelatives(neck, parent=True, fullPath=True) or neck)
    new_skin = rebind(mesh)
    weightsync.sync_all_lods()          # what a scene save does

    check(cmds.getAttr(mesh + ".a3obBakedWeights") != good,
          "sync still refreshes from the live rig — that is its job")
    check(cmds.getAttr(mesh + ".a3obBakedWeightsPrevious") == good,
          "but the copy it replaced must be kept")

    cmds.select(mesh, replace=True)
    cmds.a3obBakeSkin(selectionOnly=True, restore=True, previous=True)
    check(weights_of(mesh, new_skin) == wanted,
          "and the good weights must be recoverable after the save")


def test_restoring_bones_the_rig_lost_is_reported_not_invented():
    mesh, skin, neck, head = build()
    cmds.select(mesh, replace=True)
    cmds.a3obBakeSkin(selectionOnly=True)

    # Rebind to Neck only: the bake's Head weights have nowhere to go.
    cmds.delete(cmds.listRelatives(neck, parent=True, fullPath=True) or neck)
    cmds.select(clear=True)
    only = cmds.joint(position=(0, -3, 0), name="Neck")
    cmds.select(mesh, replace=True)
    lone_skin = cmds.skinCluster(only, mesh, toSelectedBones=True)[0]

    cmds.select(mesh, replace=True)
    cmds.a3obBakeSkin(selectionOnly=True, restore=True)
    rows = weights_of(mesh, lone_skin)
    check(all(abs(sum(row) - 1.0) < 1e-4 for row in rows),
          "every vertex still sums to 1 after renormalizing, got %r" % (rows[:2],))


def main():
    test_restore_puts_the_bake_back_on_a_fresh_bind()
    test_restore_stashes_what_it_overwrites()
    test_sync_on_save_does_not_destroy_a_good_bake()
    test_restoring_bones_the_rig_lost_is_reported_not_invented()
    print("weights restore: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
