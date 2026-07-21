"""The proxy dialog reports which of its two modes the current selection implies (mayapy).

The old panel had a "Create from selected components" checkbox, which let the user ask for a
mode the selection could not deliver. The selection already decides: components selected ->
build the proxy from them; nothing selected -> a standalone placeholder. The dialog states
which, rather than offering a control.

Run:  mayapy.exe tests/mayapy/proxy_creation_mode.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.dialogs import proxy_creation_mode  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_components_selected():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".f[0:1]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "faces selected should give 'components', got %r" % mode)


def test_vertices_selected():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".vtx[0:3]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "vertices selected should give 'components', got %r" % mode)


def test_nothing_selected():
    cmds.file(new=True, force=True)
    cmds.polyCube(name="body", ch=False)
    cmds.select(clear=True)
    mode = proxy_creation_mode()
    check(mode == "standalone", "empty selection should give 'standalone', got %r" % mode)


def test_whole_object_selected_is_standalone():
    """A whole transform is not a component selection: the proxy has no faces to attach to."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform, replace=True)
    mode = proxy_creation_mode()
    check(mode == "standalone", "a whole object should give 'standalone', got %r" % mode)


def test_reading_the_mode_does_not_dirty_the_scene():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".f[0]", replace=True)
    cmds.file(modified=False)
    proxy_creation_mode()
    check(not cmds.file(query=True, modified=True),
          "reading the proxy creation mode dirtied the scene")


def main():
    for test in (test_components_selected, test_vertices_selected, test_nothing_selected,
                 test_whole_object_selected_is_standalone,
                 test_reading_the_mode_does_not_dirty_the_scene):
        test()
        print("ok:", test.__name__, flush=True)
    print("PROXY CREATION MODE: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
