"""DayZ skin transfer: garment weights copied from the reference body (run with mayapy).

Builds a miniature of the real case — a skinned "body" cylinder on a two-joint chain, a
"garment" sleeve fitted around it, and a detached "pouch" shell standing off to the side —
then checks the pipeline end to end:

* the garment picks up the body's weights at matching heights;
* the detached shell becomes rigid (one identical weight set across all its vertices) rather
  than smearing across joints by closest point;
* the result obeys DayZ: <= 4 influences, normalized, nothing in (0, 1/254];
* the reference body is left untouched;
* the whole thing undoes in one step.

Run:  mayapy.exe tests/mayapy/skin_transfer.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

from a3ob.mayabridge import skintransfer
from a3ob.mayabridge.skinweights import MIN_ENCODABLE_WEIGHT


def weights_of(skin, shape, vertex):
    return cmds.skinPercent(skin, "%s.vtx[%d]" % (shape, vertex), query=True, value=True)


def build_scene():
    """Body cylinder skinned to Lower/Upper, plus a garment sleeve and a detached pouch."""
    cmds.file(new=True, force=True)
    body = cmds.polyCylinder(name="body", r=1.0, h=6, sx=12, sy=8, ch=False)[0]
    cmds.select(clear=True)
    lower = cmds.joint(position=(0, -3, 0), name="Lower")
    upper = cmds.joint(position=(0, 3, 0), name="Upper")
    body_skin = cmds.skinCluster(lower, upper, body, toSelectedBones=True,
                                 maximumInfluences=4)[0]

    body_shape = cmds.listRelatives(body, shapes=True, fullPath=True)[0]
    # Explicit gradient so the expected answer is known exactly.
    for i in range(cmds.polyEvaluate(body, vertex=True)):
        height = cmds.pointPosition("%s.vtx[%d]" % (body_shape, i), world=True)[1]
        up = min(1.0, max(0.0, (height + 3.0) / 6.0))
        cmds.skinPercent(body_skin, "%s.vtx[%d]" % (body_shape, i),
                         transformValue=[(lower, 1.0 - up), (upper, up)])

    # Garment: a sleeve fitted around the body — the gap must stay UNDER the far-distance
    # threshold, or the sleeve itself counts as detached geometry (the first run of this test
    # used r=1.05, a 0.05 gap, and the sleeve was rigidified too).
    garment = cmds.polyCylinder(name="garment", r=1.01, h=6, sx=12, sy=8, ch=False)[0]
    # Pouch: a small cube standing well away from the body.
    pouch = cmds.polyCube(name="pouch", w=0.4, h=0.4, d=0.4, ch=False)[0]
    cmds.setAttr(pouch + ".translateX", 2.5)
    cmds.setAttr(pouch + ".translateY", 1.5)
    garment = cmds.polyUnite(garment, pouch, name="garmentWithPouch", ch=False)[0]
    cmds.delete(garment, constructionHistory=True)
    return body, body_skin, garment


def test_reference_added_from_file():
    """The body need not be in the scene: the saved reference is imported and used.

    What it brings STAYS. The asset carries its own skeleton, the garment binds to
    exactly those joints, and removing them again would delete the skinCluster and
    every weight just transferred."""
    import tempfile

    from a3ob.mayabridge import references, skintransfer

    body, _body_skin, garment = build_scene()

    # Save to a throwaway path and restore the optionVar afterwards: the real reference
    # asset is the user's own DayZ body and must not be overwritten by a test run.
    option_var = references.KINDS["male_body"][0]
    had_var = cmds.optionVar(exists=option_var)
    previous = cmds.optionVar(query=option_var) if had_var else ""
    scratch = os.path.join(tempfile.mkdtemp(prefix="ref-"), "body.ma")

    try:
        # Saved while hidden, exactly as a reference gets made in practice: the body is
        # tucked away while the garment is fitted, and that state travels into the .ma.
        cmds.setAttr(body + ".visibility", False)
        cmds.select(body, replace=True)
        references.save_reference("male_body", scratch)
        cmds.delete(body)
        cmds.delete(cmds.ls(type="joint") or [])
        _harness.check(not cmds.objExists(body), "the body must be gone from the scene")
        _harness.check(not cmds.ls(type="joint"), "the skeleton must be gone from the scene")

        cmds.select(garment, replace=True)
        targets = skintransfer.selected_mesh_shapes()
        reference, imported = skintransfer.ensure_reference(targets)
        _harness.check(reference is not None, "a reference must be produced from the saved file")
        _harness.check(imported, "the saved asset must have been imported, got %r" % (imported,))

        # An asset that arrives invisible reads as a failed import.
        for node in imported:
            _harness.check(cmds.getAttr(node + ".visibility"),
                  "imported reference node %r must arrive visible" % (node,))

        count, _rigid = skintransfer.transfer_to_target(targets[0], reference)
        _harness.check(count > 0, "transfer must run against the imported reference")

        # The point of keeping the import: the rig is still there to edit and to export.
        skin = skintransfer.skin_cluster_of(targets[0])
        _harness.check(skin, "the garment must still carry the transferred skinCluster")
        _harness.check(cmds.ls(type="joint"), "the imported skeleton must remain — the rig needs it")
        influences = cmds.skinCluster(skin, query=True, influence=True) or []
        _harness.check(influences, "the transferred skinCluster must keep its influences")

        # A second call must reuse what is now in the scene rather than import again.
        _again, imported_again = skintransfer.ensure_reference(targets)
        _harness.check(not imported_again,
              "a reference already in the scene must be reused, imported %r" % (imported_again,))
    finally:
        if had_var:
            cmds.optionVar(stringValue=(option_var, previous))
        else:
            cmds.optionVar(remove=option_var)

    print("OK reference added from file, rig kept, reused on the next call")


def test_small_accessory_still_transfers():
    """A patch is legitimately a fraction of the body's size and must still transfer.

    Measured on a real DayZ outfit against a 2.30-unit body: the jacket sits at a size
    ratio of 1.63, the helmet at 5.0, a headphone cup at 8.9 and a helmet patch at 59.1 —
    all correctly fitted, all within 0.08 of the body surface. A blocking ratio test
    cannot tell those from a genuine unit mismatch, so alignment only warns."""
    from a3ob.mayabridge import skintransfer

    body, _body_skin, _garment = build_scene()

    # A patch: tiny next to the body, but sitting right on its surface.
    patch = cmds.polyCube(name="patch", w=0.12, h=0.12, d=0.02, ch=False)[0]
    cmds.setAttr(patch + ".translateX", 1.0)
    cmds.setAttr(patch + ".translateY", 1.0)

    patch_path = skintransfer.selected_mesh_shapes.__globals__["_shape_of"](patch)
    body_path = skintransfer.selected_mesh_shapes.__globals__["_shape_of"](body)

    # Being much smaller than the body is not itself suspicious any more.
    _harness.check(not skintransfer.check_alignment(patch_path, body_path),
          "a patch-sized target must not be flagged at all: %r"
          % (skintransfer.check_alignment(patch_path, body_path),))

    count, _rigid = skintransfer.transfer_to_target(patch_path, body_path)
    _harness.check(count > 0, "a small accessory must still receive weights")
    _harness.check(skintransfer.skin_cluster_of(patch_path),
          "the patch must carry a skinCluster after the transfer")

    # A genuine order-of-magnitude mismatch must still be REPORTED — and still not refuse,
    # because the report is advice now, not a gate.
    strayed = cmds.polyCube(name="strayed", w=0.01, h=0.01, d=0.01, ch=False)[0]
    cmds.setAttr(strayed + ".translateX", 1.0)
    strayed_path = skintransfer.selected_mesh_shapes.__globals__["_shape_of"](strayed)
    _harness.check(skintransfer.check_alignment(strayed_path, body_path),
          "a 100x size gap must still produce a warning message")
    count, _rigid = skintransfer.transfer_to_target(strayed_path, body_path)
    _harness.check(count > 0, "even a flagged pair must transfer — the check advises, it does not gate")

    print("OK small accessory transfers; a gross mismatch warns without refusing")


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)

    body, body_skin, garment = build_scene()
    body_shape = cmds.listRelatives(body, shapes=True, fullPath=True)[0]
    garment_shape = cmds.listRelatives(garment, shapes=True, fullPath=True)[0]

    body_before = [weights_of(body_skin, body_shape, i)
                   for i in range(cmds.polyEvaluate(body, vertex=True))]

    cmds.select(garment, replace=True)
    targets = skintransfer.selected_mesh_shapes()
    _harness.check(len(targets) == 1, "expected one selected mesh, got %d" % len(targets))
    reference = skintransfer.find_reference(targets)
    _harness.check("body" in reference.fullPathName(),
          "reference must be the skinned body, got %s" % reference.fullPathName())

    cmds.undoInfo(openChunk=True)
    try:
        count, rigidified = skintransfer.transfer_to_target(targets[0], reference)
    finally:
        cmds.undoInfo(closeChunk=True)

    skin = skintransfer.skin_cluster_of(targets[0])
    influences = cmds.skinCluster(skin, query=True, influence=True) or []
    _harness.check(count > 0, "no vertices processed")
    _harness.check(rigidified == 1, "the detached pouch must be rigidified exactly once, got %d" % rigidified)

    # 1. Fitted part follows the body: a vertex near the top must be Upper-dominated.
    upper_index = influences.index([i for i in influences if i.endswith("Upper")][0])
    top_vertex = None
    for i in range(count):
        position = cmds.pointPosition("%s.vtx[%d]" % (garment_shape, i), world=True)
        if position[1] > 2.5 and abs(position[0]) < 1.5:  # on the sleeve, not the pouch
            top_vertex = i
            break
    _harness.check(top_vertex is not None, "no sleeve vertex found near the top")
    top_weights = weights_of(skin, garment_shape, top_vertex)
    _harness.check(top_weights[upper_index] > 0.8,
          "top of the sleeve must follow Upper like the body does, got %r" % (top_weights,))

    # 2. The pouch shell must be rigid: identical weights on every one of its vertices.
    pouch_vertices = [i for i in range(count)
                      if cmds.pointPosition("%s.vtx[%d]" % (garment_shape, i), world=True)[0] > 2.0]
    _harness.check(len(pouch_vertices) == 8, "expected the 8 pouch vertices, got %d" % len(pouch_vertices))
    reference_weights = weights_of(skin, garment_shape, pouch_vertices[0])
    _harness.check(sum(reference_weights) > 0.0, "the pouch must carry weights, got %r" % (reference_weights,))
    for vertex in pouch_vertices[1:]:
        current = weights_of(skin, garment_shape, vertex)
        _harness.check(all(abs(a - b) < 1e-4 for a, b in zip(current, reference_weights)),
              "pouch vertex %d differs from its shell: %r vs %r"
              % (vertex, current, reference_weights))

    # 3. DayZ rules across the whole garment.
    for i in range(count):
        values = weights_of(skin, garment_shape, i)
        used = [v for v in values if v > 0.0]
        _harness.check(len(used) <= 4, "vertex %d has %d influences (max 4)" % (i, len(used)))
        _harness.check(abs(sum(values) - 1.0) < 1e-3, "vertex %d is not normalized: %.5f" % (i, sum(values)))
        for value in used:
            _harness.check(value > MIN_ENCODABLE_WEIGHT,
                  "vertex %d keeps weight %.6f, which encodes to zero in the p3d" % (i, value))

    # 3b. Redistribution must follow the neighbours, not bone proximity. Zeroing an
    # influence cannot delete weight — it moves it — and "Distance" sends it to whichever
    # bone is nearest, which is how head weight ends up on a sleeve.
    _harness.check(cmds.getAttr(skin + ".weightDistribution") == 1,
          "weightDistribution must be Neighbors (1), got %r"
          % (cmds.getAttr(skin + ".weightDistribution"),))

    # 4. The reference body must be untouched.
    body_after = [weights_of(body_skin, body_shape, i)
                  for i in range(cmds.polyEvaluate(body, vertex=True))]
    _harness.check(body_before == body_after, "the reference body's weights were modified")

    # 5. One undo must take the whole thing back.
    cmds.undo()
    _harness.check(not skintransfer.skin_cluster_of(targets[0]),
          "undo must remove the skinCluster the transfer created")

    print("OK skin transfer: %d verts, %d rigid shell(s), DayZ rules satisfied, body untouched"
          % (count, rigidified))

    test_small_accessory_still_transfers()
    test_reference_added_from_file()
    return 0


if __name__ == "__main__":
    sys.exit(_harness.run(main))
