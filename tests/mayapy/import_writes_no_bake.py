"""Importing a P3D writes no baked-weight attribute (run with mayapy).

Import used to mirror bone selections into a3obBakedWeights. The skinCluster is the
only store now, and import does not create one, so it must write nothing.

Run:  mayapy.exe tests/mayapy/import_writes_no_bake.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

# The .p3d fixtures live in the gitignored reference clone, not in tests/ — the same
# path golden.py and p3d_workflow.py use. The character sample is the one that carries
# bone selections, which is what makes this test able to fail.
FIXTURE = os.path.join(_harness.REPO, "Arma3ObjectBuilder-master", "tests", "inputs",
                       "p3d", "sample_1_character.p3d")


def main():
    if not os.path.isfile(FIXTURE):
        print("SKIP - fixture absent (clone Arma3ObjectBuilder-master): %s" % FIXTURE)
        sys.exit(0)

    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    cmds.file(new=True, force=True)
    cmds.file(FIXTURE, i=True, type="Arma P3D", ignoreVersion=True,
              mergeNamespacesOnClash=False, options="")

    baked = cmds.ls("*.a3obBakedWeights", objectsOnly=True) or []
    _harness.check(not baked, "import must not write a3obBakedWeights, got %r" % (baked,))
    print("OK - character fixture imported, no baked weights written")


main()
