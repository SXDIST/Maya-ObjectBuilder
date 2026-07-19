"""Selecting the faces a DayZ material is assigned to (run with mayapy).

The Materials panel lists a mesh's shading groups; this is the "which faces are these?"
half. Two shapes the assignment can take, and both have to work:

* a per-face assignment, where the shading group's members are already components;
* a whole-object assignment, where the members are the SHAPE itself — the common case for
  a single-material LOD, and the one that returns no components at all unless expanded.

Scope is the meshes the panel is currently showing, not every mesh in the scene: clicking a
helmet's material must not select faces on the body standing next to it.

Run:  mayapy.exe tests/mayapy/material_faces.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.scene.materials import faces_with_material  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def shading_group(name):
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    return group


def face_count(components):
    return len(cmds.ls(components, flatten=True) or [])


def test_whole_object_assignment_expands_to_faces():
    """One material on the whole mesh: members are the shape, not components."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    members = cmds.sets(group, query=True) or []
    check(not any("." in m for m in members),
          "fixture is pointless unless the assignment is whole-object, got %r" % (members,))

    faces = faces_with_material([group], [shape])
    check(face_count(faces) == 6, "all six faces of the cube, got %r" % (faces,))
    check(all(".f[" in f for f in faces), "must be face components, got %r" % (faces,))


def test_per_face_assignment_returns_only_those_faces():
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    plate = shading_group("plate")
    cmds.sets("%s.f[0:1]" % shape, edit=True, forceElement=plate)

    faces = faces_with_material([plate], [shape])
    check(face_count(faces) == 2, "only the two assigned faces, got %r" % (faces,))


def test_other_meshes_are_not_dragged_in():
    """The same material on two meshes; scoped to one, only that one answers."""
    cmds.file(new=True, force=True)
    helmet = cmds.polyCube(name="helmet", ch=False)[0]
    body = cmds.polyCube(name="body", ch=False)[0]
    helmet_shape = cmds.listRelatives(helmet, shapes=True, fullPath=True)[0]
    group = shading_group("shared")
    cmds.sets([helmet, body], edit=True, forceElement=group)

    faces = faces_with_material([group], [helmet_shape])
    check(face_count(faces) == 6, "only the scoped mesh's faces, got %r" % (faces,))
    check(all("body" not in f for f in faces),
          "the unscoped mesh must not appear, got %r" % (faces,))


def test_nothing_assigned_is_empty_not_an_error():
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    empty = shading_group("unused")
    check(faces_with_material([empty], [shape]) == [], "an unused material selects nothing")
    check(faces_with_material([], [shape]) == [], "no material selects nothing")


def test_the_skinclusters_orig_shape_is_not_selected():
    """A skinned mesh keeps a hidden `...ShapeOrig`, and members name the TRANSFORM.

    Measured on a real garment: picking one material selected 4922 faces where the mesh has
    2461 — every face twice, once on the deformed shape and once on the intermediate one.
    A member reads `jacket.f[11143:13603]`, so resolving that transform to "its mesh shapes"
    hands back the orig shape as well. Those components are not pickable in the viewport and
    mean nothing downstream.

    The assignment has to be written through the transform for this to reproduce: assigning
    the mesh object itself stores the shape, which resolves to exactly one thing and hides
    the bug."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="jacket", ch=False)[0]
    cmds.select(clear=True)
    joint = cmds.joint(position=(0, 0, 0), name="Spine")
    cmds.skinCluster(joint, mesh, toSelectedBones=True)

    shapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
    intermediates = [s for s in shapes if cmds.getAttr(s + ".intermediateObject")]
    check(intermediates, "the fixture needs a skinCluster orig shape, got %r" % (shapes,))

    group = shading_group("armour")
    cmds.sets("%s.f[0:5]" % mesh, edit=True, forceElement=group)
    check(any("Orig" not in m and "|" not in m for m in cmds.sets(group, query=True) or []),
          "the fixture must store the member through the transform, got %r"
          % (cmds.sets(group, query=True),))

    cmds.select(mesh, replace=True)
    from a3ob.ui.scene.materials import _mesh_shapes_from_selection
    faces = faces_with_material([group], _mesh_shapes_from_selection())
    check(face_count(faces) == 6,
          "six faces, not twelve — the orig shape must not be counted, got %d %r"
          % (face_count(faces), faces))
    check(not any("Orig" in f for f in faces),
          "the intermediate shape must not be selected, got %r" % (faces,))


class FakeDock:
    """Stands in for the Qt dock: hands the action the highlighted material."""

    def __init__(self, item):
        self.item = item

    def selected_material_metadata_item(self):
        return self.item


def test_the_action_scopes_to_what_was_selected_when_it_ran():
    """The action replaces the selection, so it must read the scope BEFORE selecting.

    Reading it afterwards would scope the result to the action's own output — which looks
    correct on the first click and silently narrows on every repeat."""
    cmds.file(new=True, force=True)
    helmet = cmds.polyCube(name="helmet", ch=False)[0]
    body = cmds.polyCube(name="body", ch=False)[0]
    plate = shading_group("plate")
    cmds.sets("%s.f[0:1]" % helmet, edit=True, forceElement=plate)
    cmds.sets("%s.f[0:3]" % body, edit=True, forceElement=plate)

    # Patch the module that CALLS it: `_active_qt_dock` is star-imported, so a3ob.ui.entry
    # holds a different binding than the one the action actually resolves.
    from a3ob.ui.actions import materials as action
    action._active_qt_dock = lambda: FakeDock(
        {"shading_groups": [plate], "material_node": "plate"})

    cmds.select(helmet, replace=True)
    first = action.select_faces_with_material()
    check(first == 2, "the helmet's two assigned faces, got %r" % (first,))
    check(all("body" not in item for item in cmds.ls(selection=True, long=True) or []),
          "the body shares the material but was never in scope")

    # Repeat on the action's own output: still the same two faces, not a shrinking subset.
    second = action.select_faces_with_material()
    check(second == 2, "clicking again must be stable, got %r" % (second,))


def main():
    test_whole_object_assignment_expands_to_faces()
    test_per_face_assignment_returns_only_those_faces()
    test_other_meshes_are_not_dragged_in()
    test_nothing_assigned_is_empty_not_an_error()
    test_the_skinclusters_orig_shape_is_not_selected()
    test_the_action_scopes_to_what_was_selected_when_it_ran()
    print("material faces: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
