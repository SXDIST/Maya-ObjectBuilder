"""Correctness regressions for a3ob* commands (run with mayapy).

Covers two bugs found in the native-practice audit:

1. ``a3obSetMaterial`` assigned the shader at OBJECT level whenever the selection contained
   the transform alongside the faces, because it passed the raw ``cmds.ls(selection=True)``
   to ``forceElement`` instead of the component list it had already resolved.
2. ``mass_values_for_lod`` sized its list from the Maya vertex count but filled it from
   ``a3obMassValues``, which is stored in P3D source-vertex order. Whenever import remapped
   vertices the two index spaces disagreed and masses silently landed on wrong vertices.

Run:  mayapy.exe tests/mayapy/command_correctness.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402


def test_material_stays_face_level():
    transform = _harness.make_lod("matLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]

    # The transform is selected TOGETHER with the faces — this is what triggered the bug.
    cmds.select([transform, "%s.f[0]" % shape, "%s.f[1]" % shape], replace=True)
    cmds.a3obSetMaterial(texture="ca\\dayz\\test_co.paa", material="ca\\dayz\\test.rvmat")

    # listConnections repeats a shading engine once per connected component.
    groups = sorted({s for s in cmds.listConnections(shape, type="shadingEngine") or []
                     if s != "initialShadingGroup"})
    _harness.check(len(groups) == 1, "expected exactly one new shading group, got %r" % (groups,))
    members = cmds.sets(groups[0], query=True) or []
    _harness.check(members, "the new shading group has no members")

    # Every member must be a face component, never the bare shape/transform.
    for member in members:
        _harness.check(".f[" in member,
              "shader was assigned at object level: %r in %r" % (member, members))
    faces = set(cmds.ls(members, flatten=True) or [])
    _harness.check(len(faces) == 2,
          "expected the 2 selected faces to be assigned, got %d: %r" % (len(faces), sorted(faces)))
    print("OK a3obSetMaterial assigns at face level even with the transform selected")


def test_mass_uses_maya_index_space():
    from a3ob.mayabridge.commands.helpers.sets import mass_values_for_lod

    transform = _harness.make_lod("massLOD")
    vertex_count = cmds.polyEvaluate(transform, vertex=True)

    # A stored mass list SHORTER than the mesh (what a remapped import leaves behind).
    cmds.addAttr(transform, longName="a3obMassValues", dataType="string")
    cmds.setAttr(transform + ".a3obMassValues", "1;2;3", type="string")

    import maya.api.OpenMaya as om
    selection = om.MSelectionList()
    selection.add(transform)
    values = mass_values_for_lod(selection.getDependNode(0), 0.0)

    _harness.check(len(values) == vertex_count,
          "mass list must cover every Maya vertex: %d values for %d verts"
          % (len(values), vertex_count))
    _harness.check(values[:3] == [1.0, 2.0, 3.0],
          "stored masses must keep their order, got %r" % (values[:3],))
    _harness.check(all(v == 0.0 for v in values[3:]),
          "unset vertices must default to 0.0, got %r" % (values[3:],))
    print("OK mass values cover the vertex count (%d verts)" % vertex_count)


def test_mass_follows_source_vertex_remap():
    """Masses are stored in P3D source-vertex order (that is what import writes and export
    reads), so setting a mass on a Maya vertex must land on ITS source slot, not on the slot
    with the same ordinal. Without the remap the two spaces silently disagree."""
    from a3ob.mayabridge.commands.helpers.sets import set_selected_mass_values

    transform = _harness.make_lod("remapLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
    vertex_count = cmds.polyEvaluate(transform, vertex=True)

    # Reversed mapping: Maya vertex i corresponds to P3D source vertex (count - 1 - i).
    mapping = list(range(vertex_count - 1, -1, -1))
    cmds.addAttr(transform, longName="a3obVertexSourceIndices", dataType="string")
    cmds.setAttr(transform + ".a3obVertexSourceIndices",
                 ";".join(str(i) for i in mapping), type="string")
    cmds.addAttr(transform, longName="a3obSourceVertexCount", attributeType="long")
    cmds.setAttr(transform + ".a3obSourceVertexCount", vertex_count)
    cmds.addAttr(transform, longName="a3obMassValues", dataType="string")
    cmds.setAttr(transform + ".a3obMassValues", "", type="string")
    cmds.addAttr(transform, longName="a3obHasMass", attributeType="bool")

    import maya.api.OpenMaya as om
    selection = om.MSelectionList()
    selection.add(transform)
    lod_obj = selection.getDependNode(0)

    cmds.select("%s.vtx[0]" % shape, replace=True)
    _harness.check(set_selected_mass_values(lod_obj, 5.0), "setting mass on vtx[0] must succeed")

    stored = [float(v) for v in cmds.getAttr(transform + ".a3obMassValues").split(";") if v]
    expected_slot = mapping[0]
    _harness.check(len(stored) == vertex_count,
          "stored masses must cover every source vertex: %d for %d" % (len(stored), vertex_count))
    _harness.check(stored[expected_slot] == 5.0,
          "mass for Maya vtx[0] must land in source slot %d, got %r" % (expected_slot, stored))
    _harness.check(sum(1 for v in stored if v == 5.0) == 1,
          "exactly one slot may carry the mass, got %r" % (stored,))
    print("OK masses follow the source-vertex remap (Maya vtx[0] -> source %d)" % expected_slot)


def main():
    _harness.load_plugin()
    test_material_stays_face_level()
    test_mass_uses_maya_index_space()
    test_mass_follows_source_vertex_remap()


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
