"""Selecting a material's faces resolved from the current selection (run with mayapy).

The in-AE Select Faces button died because `editorTemplate -callCustom` never fires from
inside the AETemplateCustomContent hook, and any raw UI built into that hook cannot re-point
when the AE switches nodes (it fires once per node type per tab) - a stored node goes stale
the instant the user selects a different material. The fix moves the action to the
MayaObjectBuilder menu and resolves its target from the CURRENT SELECTION at call time instead
of anything stored: a resolver that re-reads the selection has nothing to go stale.

Hypershade can select objects by a material, but never faces - this is the one thing it cannot
do on its own: select a shading engine, or the material feeding one, and get exactly the faces
it is painted onto, with no mesh needing to already be part of the selection.

Run:  mayapy.exe tests/mayapy/select_faces_from_selection.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.OpenMaya as om1  # noqa: E402 - API 1.0 has the command-output callback

from a3ob.ui.actions.materials import select_faces_for_selected_material  # noqa: E402


def shading_group(name):
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    return shader, group


def test_a_selected_shading_engine_resolves_to_itself():
    """Selecting the shadingEngine node directly selects its own faces - no mesh needs to be
    part of the selection, since Hypershade never puts one there."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    _shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    # noExpand: a plain cmds.select(group) selects the SET's MEMBERS, not the set node -
    # exactly the resolver must not do either, and the fixture must not do it by accident.
    cmds.select(group, replace=True, noExpand=True)
    result = select_faces_for_selected_material()

    _harness.check(result == 6, "all six faces of the cube, got %r" % (result,))
    selected = cmds.ls(selection=True, long=True) or []
    _harness.check(all(".f[" in item for item in selected),
          "must select face components, got %r" % (selected,))
    _harness.check(all("helmet" in item for item in selected),
          "must select the mesh the material is on, got %r" % (selected,))


def test_a_selected_material_resolves_to_its_shading_engine():
    """Selecting the MATERIAL node - what a Hypershade double-click actually opens in the
    Attribute Editor - must resolve to the shading engine it feeds."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    cmds.select(shader, replace=True)
    result = select_faces_for_selected_material()

    _harness.check(result == 6, "all six faces of the cube, got %r" % (result,))


def test_a_selection_with_no_material_warns_and_selects_nothing():
    """Selecting a plain mesh - neither a shadingEngine nor a material - must not select
    anything, and must warn rather than silently doing nothing.

    The docstring promises "0 and a warning" - asserting only the 0 leaves half the
    contract unpinned, since deleting the cmds.warning(...) call in
    select_faces_for_selected_material would still pass a result-only check. Captured
    the same way dock_panel_sync.py's test_list_influences_is_silent does: an API 1.0
    command-output callback, with a positive control BEFORE the real assertion so a
    listener that silently stopped working fails loudly instead of the check passing
    vacuously."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    cmds.select(mesh, replace=True)
    before = cmds.ls(selection=True, long=True) or []

    said = []
    callback = om1.MCommandMessage.addCommandOutputCallback(
        lambda message, message_type, data: said.append(message))
    try:
        # Positive control FIRST: prove the callback actually hears cmds.warning before
        # trusting it to have heard (or not heard) anything from the call under test.
        cmds.warning("select_faces_from_selection_control_signal")
        _harness.check(any("select_faces_from_selection_control_signal" in m for m in said),
              "the output callback hears nothing at all - the warning check below "
              "would pass vacuously")
        said[:] = []

        result = select_faces_for_selected_material()
    finally:
        om1.MMessage.removeCallback(callback)

    _harness.check(result == 0, "no material named, got %r" % (result,))
    after = cmds.ls(selection=True, long=True) or []
    _harness.check(after == before, "the selection must be left alone, got %r" % (after,))
    _harness.check(said, "select_faces_for_selected_material must warn when the "
                        "selection names no material, but nothing was said")


def test_the_faces_selected_are_the_ones_the_material_is_assigned_to():
    """Reuse material_faces.py's fixture shape; it already builds a shaded mesh.

    A per-face assignment - the shape where getting the scope wrong is easiest to hide, since
    a whole-object assignment expands to every face regardless of whether the scope was
    computed correctly."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    shader, plate = shading_group("plate")
    cmds.sets("%s.f[0:1]" % shape, edit=True, forceElement=plate)

    cmds.select(shader, replace=True)
    result = select_faces_for_selected_material()

    expected = set(cmds.ls("%s.f[0:1]" % shape, flatten=True, long=True) or [])
    got = set(cmds.ls(selection=True, flatten=True, long=True) or [])
    _harness.check(result == 2, "only the two assigned faces, got %r" % (result,))
    _harness.check(got == expected,
          "must be exactly the two assigned faces, got %r want %r" % (got, expected))


def test_a_selected_mesh_with_one_material_resolves_to_its_faces():
    """The natural gesture: select the mesh you can see. No Hypershade/AE detour needed -
    a mesh (or its transform) carrying exactly one DayZ shading engine resolves to it."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    _shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    cmds.select(mesh, replace=True)
    result = select_faces_for_selected_material()

    _harness.check(result == 6, "all six faces of the cube, got %r" % (result,))


def test_a_selected_face_component_resolves_to_its_material():
    """A face component is the natural disambiguator: it resolves to whatever shading
    engine is assigned to those specific faces, not to every material on the mesh."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    _shader, plate = shading_group("plate")
    cmds.sets("%s.f[0:1]" % shape, edit=True, forceElement=plate)

    cmds.select("%s.f[0:1]" % mesh, replace=True)
    result = select_faces_for_selected_material()

    expected = set(cmds.ls("%s.f[0:1]" % shape, flatten=True, long=True) or [])
    got = set(cmds.ls(selection=True, flatten=True, long=True) or [])
    _harness.check(result == 2,
          "the two faces the component selection named, got %r" % (result,))
    _harness.check(got == expected,
          "must be exactly those two faces, got %r want %r" % (got, expected))


def test_a_mesh_with_two_materials_warns_and_selects_nothing():
    """A mesh can carry more than one shading engine - there is no single right answer, so
    the resolver must refuse rather than guess. Captured with the same positive-control
    pattern as the no-material case above, so a silently-broken warning fails loudly."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    _shader1, plate = shading_group("plate")
    _shader2, chainmail = shading_group("chainmail")
    cmds.sets("%s.f[0:2]" % shape, edit=True, forceElement=plate)
    cmds.sets("%s.f[3:5]" % shape, edit=True, forceElement=chainmail)

    cmds.select(mesh, replace=True)
    before = cmds.ls(selection=True, long=True) or []

    said = []
    callback = om1.MCommandMessage.addCommandOutputCallback(
        lambda message, message_type, data: said.append(message))
    try:
        cmds.warning("select_faces_from_selection_control_signal")
        _harness.check(any("select_faces_from_selection_control_signal" in m for m in said),
              "the output callback hears nothing at all - the warning check below "
              "would pass vacuously")
        said[:] = []

        result = select_faces_for_selected_material()
    finally:
        om1.MMessage.removeCallback(callback)

    _harness.check(result == 0, "ambiguous - must select nothing, got %r" % (result,))
    after = cmds.ls(selection=True, long=True) or []
    _harness.check(after == before, "the selection must be left alone, got %r" % (after,))
    warned = " ".join(said)
    _harness.check("plate" in warned and "chainmail" in warned,
          "the warning must name both materials, got %r" % (said,))


def test_mesh_selection_does_not_widen_to_a_sharing_object():
    """Two meshes wear the same material; selecting only one must not pull the other in.
    Unlike the shading-engine/material case, a geometry selection IS the scope - rebuilding
    it from the material's full membership would silently widen the result."""
    cmds.file(new=True, force=True)
    helmet = cmds.polyCube(name="helmet", ch=False)[0]
    body = cmds.polyCube(name="body", ch=False)[0]
    _shader, shared = shading_group("shared")
    cmds.sets([helmet, body], edit=True, forceElement=shared)

    cmds.select(helmet, replace=True)
    result = select_faces_for_selected_material()

    _harness.check(result == 6, "only the selected mesh's six faces, got %r" % (result,))
    selected = cmds.ls(selection=True, long=True) or []
    _harness.check(all("body" not in item for item in selected),
          "the unselected sibling must not be dragged in, got %r" % (selected,))


def main():
    test_a_selected_shading_engine_resolves_to_itself()
    test_a_selected_material_resolves_to_its_shading_engine()
    test_a_selection_with_no_material_warns_and_selects_nothing()
    test_the_faces_selected_are_the_ones_the_material_is_assigned_to()
    test_a_selected_mesh_with_one_material_resolves_to_its_faces()
    test_a_selected_face_component_resolves_to_its_material()
    test_a_mesh_with_two_materials_warns_and_selects_nothing()
    test_mesh_selection_does_not_widen_to_a_sharing_object()
    print("select faces from selection: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
