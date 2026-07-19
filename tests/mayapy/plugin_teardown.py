"""Nothing this plugin installs may outlive unloading it (run with mayapy).

Maya crashes on shutdown when a callback registered by a plugin fires after the plugin's
Python objects are gone. The plugin installs two kinds: `weightsync`'s kBeforeSave callback
(an MMessage id) and the dock's scriptJobs. Both must be gone after unload, and loading and
unloading repeatedly must not accumulate either — an idempotency bug here shows up as a
crash on exit, days later, with no traceback to connect it to.

Run:  mayapy.exe tests/mayapy/plugin_teardown.py
"""

import os
import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds

_PLUGIN = os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py")


def our_script_jobs():
    """scriptJobs whose command mentions this plugin's UI module."""
    return [job for job in (cmds.scriptJob(listJobs=True) or [])
            if "objectBuilderMenu" in job or "a3ob" in job]


def main():
    from a3ob.mayabridge import weightsync

    baseline_jobs = len(our_script_jobs())

    for cycle in range(3):
        cmds.loadPlugin(_PLUGIN)
        _harness.check(cmds.pluginInfo("MayaObjectBuilder", query=True, loaded=True),
              "cycle %d: the plugin must load" % cycle)

        # The save callback must be installed exactly once, however many times install()
        # is called — a second id would fire the sync twice and leak on unload.
        weightsync.install()
        weightsync.install()
        _harness.check(len(weightsync._callback_ids) == 1,
              "cycle %d: install() must be idempotent, got %d callback(s)"
              % (cycle, len(weightsync._callback_ids)))

        cmds.file(new=True, force=True)
        cmds.unloadPlugin("MayaObjectBuilder")

        _harness.check(not weightsync._callback_ids,
              "cycle %d: unloading must remove the save callback, %d left"
              % (cycle, len(weightsync._callback_ids)))
        _harness.check(len(our_script_jobs()) == baseline_jobs,
              "cycle %d: unloading must remove our scriptJobs, %d left over"
              % (cycle, len(our_script_jobs()) - baseline_jobs))

    # Unloading when nothing was installed must not raise either.
    weightsync.uninstall()
    weightsync.uninstall()

    # And a save with the plugin unloaded must not reach our callback.
    cmds.file(new=True, force=True)
    transform = cmds.polyCylinder(name="orphan", r=1, h=2, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    import tempfile
    scene = os.path.join(tempfile.mkdtemp(prefix="teardown-"), "scene.ma")
    cmds.file(rename=scene)
    cmds.file(save=True, type="mayaAscii", force=True)

    print("OK plugin teardown: no callback or scriptJob survives unload (3 cycles)")
    return 0


if __name__ == "__main__":
    sys.exit(_harness.run(main))
