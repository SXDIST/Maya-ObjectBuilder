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

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.mayabridge import skintransfer  # noqa: E402
from a3ob.mayabridge.skinweights import MIN_ENCODABLE_WEIGHT  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


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


def main():
    cmds.loadPlugin(os.path.join(_REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.undoInfo(state=True, infinity=True)

    body, body_skin, garment = build_scene()
    body_shape = cmds.listRelatives(body, shapes=True, fullPath=True)[0]
    garment_shape = cmds.listRelatives(garment, shapes=True, fullPath=True)[0]

    body_before = [weights_of(body_skin, body_shape, i)
                   for i in range(cmds.polyEvaluate(body, vertex=True))]

    cmds.select(garment, replace=True)
    targets = skintransfer.selected_mesh_shapes()
    check(len(targets) == 1, "expected one selected mesh, got %d" % len(targets))
    reference = skintransfer.find_reference(targets)
    check("body" in reference.fullPathName(),
          "reference must be the skinned body, got %s" % reference.fullPathName())

    cmds.undoInfo(openChunk=True)
    try:
        count, rigidified = skintransfer.transfer_to_target(targets[0], reference)
    finally:
        cmds.undoInfo(closeChunk=True)

    skin = skintransfer.skin_cluster_of(targets[0])
    influences = cmds.skinCluster(skin, query=True, influence=True) or []
    check(count > 0, "no vertices processed")
    check(rigidified == 1, "the detached pouch must be rigidified exactly once, got %d" % rigidified)

    # 1. Fitted part follows the body: a vertex near the top must be Upper-dominated.
    upper_index = influences.index([i for i in influences if i.endswith("Upper")][0])
    top_vertex = None
    for i in range(count):
        position = cmds.pointPosition("%s.vtx[%d]" % (garment_shape, i), world=True)
        if position[1] > 2.5 and abs(position[0]) < 1.5:  # on the sleeve, not the pouch
            top_vertex = i
            break
    check(top_vertex is not None, "no sleeve vertex found near the top")
    top_weights = weights_of(skin, garment_shape, top_vertex)
    check(top_weights[upper_index] > 0.8,
          "top of the sleeve must follow Upper like the body does, got %r" % (top_weights,))

    # 2. The pouch shell must be rigid: identical weights on every one of its vertices.
    pouch_vertices = [i for i in range(count)
                      if cmds.pointPosition("%s.vtx[%d]" % (garment_shape, i), world=True)[0] > 2.0]
    check(len(pouch_vertices) == 8, "expected the 8 pouch vertices, got %d" % len(pouch_vertices))
    reference_weights = weights_of(skin, garment_shape, pouch_vertices[0])
    check(sum(reference_weights) > 0.0, "the pouch must carry weights, got %r" % (reference_weights,))
    for vertex in pouch_vertices[1:]:
        current = weights_of(skin, garment_shape, vertex)
        check(all(abs(a - b) < 1e-4 for a, b in zip(current, reference_weights)),
              "pouch vertex %d differs from its shell: %r vs %r"
              % (vertex, current, reference_weights))

    # 3. DayZ rules across the whole garment.
    for i in range(count):
        values = weights_of(skin, garment_shape, i)
        used = [v for v in values if v > 0.0]
        check(len(used) <= 4, "vertex %d has %d influences (max 4)" % (i, len(used)))
        check(abs(sum(values) - 1.0) < 1e-3, "vertex %d is not normalized: %.5f" % (i, sum(values)))
        for value in used:
            check(value > MIN_ENCODABLE_WEIGHT,
                  "vertex %d keeps weight %.6f, which encodes to zero in the p3d" % (i, value))

    # 4. The reference body must be untouched.
    body_after = [weights_of(body_skin, body_shape, i)
                  for i in range(cmds.polyEvaluate(body, vertex=True))]
    check(body_before == body_after, "the reference body's weights were modified")

    # 5. One undo must take the whole thing back.
    cmds.undo()
    check(not skintransfer.skin_cluster_of(targets[0]),
          "undo must remove the skinCluster the transfer created")

    print("OK skin transfer: %d verts, %d rigid shell(s), DayZ rules satisfied, body untouched"
          % (count, rigidified))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL skin_transfer: %s" % error, file=sys.stderr)
        raise
