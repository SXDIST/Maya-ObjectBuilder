"""Regression test for dock refresh cost on component selection (run with mayapy).

The dock rebuilds every panel from the selected LOD, and that rebuild scans every objectSet
in the scene. Reacting to raw SelectionChanged made picking verts on a dense mesh crawl, so
refreshes are debounced and skipped when the shown LOD has not changed. This asserts that
selecting components inside one LOD triggers no rebuild, while switching LOD still does.

Run:  mayapy.exe tests/mayapy/dock_refresh_cost.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui import entry  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_lod(name):
    transform = cmds.polySphere(name=name, subdivisionsX=20, subdivisionsY=20, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    return transform


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
    first = make_lod("lodA")
    second = make_lod("lodB")

    dock = FakeDock()
    entry._active_qt_dock = lambda: dock
    entry._last_context_key = None

    cmds.select(first, replace=True)
    entry._refresh_context_ui(False)
    after_first = dock.rebuilds
    check(after_first > 0, "selecting a LOD must rebuild the dock once")

    # Picking components inside the SAME LOD: the dock shows nothing derived from them.
    shape = cmds.listRelatives(first, shapes=True, fullPath=True)[0]
    for i in range(0, 200, 20):
        cmds.select("%s.vtx[%d:%d]" % (shape, i, i + 19), replace=True)
        entry._refresh_context_ui(False)
    check(dock.rebuilds == after_first,
          "component selection inside one LOD must not rebuild the dock (%d extra rebuilds)"
          % (dock.rebuilds - after_first))

    # Switching to another LOD must still rebuild.
    cmds.select(second, replace=True)
    entry._refresh_context_ui(False)
    check(dock.rebuilds > after_first, "switching LOD must rebuild the dock")

    # Undo/scene events force a rebuild even when the LOD is unchanged.
    before_force = dock.rebuilds
    entry._refresh_context_ui()
    check(dock.rebuilds > before_force, "a forced refresh must rebuild even on the same LOD")

    print("OK dock refresh: component picking costs 0 rebuilds, LOD switch still refreshes")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:  # noqa: BLE001
        print("FAIL dock_refresh_cost: %s" % error, file=sys.stderr)
        raise
