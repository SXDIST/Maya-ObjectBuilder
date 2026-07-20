"""Every mesh carrying a bake must also have a live skinCluster (run with mayapy).

Phase 1 deletes a3obBakedWeights outright. That is only safe while no weight exists
ONLY as a bake. Point this at a real scene before deleting anything.

Run:  mayapy.exe tests/mayapy/weights_premise_check.py [scene.mb]
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def orphan_bakes():
    """LOD transforms with stored weights and no live skinCluster."""
    orphans = []
    for node in cmds.ls("*.a3obBakedWeights", objectsOnly=True, long=True) or []:
        if not (cmds.getAttr(node + ".a3obBakedWeights") or ""):
            continue
        shapes = cmds.listRelatives(node, allDescendents=True, type="mesh",
                                    fullPath=True, noIntermediate=True) or []
        live = shapes and cmds.ls(cmds.listHistory(shapes[0], pruneDagObjects=True) or [],
                                  type="skinCluster")
        if not live:
            orphans.append(node)
    return orphans


def main():
    scene = sys.argv[1] if len(sys.argv) > 1 else ""
    if scene:
        cmds.file(scene, open=True, force=True)
    orphans = orphan_bakes()
    _harness.check(
        not orphans,
        "these carry a bake with no live skinCluster, so the bake is their ONLY copy: %r"
        % (orphans,))
    print("OK - %d baked mesh(es), all with a live skinCluster"
          % len(cmds.ls("*.a3obBakedWeights", objectsOnly=True) or []))


if __name__ == "__main__":
    sys.exit(_harness.run(main))
