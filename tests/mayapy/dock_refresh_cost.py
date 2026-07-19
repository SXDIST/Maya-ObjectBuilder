"""Regression test for dock refresh cost on component selection (run with mayapy).

The dock rebuilds every panel from the selected LOD, and that rebuild scans every objectSet
in the scene. Reacting to raw SelectionChanged made picking verts on a dense mesh crawl, so
refreshes are debounced and skipped when the shown LOD has not changed. This asserts that
selecting components inside one LOD triggers no rebuild, while switching LOD still does.

Run:  mayapy.exe tests/mayapy/dock_refresh_cost.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui import entry  # noqa: E402


class FakeDock:
    """Stands in for the Qt dock: counts how many times the panels get rebuilt."""

    def __init__(self):
        self.rebuilds = 0

    def _count(self, *_args, **_kwargs):
        self.rebuilds += 1

    refresh_lod_list = _count
    refresh_lod_assignment = _count
    refresh_named_properties = _count
    refresh_material_metadata = _count
    refresh_selection_manager = _count
    refresh_mass_summary = _count
    refresh_influences = _count


def main():
    first = _harness.make_lod("lodA", kind="sphere")
    second = _harness.make_lod("lodB", kind="sphere")

    dock = FakeDock()
    entry._active_qt_dock = lambda: dock
    entry._last_context_key = None

    cmds.select(first, replace=True)
    entry._refresh_context_ui(False)
    after_first = dock.rebuilds
    _harness.check(after_first > 0, "selecting a LOD must rebuild the dock once")

    # Picking components inside the SAME LOD: the dock shows nothing derived from them.
    shape = cmds.listRelatives(first, shapes=True, fullPath=True)[0]
    for i in range(0, 200, 20):
        cmds.select("%s.vtx[%d:%d]" % (shape, i, i + 19), replace=True)
        entry._refresh_context_ui(False)
    _harness.check(dock.rebuilds == after_first,
          "component selection inside one LOD must not rebuild the dock (%d extra rebuilds)"
          % (dock.rebuilds - after_first))

    # Switching to another LOD must still rebuild.
    cmds.select(second, replace=True)
    entry._refresh_context_ui(False)
    _harness.check(dock.rebuilds > after_first, "switching LOD must rebuild the dock")

    # Undo/scene events force a rebuild even when the LOD is unchanged.
    before_force = dock.rebuilds
    entry._refresh_context_ui()
    _harness.check(dock.rebuilds > before_force, "a forced refresh must rebuild even on the same LOD")

    print("OK dock refresh: component picking costs 0 rebuilds, LOD switch still refreshes")
    test_sibling_mesh_switch_refreshes(dock)


def test_sibling_mesh_switch_refreshes(dock):
    """Two meshes under ONE LOD must each refresh the panels when selected.

    Reported from real use: the Influences list stayed empty until you typed something into
    the filter box and deleted it again — the only thing that called the refresh directly.
    The cause was the context key holding the LOD alone, so picking a different garment under
    the same LOD looked like no change at all and the refresh short-circuited."""
    parent = _harness.make_lod("lodShared", kind="sphere")
    first = cmds.polyCylinder(name="garmentA", r=1, h=2, ch=False)[0]
    second = cmds.polyCylinder(name="garmentB", r=1, h=2, ch=False)[0]
    cmds.parent(first, parent)
    cmds.parent(second, parent)

    cmds.select(first, replace=True)
    entry._refresh_context_ui(False)
    baseline = dock.rebuilds

    cmds.select(second, replace=True)
    entry._refresh_context_ui(False)
    _harness.check(dock.rebuilds > baseline,
          "selecting a sibling mesh under the same LOD must refresh the panels")

    # ...and picking components on that mesh must still cost nothing.
    settled = dock.rebuilds
    shape = cmds.listRelatives(second, shapes=True, fullPath=True)[0]
    for i in range(0, 60, 20):
        cmds.select("%s.vtx[%d:%d]" % (shape, i, i + 19), replace=True)
        entry._refresh_context_ui(False)
    _harness.check(dock.rebuilds == settled,
          "component picking on that mesh must still cost 0 rebuilds (%d extra)"
          % (dock.rebuilds - settled))

    print("OK sibling mesh switch refreshes, its components still cost nothing")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
