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


def build_all_unrigged_model():
    """A model whose LODs are ALL unrigged and NEVER had a skinCluster — the static-prop
    case this gate exists to keep silent. Two LODs sharing a parent group (so the sibling
    walk has something to look at), neither ever skinned.

    This is the negative case: without ``_model_has_skinned_sibling`` gating the warning,
    reverting to "warn on every mesh with no skinCluster" would fire on both of these and
    fail the assertion below — which is what actually proves the gate does something,
    unlike the rigged/unrigged-sibling pair above that passes either way."""
    model = cmds.group(empty=True, name="static_model")

    lod_a = cmds.polyCylinder(name="static_hi", r=1, h=4, sx=8, sy=4, ch=False)[0]
    _mark_lod(lod_a, 0)
    cmds.parent(lod_a, model)

    lod_b = cmds.polyCylinder(name="static_lo", r=1, h=4, sx=4, sy=2, ch=False)[0]
    _mark_lod(lod_b, 1)
    cmds.parent(lod_b, model)

    return lod_a, lod_b


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

    # A model whose LODs are ALL unrigged (a static prop, or a lone LOD with no skinned
    # sibling) must produce ZERO "no skinCluster" warnings. This is the negative case that
    # actually exercises _model_has_skinned_sibling: if that gate were removed and the code
    # reverted to warning on every mesh with no skinCluster, every check above would still
    # pass unchanged (phase 1 has no unrigged mesh, phase 2's unrigged mesh is expected to
    # warn either way) — only this assertion can fail on that regression.
    static_hi, static_lo = build_all_unrigged_model()
    lost_static_hi = [r for r in rows_for(static_hi) if "no skinCluster" in r]
    lost_static_lo = [r for r in rows_for(static_lo) if "no skinCluster" in r]
    _harness.check(not lost_static_hi and not lost_static_lo,
                   "a model with no skinned sibling anywhere (static prop) must never warn "
                   "about a missing skinCluster, got hi=%r lo=%r" % (lost_static_hi, lost_static_lo))

    print("OK - lost rig reported once, only for the LOD whose sibling is still skinned, "
          "and a fully-unrigged model stays silent")


main()
