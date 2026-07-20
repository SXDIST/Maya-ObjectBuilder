"""The Skinning panel holds no weight-storage UI (run with mayapy).

The storage model is gone, so the panel must not name it, and expanding the panel
must cost no scene scan — its on_expand callback existed only to refresh the state
line.

Run:  mayapy.exe tests/mayapy/weights_panel_state.py
"""

import inspect
import os

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def main():
    cmds.loadPlugin(os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py"))
    from a3ob.ui.panels import skinning

    source = inspect.getsource(skinning)
    for gone in ("a3obBakedWeights", "_weights_state", "run_bake_skin",
                 "run_restore_skin", "refresh_weights_state", "Restore Weights",
                 "Bake Now", "Use the Older Copy"):
        _harness.check(gone not in source,
                       "Skinning panel still references %r" % gone)

    for gone in ("_bake_skin_weights", "_restore_skin_weights"):
        from a3ob.ui import entry
        _harness.check(not hasattr(entry, gone),
                       "entry still exports %r" % gone)

    # Positive control: the panel must still hold the things that stay, or the checks
    # above would pass vacuously against an empty file.
    for kept in ("Transfer Skin from Body", "Test Pose", "influence_list"):
        _harness.check(kept in source, "Skinning panel lost %r" % kept)

    print("OK - storage UI gone, transfer/pose/influences intact")


main()
