"""The dock panels must follow the SELECTED LOD, and stay quiet while doing it (mayapy).

Three regressions, all from the same mistake — a panel guessing which LOD it is showing
instead of being told the node:

1. ``a3obInfluence -listInfluences`` is what the Influences panel calls on every selection
   change. A query that warns turns "click any mesh in the scene" into a Script Editor full
   of "select a skinned mesh first". Queries are silent; only the acting flags speak up.
2. Selections were filtered by the LOD's *label* ("Resolution 1"), and a label is not an
   identity: a real DayZ scene had `|helmet`, `|group1|body|Resolution_2` and
   `|group1|body|Resolution_1` all labelled "Resolution 1", so every one of them listed all
   the others' sets. Filtering is by LOD node.
3. The LOD list restored its highlight from its own previous row before looking at the
   scene, so selecting a LOD in the viewport never moved the highlight.

Run:  mayapy.exe tests/mayapy/dock_panel_sync.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.OpenMaya as om1  # noqa: E402 - API 1.0 has the command-output callback

from a3ob.ui.scene.lods import (  # noqa: E402
    _lod_name_from_transform, _lod_list_target, _selected_selection_owner)
from a3ob.ui.scene.selections import selection_sets_for_owner  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_lod(name, lod_type=0, resolution=1):
    transform = cmds.polyCube(name=name, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.setAttr(transform + ".a3obLodType", lod_type)
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    cmds.setAttr(transform + ".a3obResolution", resolution)
    return cmds.ls(transform, long=True)[0]


def make_selection_set(lod, name):
    shape = cmds.listRelatives(lod, shapes=True, fullPath=True)[0]
    node = cmds.sets("%s.f[0:2]" % shape, name=name)
    cmds.addAttr(node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(node + ".a3obSelectionName", name, type="string")
    return node


def test_selections_are_filtered_by_lod_node():
    """Two LODs sharing a label must not share their selections."""
    cmds.file(new=True, force=True)
    first = make_lod("lodA")
    second = make_lod("lodB")
    check(_lod_name_from_transform(first) == _lod_name_from_transform(second),
          "the fixture is pointless unless both LODs carry the same label")

    make_selection_set(first, "belt")
    make_selection_set(second, "strap")

    on_first = [item["name"] for item in selection_sets_for_owner(first)]
    on_second = [item["name"] for item in selection_sets_for_owner(second)]
    check(on_first == ["belt"], "lodA must list only its own set, got %r" % (on_first,))
    check(on_second == ["strap"], "lodB must list only its own set, got %r" % (on_second,))
    check(selection_sets_for_owner(None) == [], "no LOD selected means nothing to list")


def test_legacy_named_orphan_still_surfaces():
    """A set with no members has no owning node; a legacy name still says which LOD.

    Sets written by this plugin are named `a3ob_SEL_<name>` and carry no LOD in the name,
    so an emptied one belongs nowhere either way. The name-derived fallback exists for the
    older `<LOD>_SEL_<name>` scenes, and node matching must not have taken it away."""
    cmds.file(new=True, force=True)
    lod = make_lod("body", resolution=0)
    node = make_selection_set(lod, "Resolution_0_SEL_ghost")
    cmds.sets(clear=node)
    names = [item["node"] for item in selection_sets_for_owner(lod)]
    check(names == ["Resolution_0_SEL_ghost"],
          "a legacy set naming its LOD must still be listed, got %r" % (names,))


def test_selections_show_on_a_mesh_that_is_not_a_lod_yet():
    """People name parts while modelling, long before anything is marked as a LOD.

    Keying the panel strictly on the LOD meant such a set existed in the scene, exported
    fine, and appeared nowhere — which reads as "my selection was not created"."""
    cmds.file(new=True, force=True)
    plain = cmds.ls(cmds.polyCube(name="helmet_shell", ch=False)[0], long=True)[0]
    other = cmds.ls(cmds.polyCube(name="visor", ch=False)[0], long=True)[0]
    make_selection_set(plain, "a3ob_SEL_camo")
    make_selection_set(other, "a3ob_SEL_glass")

    check([i["name"] for i in selection_sets_for_owner(plain)] == ["a3ob_SEL_camo"],
          "an unmarked mesh lists its own set")
    check([i["name"] for i in selection_sets_for_owner(other)] == ["a3ob_SEL_glass"],
          "and only its own — meshes must not share")

    cmds.select(plain, replace=True)
    check(_selected_selection_owner() == plain,
          "selecting the mesh makes it the owner, got %r" % (_selected_selection_owner(),))

    # Selecting components of it resolves to the same owner, so picking faces to add to a
    # set does not blank the list it is being added to.
    shape = cmds.listRelatives(plain, shapes=True, fullPath=True)[0]
    cmds.select("%s.f[0]" % shape, replace=True)
    check(_selected_selection_owner() == plain,
          "a component belongs to its mesh, got %r" % (_selected_selection_owner(),))


def test_a_lod_still_wins_over_the_plain_mesh():
    """Marking it as a LOD must not split its selections into a second bucket."""
    cmds.file(new=True, force=True)
    lod = make_lod("helmet")
    make_selection_set(lod, "a3ob_SEL_camo")
    cmds.select(lod, replace=True)
    check(_selected_selection_owner() == lod, "the LOD is the owner")
    check([i["name"] for i in selection_sets_for_owner(lod)] == ["a3ob_SEL_camo"],
          "and the set made before marking is still listed against it")


def test_list_influences_is_silent():
    """The panel queries this on every click; a query must not talk."""
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    mesh = cmds.polySphere(name="not_a_dayz_mesh", ch=False)[0]
    cmds.select(mesh, replace=True)

    def listen(call):
        said = []
        callback = om1.MCommandMessage.addCommandOutputCallback(
            lambda message, message_type, data: said.append(message))
        try:
            result = call()
        finally:
            om1.MMessage.removeCallback(callback)
        return result, [line for line in said if "a3obInfluence" in line]

    # Positive control FIRST. Asserting silence is worthless unless this harness can hear
    # the command speak — a callback that never fires passes the silence check no matter
    # what the command does. An acting flag is what still speaks.
    _, control = listen(lambda: cmds.a3obInfluence(selectVertices="NoSuchBone"))
    check(control, "the output callback hears nothing at all — the silence check below "
                   "would pass vacuously")

    # Both spellings of the query: the dock uses the long one, and under interactive Maya
    # the two did not parse alike.
    for call, label in ((lambda: cmds.a3obInfluence(listInfluences=True), "listInfluences"),
                        (lambda: cmds.a3obInfluence(), "the bare form")):
        result, noise = listen(call)
        check(not result, "an unskinned mesh has no influences, got %r" % (result,))
        check(not noise, "%s must stay silent, said: %r" % (label, noise))


def test_lod_list_follows_the_scene():
    """Scene selection wins; the panel's own row is only the fallback."""
    check(_lod_list_target("|fromScene", "|fromPanel") == "|fromScene",
          "a LOD selected in the scene must move the list highlight")
    check(_lod_list_target(None, "|fromPanel") == "|fromPanel",
          "with nothing selected the list keeps the row it had")
    check(_lod_list_target(None, None) is None, "nothing to highlight")


def test_broken_panel_warns_once_not_on_repeat():
    """A dock panel that raises on refresh must warn exactly once per session.

    Two regressions guarded here:
    1. One broken panel was silently swallowing the error for ALL panels (the old single
       try/except around _refresh_dirty_panels) — now each panel is wrapped individually.
    2. Panels rebuild on every SelectionChanged, so a recurring error without dedup would
       flood the Script Editor — _warn_panel_once deduplicates by panel name.

    Positive control comes first: silence is meaningless without proof the callback works."""
    cmds.file(new=True, force=True)
    from a3ob.ui import dock as dock_module
    dock_module._dock_warned_panels.clear()

    said = []
    callback = om1.MCommandMessage.addCommandOutputCallback(
        lambda message, message_type, data: said.append(message))
    try:
        # Positive control: cmds.warning must reach the callback or the silence check
        # below would pass vacuously even if _warn_panel_once does nothing at all.
        cmds.warning("dock_test_panel_control_signal")
        check(any("dock_test_panel_control_signal" in m for m in said),
              "the output callback must hear cmds.warning — dedup check below would be vacuous")
        said.clear()

        # First call for "Validation" must warn.
        dock_module._warn_panel_once("Validation", RuntimeError("scene mid-edit"))
        validation_warnings = [m for m in said if "Validation" in m]
        check(len(validation_warnings) == 1,
              "first panel failure must warn once, got %d: %r" % (len(validation_warnings), validation_warnings))

        # Second call for the same panel must stay silent.
        dock_module._warn_panel_once("Validation", RuntimeError("same panel again"))
        validation_warnings = [m for m in said if "Validation" in m]
        check(len(validation_warnings) == 1,
              "repeated failure for the same panel must not re-warn, got %d" % len(validation_warnings))

        # A DIFFERENT panel still warns (dedup is per-panel, not global).
        dock_module._warn_panel_once("LODs", RuntimeError("different panel"))
        lod_warnings = [m for m in said if "LODs" in m]
        check(len(lod_warnings) == 1,
              "a different panel must still warn once, got %d: %r" % (len(lod_warnings), lod_warnings))
    finally:
        om1.MMessage.removeCallback(callback)
        dock_module._dock_warned_panels.clear()  # leave state clean for later tests


def main():
    test_selections_are_filtered_by_lod_node()
    test_legacy_named_orphan_still_surfaces()
    test_selections_show_on_a_mesh_that_is_not_a_lod_yet()
    test_a_lod_still_wins_over_the_plain_mesh()
    test_list_influences_is_silent()
    test_lod_list_follows_the_scene()
    test_broken_panel_warns_once_not_on_repeat()
    print("dock panel sync: OK")


if __name__ == "__main__":
    sys.exit(_harness.run(main))
