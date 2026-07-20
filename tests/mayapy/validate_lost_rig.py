"""a3obValidate warns when a mesh carries bone selections but has no rig (run with mayapy).

This is the safety net that replaces a3obBakedWeights: instead of silently carrying a
second copy forever, say so the moment a rig goes missing.

The warning is scoped to "this LOD lost its rig while a sibling LOD of the same model
kept one" rather than "this LOD has no skinCluster", because a Geometry LOD (and any
purely static model) never has a skinCluster in the first place and must not be spammed
on every validate. "Same model" is resolved the way export itself groups LODs: the
folder directly holding a LOD, walked downward for every LOD under it (see
``export.parse.resolve_lod_paths``) — so the fixture below needs two LODs sharing a
parent group, each with its OWN rig, so one can lose its skinCluster while the other
stays skinned throughout.

Run:  mayapy.exe tests/mayapy/validate_lost_rig.py
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


def build_two_lod_model():
    """One model, two Resolution LODs sharing a parent group (the "model" folder export
    would resolve to if selected), each with its OWN skinCluster on its OWN joint chain —
    so one rig can be deleted without touching the other."""
    cmds.file(new=True, force=True)
    model = cmds.group(empty=True, name="model")

    lod_hi = cmds.polyCylinder(name="garment_hi", r=1, h=4, sx=8, sy=4, ch=False)[0]
    _mark_lod(lod_hi, 0)
    cmds.parent(lod_hi, model)

    lod_lo = cmds.polyCylinder(name="garment_lo", r=1, h=4, sx=4, sy=2, ch=False)[0]
    _mark_lod(lod_lo, 1)
    cmds.parent(lod_lo, model)

    cmds.select(clear=True)
    root_hi = cmds.joint(position=(0, -2, 0), name="PelvisHi")
    tip_hi = cmds.joint(position=(0, 2, 0), name="SpineHi")
    cmds.skinCluster(root_hi, tip_hi, lod_hi, toSelectedBones=True, maximumInfluences=4)

    cmds.select(clear=True)
    root_lo = cmds.joint(position=(0, -2, 5), name="PelvisLo")
    tip_lo = cmds.joint(position=(0, 2, 5), name="SpineLo")
    cmds.skinCluster(root_lo, tip_lo, lod_lo, toSelectedBones=True, maximumInfluences=4)

    return lod_hi, lod_lo, root_lo


def rows_for(node):
    return [r for r in (cmds.a3obValidate() or []) if node in r]


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    lod_hi, lod_lo, root_lo = build_two_lod_model()

    # Both LODs are still rigged: neither is warned about.
    lost_hi = [r for r in rows_for(lod_hi) if "no skinCluster" in r]
    lost_lo = [r for r in rows_for(lod_lo) if "no skinCluster" in r]
    _harness.check(not lost_hi and not lost_lo,
                   "rigged meshes must not be warned about, got hi=%r lo=%r" % (lost_hi, lost_lo))

    # Delete only lod_lo's rig. lod_hi (its sibling in the same model) is still skinned,
    # so lod_lo losing its cluster must be reported.
    cmds.delete(root_lo)

    lost_hi = [r for r in rows_for(lod_hi) if "no skinCluster" in r]
    lost_lo = [r for r in rows_for(lod_lo) if "no skinCluster" in r]
    _harness.check(not lost_hi,
                   "the still-rigged sibling must not be warned about, got %r" % (lost_hi,))
    _harness.check(len(lost_lo) == 1,
                   "expected exactly one lost-rig warning for the LOD whose rig was "
                   "deleted while its sibling stayed skinned, got %r" % (lost_lo,))
    _harness.check(lost_lo[0].startswith("warning|"),
                   "lost rig is a warning, not an error: %r" % (lost_lo[0],))
    print("OK - lost rig reported once, only for the LOD whose sibling is still skinned")


main()
