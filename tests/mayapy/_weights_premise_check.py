"""Manual gate: every mesh carrying a bake must also have a live skinCluster (run with mayapy).

MANUAL GATE — excluded from suite auto-discovery by the leading underscore in the filename.
Requires a scene path argument to do any real work; run with no arguments does nothing.

Phase 1 deletes a3obBakedWeights outright. That is only safe while no weight exists
ONLY as a bake. Point this at a real scene before deleting anything.

Run:  mayapy.exe tests/mayapy/_weights_premise_check.py <scene.mb>
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def baked_nodes():
    """Transforms carrying a stored (non-empty) a3obBakedWeights value.

    A bare ``a3obBakedWeights`` attribute with nothing stored in it is not a bake —
    ``orphan_bakes`` skips those, so the summary count has to use this same population
    or it overstates how many meshes were actually evaluated.
    """
    return [node for node in cmds.ls("*.a3obBakedWeights", objectsOnly=True, long=True) or []
            if cmds.getAttr(node + ".a3obBakedWeights") or ""]


def orphan_bakes():
    """LOD transforms with stored weights and no live skinCluster."""
    orphans = []
    for node in baked_nodes():
        shapes = cmds.listRelatives(node, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        live = shapes and cmds.ls(cmds.listHistory(shapes[0], pruneDagObjects=True) or [],
                                  type="skinCluster")
        if not live:
            orphans.append(node)
    return orphans


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else ""
    if not scene:
        # No scene means an empty standalone scene, which trivially has zero baked
        # meshes and would otherwise print "OK - 0 baked mesh(es)" — a green result
        # that proves nothing. Say so plainly instead of claiming a real check ran.
        print("SKIP weights premise check — no scene given, nothing was checked "
              "(run: mayapy tests/mayapy/_weights_premise_check.py <scene.mb>)")
        return 0
    cmds.file(scene, open=True, force=True)
    orphans = orphan_bakes()
    _harness.check(
        not orphans,
        "these carry a bake with no live skinCluster, so the bake is their ONLY copy: %r"
        % (orphans,))
    print("OK - %d baked mesh(es), all with a live skinCluster"
          % len(baked_nodes()))


if __name__ == "__main__":
    sys.exit(_harness.run(main))
