"""Texture import is opt-out (run with mayapy).

Decoding .paa and wiring file nodes is the slow part of an import. It stays ON by
default — existing behaviour — but a user who does not want it must be able to say so.

Run:  mayapy.exe tests/mayapy/import_textures_optional.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

FIXTURE = os.path.join(_harness.REPO, "Arma3ObjectBuilder-master", "tests", "inputs",
                       "p3d", "sample_1_character.p3d")


def import_with(options):
    cmds.file(new=True, force=True)
    cmds.file(FIXTURE, i=True, type="Arma P3D", ignoreVersion=True,
              mergeNamespacesOnClash=False, options=options)
    cmds.refresh()


def main():
    if not os.path.isfile(FIXTURE):
        print("SKIP - fixture absent (clone Arma3ObjectBuilder-master): %s" % FIXTURE)
        sys.exit(0)
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))

    import a3ob.mayabridge.paatex as paatex
    calls = []
    original = paatex.assign_pending_textures
    paatex.assign_pending_textures = lambda *a, **k: calls.append(1)
    try:
        import_with("importTextures=0")
        cmds.evalDeferred(lambda: None, lowestPriority=True)
        _harness.check(not calls,
                       "importTextures=0 must not schedule texture assignment, got %r"
                       % (calls,))

        import_with("importTextures=1")
        cmds.evalDeferred(lambda: None, lowestPriority=True)
        _harness.check(calls,
                       "importTextures=1 must schedule texture assignment")
    finally:
        paatex.assign_pending_textures = original
    print("OK - texture assignment follows importTextures")


main()
