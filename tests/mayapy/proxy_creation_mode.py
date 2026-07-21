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


def test_edges_selected():
    """Edges are a mesh component like any other: create_proxy_selection_set accepts them.

    That helper takes ANY non-null component on a mesh (kMesh + not component.isNull()), so an
    edge selection really does produce a proxy selection set. A classifier that only looked for
    faces and vertices sent fromSelection=False and silently created nothing."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".e[0:3]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "edges selected should give 'components', got %r" % mode)


def test_uvs_selected():
    """UVs likewise: a kMeshMapComponent is non-null and lives on a mesh."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    cmds.select(transform + ".map[0:3]", replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "UVs selected should give 'components', got %r" % mode)


def test_mixed_component_and_whole_object_is_components():
    """Components plus a whole object -> "components".

    create_proxy_selection_set filters per selection entry rather than rejecting the whole
    selection: the whole-object entry contributes nothing, the component entry does, and the
    resulting set is non-empty. "components" is therefore the truthful answer — it is exactly
    what the command will do. Answering "standalone" would both mis-describe the outcome and,
    via fromSelection=False, suppress a set the command would otherwise have built."""
    cmds.file(new=True, force=True)
    body = cmds.polyCube(name="body", ch=False)[0]
    other = cmds.polyCube(name="other", ch=False)[0]
    cmds.select([body + ".f[0]", other], replace=True)
    mode = proxy_creation_mode()
    check(mode == "components", "components + a whole object should give 'components', got %r" % mode)


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
    for test in (test_components_selected, test_vertices_selected, test_edges_selected,
                 test_uvs_selected, test_mixed_component_and_whole_object_is_components,
                 test_nothing_selected, test_whole_object_selected_is_standalone,
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
