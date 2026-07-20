"""Deleting a rig loses its weights, and validation says so (run with mayapy).

The old promise was that weights survived losing the skeleton, paid for with a second
copy of every weight in every scene. The promise now is narrower and honest: they do
not survive, and you are told the moment they are gone.

The lost-rig warning (Task 2) is scoped to "this LOD lost its rig while a sibling LOD
of the same model kept one" — a single-LOD scene that loses its only rig produces NO
warning, by design (see ``validate_lost_rig.py``: a Geometry LOD, or any static prop,
never has a skinCluster and must not be spammed on every validate). So the fixture here
needs two LODs sharing a parent group, each with its own rig, and only one rig gets
deleted — exactly the shape ``_model_has_skinned_sibling`` is built to catch.

Run:  mayapy.exe tests/mayapy/weights_survive_skeleton.py
"""

import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def _mark_lod(transform, resolution):
    for name, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                       ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=name, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", resolution)


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.file(new=True, force=True)

    # Two LODs of one model, sharing a parent group, each with its OWN skinCluster on
    # its OWN joint chain — so garment's rig can be deleted without touching sibling's.
    model = cmds.group(empty=True, name="model")

    transform = cmds.polyCylinder(name="garment", r=1, h=4, sx=8, sy=4, ch=False)[0]
    _mark_lod(transform, 0)
    cmds.parent(transform, model)

    sibling = cmds.polyCylinder(name="sibling", r=1, h=4, sx=4, sy=2, ch=False)[0]
    _mark_lod(sibling, 1)
    cmds.parent(sibling, model)

    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 2, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)

    cmds.select(clear=True)
    sibling_root = cmds.joint(position=(0, -2, 5), name="PelvisSibling")
    sibling_tip = cmds.joint(position=(0, 2, 5), name="SpineSibling")
    cmds.skinCluster(sibling_root, sibling_tip, sibling, toSelectedBones=True,
                     maximumInfluences=4)

    warned = [r for r in (cmds.a3obValidate() or [])
              if transform in r and "no skinCluster" in r]
    _harness.check(not warned, "a rigged mesh must not be warned about")

    cmds.delete(root)
    _harness.check(
        not cmds.ls(cmds.listHistory(transform, pruneDagObjects=True) or [],
                    type="skinCluster"),
        "deleting the skeleton must take the skinCluster with it")
    _harness.check(
        not cmds.attributeQuery("a3obBakedWeights", node=transform, exists=True),
        "no second copy should exist to fall back on")

    warned = [r for r in (cmds.a3obValidate() or [])
              if transform in r and "no skinCluster" in r]
    _harness.check(len(warned) == 1,
                   "losing the rig must be reported exactly once, got %r" % (warned,))

    sibling_warned = [r for r in (cmds.a3obValidate() or [])
                       if sibling in r and "no skinCluster" in r]
    _harness.check(not sibling_warned,
                   "the still-rigged sibling must not be warned about, got %r"
                   % (sibling_warned,))

    print("OK - weights go with the rig, and validation says so")

    # Preserved from the prior version of this file: skeleton_is_posed() regression
    # coverage. This has no other home in the suite (grep tests/ for "posetest" or
    # "skeleton_is_posed" — this is the only hit) and pins a real bug (bindPreMatrix
    # is a sparse multi indexed by LOGICAL .matrix[] indices that do not compact when
    # a middle influence is removed; see CLAUDE.md). Dropping it would have been a
    # silent coverage loss unrelated to the a3obBakedWeights removal this task is
    # otherwise about, so it stays.
    test_bind_pose_detection()
    return 0


def test_bind_pose_detection():
    """Exporting a posed rig bakes the pose into the model, so validation must catch it."""
    from a3ob.mayabridge.posetest import skeleton_is_posed

    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="posed", r=1, h=4, ch=False)[0]
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -2, 0), name="Root")
    tip = cmds.joint(position=(0, 2, 0), name="Tip")
    cmds.skinCluster(root, tip, mesh, toSelectedBones=True)

    _harness.check(skeleton_is_posed() == [], "a freshly bound rig must read as bind pose")

    cmds.setAttr(tip + ".rotateX", 45)
    posed = skeleton_is_posed()
    _harness.check(len(posed) == 1 and posed[0].endswith("Tip"),
          "the rotated joint must be reported, got %r" % (posed,))

    cmds.setAttr(tip + ".rotateX", 0)
    _harness.check(skeleton_is_posed() == [], "returning to bind pose must clear the warning")
    print("OK bind pose detection (posed rig reported, restored rig clean)")
    test_bind_pose_detection_after_middle_influence_removal()


def test_bind_pose_detection_after_middle_influence_removal():
    """Regression: bindPreMatrix is a SPARSE multi indexed by .matrix[] LOGICAL indices,
    which do NOT compact when an influence is removed. Removing a TRAILING influence never
    exposed the bug (the surviving indices stay dense from 0), so this removes a MIDDLE one:
    a 4-joint rig with B and C removed leaves influences=['A', 'D'] but the correct
    bindPreMatrix slots are [0, 3], not [0, 1]. skintransfer.finish_for_dayz() and
    a3obInfluence -ri both remove by name, not by trailing position, so this is the shape a
    real DayZ rig hits on every transfer."""
    from a3ob.mayabridge.posetest import skeleton_is_posed

    cmds.file(new=True, force=True)
    mesh = cmds.polyCylinder(name="middleRemoval", r=1, h=6, sx=8, sy=6, ch=False)[0]
    cmds.select(clear=True)
    a = cmds.joint(position=(0, -3, 0), name="A")
    b = cmds.joint(position=(0, -1, 0), name="B")
    c = cmds.joint(position=(0, 1, 0), name="C")
    d = cmds.joint(position=(0, 3, 0), name="D")
    skin = cmds.skinCluster(a, b, c, d, mesh, toSelectedBones=True, maximumInfluences=4)[0]

    cmds.skinCluster(skin, edit=True, removeInfluence=[b, c])
    _harness.check(cmds.skinCluster(skin, query=True, influence=True) == ["A", "D"],
          "expected A and D to survive the removal")

    posed = skeleton_is_posed()
    _harness.check(posed == [],
          "a rig that was never moved must read as bind pose after removing a middle "
          "influence, got %r (mis-indexed bindPreMatrix would report the survivors)" % (posed,))
    print("OK bind pose detection survives a middle-influence removal")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
