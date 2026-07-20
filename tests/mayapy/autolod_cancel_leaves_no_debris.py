"""Cancelling Auto LOD must leave the scene exactly as it was (mayapy).

Auto LOD is the longest operation in the plugin, so Esc has to work — but a cancel
that leaves debris behind is its own bug. Two things are created BEFORE the
decimation that can raise:

  * the ``visuals`` group, passed into _generate_resolution_lods as an argument
  * ``__auto_lod_geometry_source``, a hidden duplicate of the user's mesh whose
    delete originally sat past the raise point

The hidden duplicate is the dangerous one: a second copy of the model, invisible
in the viewport, that exports as an extra LOD if nobody notices.

Run:  mayapy.exe tests/mayapy/autolod_cancel_leaves_no_debris.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.autolod.core import generate_auto_lods  # noqa: E402
from a3ob.ui.autolod.helpers.meshops import AutoLodCancelled  # noqa: E402


class _AlreadyCancelled:
    """Stands in for Progress with Esc already pressed.

    Under mayapy the real Progress degrades to a no-op whose cancelled() is always
    False (API-1.0 MComputation is unavailable), so the cancel path is unreachable
    without this.
    """

    def __init__(self, total):
        self.total = total

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def cancelled(self):
        return True

    def step(self, done):
        pass


def _scene_nodes():
    return set(cmds.ls(long=True, transforms=True) or [])


def test_cancel_removes_the_group_and_the_hidden_duplicate():
    cmds.file(new=True, force=True)
    source = cmds.polySphere(name="cancel_me", subdivisionsX=24, subdivisionsY=24, ch=False)[0]
    before = _scene_nodes()

    import a3ob.mayabridge.progress as progress_module
    real = progress_module.Progress
    progress_module.Progress = _AlreadyCancelled
    try:
        cmds.select(source, replace=True)
        try:
            generate_auto_lods({"resolution": True, "geometry": True, "memory": True})
        except AutoLodCancelled:
            pass
        else:
            raise AssertionError("cancelling mid-decimation must raise AutoLodCancelled")
    finally:
        progress_module.Progress = real

    after = _scene_nodes()
    leaked = sorted(after - before)
    _harness.check(not leaked,
                   f"cancelling Auto LOD left {len(leaked)} node(s) behind: {leaked}")

    _harness.check(cmds.objExists(source),
                   "the user's source mesh must survive a cancelled Auto LOD")
    _harness.check(not cmds.ls("__auto_lod_geometry_source*", long=True),
                   "the hidden geometry-source duplicate must not outlive a cancel")


def test_a_pre_existing_group_is_not_deleted():
    """Cleanup may only remove groups this run created.

    _group() returns an existing group when there is one, so a blind delete would
    destroy a "visuals" the user already had.
    """
    cmds.file(new=True, force=True)
    existing = cmds.group(empty=True, name="visuals")
    source = cmds.polySphere(name="cancel_me_too", subdivisionsX=20, subdivisionsY=20, ch=False)[0]

    import a3ob.mayabridge.progress as progress_module
    real = progress_module.Progress
    progress_module.Progress = _AlreadyCancelled
    try:
        cmds.select(source, replace=True)
        try:
            generate_auto_lods({"resolution": True})
        except AutoLodCancelled:
            pass
    finally:
        progress_module.Progress = real

    _harness.check(cmds.objExists(existing),
                   "a pre-existing empty 'visuals' group is not ours to delete on cancel")


def main():
    test_cancel_removes_the_group_and_the_hidden_duplicate()
    test_a_pre_existing_group_is_not_deleted()
    print("auto lod cancel leaves no debris: OK")


if __name__ == "__main__":
    sys.exit(_harness.run(main))
