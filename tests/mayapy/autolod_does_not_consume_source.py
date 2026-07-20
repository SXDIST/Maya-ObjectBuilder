"""Auto LOD leaves the source mesh alone (run with mayapy).

_generate_resolution_lods used to rename the source into LOD1 — it consumed the mesh
the user selected. Generation at export has to be able to delete everything it made,
which is impossible while one of those nodes is the user's own mesh.

Run:  mayapy.exe tests/mayapy/autolod_does_not_consume_source.py
"""

import os

import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def build_skinned_source():
    cmds.file(new=True, force=True)
    transform = cmds.polySphere(name="garment", r=1, sx=12, sy=12, ch=False)[0]
    cmds.select(clear=True)
    root = cmds.joint(position=(0, -1, 0), name="Pelvis")
    tip = cmds.joint(position=(0, 1, 0), name="Spine")
    cmds.skinCluster(root, tip, transform, toSelectedBones=True, maximumInfluences=4)
    # A selection set on the source: generation must carry it onto LOD1, not lose it.
    cmds.select(transform + ".vtx[0:10]", replace=True)
    set_node = cmds.sets(name="a3ob_SEL_camo_test")
    cmds.addAttr(set_node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_node + ".a3obSelectionName", "camo_test", type="string")
    cmds.select(transform, replace=True)
    return transform


def live_weights(mesh):
    shape = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True)[0]
    skins = cmds.ls(cmds.listHistory(shape, pruneDagObjects=True) or [], type="skinCluster")
    if not skins:
        return None
    sel = om.MSelectionList(); sel.add(skins[0])
    fn = oma.MFnSkinCluster(sel.getDependNode(0))
    sel2 = om.MSelectionList(); sel2.add(shape)
    comp = om.MFnSingleIndexedComponent().create(om.MFn.kMeshVertComponent)
    om.MFnSingleIndexedComponent(comp).setCompleteData(cmds.polyEvaluate(mesh, vertex=True))
    weights, _cols = fn.getWeights(sel2.getDagPath(0), comp)
    return list(weights)


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    from a3ob.mayabridge.autolod import generate_auto_lods

    source = build_skinned_source()
    before = live_weights(source)
    _harness.check(before is not None, "fixture must be skinned or this test proves nothing")

    generated = generate_auto_lods({"resolution": True, "geometry": False})
    _harness.check(bool(generated), "expected generated LODs, got %r" % (generated,))

    _harness.check(cmds.objExists(source),
                   "the source mesh must survive generation under its own name")
    after = live_weights(source)
    _harness.check(after is not None,
                   "the source must keep its skinCluster")
    _harness.check(after == before,
                   "the source's weights must be untouched")

    # LOD1 is a copy now, so it must have been given the source's weights and selections.
    lod1 = [n for n in generated if cmds.objExists(n)
            and "1" in n.split("|")[-1] and n.split("|")[-1] != source]
    _harness.check(bool(lod1), "expected a full-resolution LOD, got %r" % (generated,))
    lod1_weights = live_weights(lod1[0])
    _harness.check(lod1_weights is not None,
                   "LOD1 must be bound — a duplicate has no skinCluster unless re-bound")
    _harness.check(max(abs(a - b) for a, b in zip(before, lod1_weights)) == 0.0,
                   "LOD1's weights must match the source EXACTLY; copySkinWeights is not "
                   "exact enough (measured 0.1027 on identical geometry)")
    members = cmds.sets("a3ob_SEL_camo_test", query=True) or []
    _harness.check(any(lod1[0].split("|")[-1] in m for m in members),
                   "LOD1 must have been added to the source's selection set, got %r" % (members,))
    print("OK - source survives intact, LOD1 carries its weights and selections")


main()
