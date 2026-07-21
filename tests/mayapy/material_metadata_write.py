"""Writing DayZ material metadata without a dock (run with mayapy).

Phase 3d retires the Materials dock panel; per-material editing moves into the Attribute
Editor, which has no dock to read `dock.material_texture_path()` / `dock.selected_material_
metadata_item()` from. This tests the dock-free replacements directly:
``write_material_metadata(node, texture, material)`` and
``select_faces_for_shading_group(shading_group)``.

Reuses the shading-group fixture shape from ``tests/mayapy/material_faces.py`` so the two
files stay consistent. No dock is built here — a real QWidget under mayapy segfaults with no
traceback unless a QApplication exists before ``maya.standalone.initialize()``, and these two
functions are dock-free by design, so building one would defeat the point of the test.

Run:  mayapy.exe tests/mayapy/material_metadata_write.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.actions.materials import (  # noqa: E402
    write_material_metadata,
    select_faces_for_shading_group,
)


def shading_group(name):
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    return shader, group


def test_writing_sets_both_attributes_on_the_shading_group():
    """A shading engine with a3obTexture/a3obMaterial takes the normalised values."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    written = write_material_metadata(group, r"P:\data\helmet_co.paa", r"P:\data\helmet.rvmat")
    _harness.check(group in written, "the shading group itself must be a written target, got %r" % (written,))
    _harness.check(cmds.getAttr(group + ".a3obTexture") == "data\\helmet_co.paa",
                    "texture attr wrong: %r" % (cmds.getAttr(group + ".a3obTexture"),))
    _harness.check(cmds.getAttr(group + ".a3obMaterial") == "data\\helmet.rvmat",
                    "material attr wrong: %r" % (cmds.getAttr(group + ".a3obMaterial"),))


def test_paths_are_normalised_on_the_way_in():
    """Forward slashes and a drive letter become the backslash form DayZ stores —
    _normalize_dayz_path is the single definition and must still be the one applied."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    write_material_metadata(group, "P:/data/helmet_co.paa", "p:/data/helmet.rvmat")
    _harness.check(cmds.getAttr(group + ".a3obTexture") == "data\\helmet_co.paa",
                    "forward slashes / drive letter must be normalised, got %r"
                    % (cmds.getAttr(group + ".a3obTexture"),))
    _harness.check(cmds.getAttr(group + ".a3obMaterial") == "data\\helmet.rvmat",
                    "forward slashes / drive letter must be normalised, got %r"
                    % (cmds.getAttr(group + ".a3obMaterial"),))


def test_the_material_node_and_sibling_shading_groups_also_receive_it():
    """The panel wrote to every target, not just the one shading group; the AE must not
    quietly narrow that."""
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    other_mesh = cmds.polyCube(name="visor", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    # A second shading engine sharing the SAME shader — the sibling the fan-out must reach.
    sibling = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="armourSiblingSG")
    cmds.connectAttr(shader + ".outColor", sibling + ".surfaceShader", force=True)
    cmds.sets(other_mesh, edit=True, forceElement=sibling)

    written = write_material_metadata(group, r"P:\data\helmet_co.paa", r"P:\data\helmet.rvmat")

    _harness.check(group in written, "the shading group passed in must be written, got %r" % (written,))
    _harness.check(shader in written, "the material node must be written, got %r" % (written,))
    _harness.check(sibling in written, "the sibling shading engine on the same material must be written, got %r" % (written,))
    for node in (shader, sibling):
        _harness.check(cmds.getAttr(node + ".a3obTexture") == "data\\helmet_co.paa",
                        "%s did not receive the texture path" % (node,))
        _harness.check(cmds.getAttr(node + ".a3obMaterial") == "data\\helmet.rvmat",
                        "%s did not receive the material path" % (node,))

    # And passing the MATERIAL node instead of the shading group must reach the identical
    # fan-out (this is the shape the panel's cached item dict actually prefers: see
    # `_persist_selected_material_metadata`'s wrapper, which passes `material_node` first).
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    other_mesh = cmds.polyCube(name="visor", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)
    sibling = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="armourSiblingSG")
    cmds.connectAttr(shader + ".outColor", sibling + ".surfaceShader", force=True)
    cmds.sets(other_mesh, edit=True, forceElement=sibling)

    written_from_material = write_material_metadata(shader, r"P:\data\helmet_co.paa", r"P:\data\helmet.rvmat")
    _harness.check(written_from_material == written,
                    "starting from the material node must reach the same targets as starting "
                    "from the shading group, got %r vs %r" % (written_from_material, written))


def test_a_deleted_target_reports_nothing_written_rather_than_raising():
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)
    cmds.delete(group)
    cmds.delete(shader)

    written = write_material_metadata("armourSG", r"P:\data\helmet_co.paa", r"P:\data\helmet.rvmat")
    _harness.check(written == set(), "a deleted target must report nothing written, got %r" % (written,))


def test_selecting_faces_returns_the_count_and_selects_them():
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, group = shading_group("armour")
    cmds.sets(mesh, edit=True, forceElement=group)

    cmds.select(mesh, replace=True)
    count = select_faces_for_shading_group(group)
    _harness.check(count == 6, "all six faces of the cube, got %r" % (count,))
    selected = cmds.ls(selection=True, flatten=True) or []
    _harness.check(len(selected) == 6, "the faces must actually be selected, got %r" % (selected,))
    _harness.check(all(".f[" in item for item in selected),
                    "must be face components, got %r" % (selected,))


def test_selecting_faces_on_an_unassigned_material_selects_nothing_and_warns():
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="helmet", ch=False)[0]
    shader, unused = shading_group("unused")

    cmds.select(mesh, replace=True)
    count = select_faces_for_shading_group(unused)
    _harness.check(count == 0, "an unused material must select nothing, got %r" % (count,))


def main():
    test_writing_sets_both_attributes_on_the_shading_group()
    test_paths_are_normalised_on_the_way_in()
    test_the_material_node_and_sibling_shading_groups_also_receive_it()
    test_a_deleted_target_reports_nothing_written_rather_than_raising()
    test_selecting_faces_returns_the_count_and_selects_them()
    test_selecting_faces_on_an_unassigned_material_selects_nothing_and_warns()
    print("material metadata write: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
