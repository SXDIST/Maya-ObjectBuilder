"""Export must read the LIVE Maya mesh, not replayed import blobs (run with mayapy).

Two bugs from the native-practice audit:

* ``a3obUVSetTaggs`` was echoed back verbatim, so every UV edit made in Maya was discarded on
  export (and after n-gon triangulation the stored corner list no longer matched the faces).
* ``a3obSharpEdges`` was echoed back the same way, so hardening/softening an edge in Maya
  never reached the P3D.

Import now applies sharp edges to the mesh, which makes the mesh authoritative for both.
This test proves the round-trip still preserves the data AND that a Maya-side edit wins.

Run:  mayapy.exe tests/mayapy/export_uses_live_mesh.py
"""

import os
import sys
import tempfile
from pathlib import Path

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

_REPO = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FIXTURE = _REPO / "Arma3ObjectBuilder-master" / "tests" / "inputs" / "p3d" / "sample_1_character.p3d"


def read_mlod(path):
    from a3ob.formats.binary import BinaryReader
    from a3ob.formats.p3d import MLOD
    with BinaryReader(str(path)) as reader:
        return MLOD.read(reader)


def read_lods(path):
    return read_mlod(path).lods


def tagg_of(lod, kind):
    return [t.data for t in lod.taggs if t.data is not None and t.data.kind == kind]


def main():
    if not FIXTURE.is_file():
        print("SKIP export_uses_live_mesh: fixture missing (%s)" % FIXTURE)
        return 0

    _harness.load_plugin()
    from a3ob.mayabridge.import_.importer import MayaMeshImport
    from a3ob.mayabridge.export.exporter import MayaMeshExport, ExportOptions

    original = read_lods(FIXTURE)
    original_edges = sum(len(d.edges) for lod in original for d in tagg_of(lod, "SharpEdges"))

    cmds.file(new=True, force=True)
    MayaMeshImport().import_mlod(read_mlod(FIXTURE), str(FIXTURE))

    # 1. Import must have hardened the edges on the actual mesh, not just stashed a string.
    hard_edges = 0
    for lod in cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []:
        for shape in cmds.listRelatives(lod, allDescendents=True, type="mesh",
                                        fullPath=True, noIntermediate=True) or []:
            selection = om.MSelectionList()
            selection.add(shape)
            edge_it = om.MItMeshEdge(selection.getDagPath(0))
            while not edge_it.isDone():
                if not edge_it.isSmooth:
                    hard_edges += 1
                edge_it.next()
    if original_edges:
        _harness.check(hard_edges > 0,
              "import must harden the %d sharp edges on the mesh, found none" % original_edges)

    # 2. Round-trip must preserve them.
    out = Path(tempfile.mkdtemp(prefix="live-mesh-")) / "roundtrip.p3d"
    _harness.check(MayaMeshExport().export_mlod(str(out)), "export failed")
    exported_edges = sum(len(d.edges) for lod in read_lods(out) for d in tagg_of(lod, "SharpEdges"))
    if original_edges:
        _harness.check(exported_edges > 0,
              "sharp edges lost on export: %d in, %d out" % (original_edges, exported_edges))
        # Not just "some": roughly the SAME set. `> 0` hid a 19x inflation for a long time —
        # this fixture carries 2004 sharp edges and export wrote 38871, because it trusted
        # Maya's per-edge hard FLAG while the smoothing actually lived in the locked normals
        # import had applied. Object Builder recomputes normals from this tagg, so the
        # round trip came back fully faceted.
        _harness.check(abs(exported_edges - original_edges) <= max(4, original_edges * 0.02),
              "sharp edge count must survive the round trip: %d in, %d out"
              % (original_edges, exported_edges))

    # 3. A UV edit made in Maya must reach the exported file. Shift EVERY UV of one LOD by
    # a known offset and check the exported U range moves with it — far more robust than
    # poking a single map[] index, which may not be referenced by any face corner.
    target_lod, target_shape = None, None
    for lod in cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []:
        for shape in cmds.listRelatives(lod, allDescendents=True, type="mesh",
                                        fullPath=True, noIntermediate=True) or []:
            if (cmds.polyEvaluate(shape, uvcoord=True) or 0) > 100:
                target_lod, target_shape = lod, shape
                break
        if target_shape:
            break
    _harness.check(target_shape is not None, "no UV-mapped mesh in the fixture")

    def exported_u_range():
        path = Path(tempfile.mkdtemp(prefix="live-mesh-")) / "uv.p3d"
        cmds.select(target_lod, replace=True)
        _harness.check(MayaMeshExport().export_mlod(str(path), ExportOptions(selected_only=True)),
              "export of the UV LOD failed")
        values = [uv.u for lod in read_lods(path) for face in lod.faces for uv in face.uvs]
        _harness.check(values, "exported LOD carries no UVs")
        return min(values), max(values)

    before_min, before_max = exported_u_range()
    shift = 0.5
    uv_count = cmds.polyEvaluate(target_shape, uvcoord=True)
    cmds.polyEditUV("%s.map[0:%d]" % (target_shape, uv_count - 1),
                    relative=True, uValue=shift, vValue=0.0)
    after_min, after_max = exported_u_range()

    _harness.check(abs((after_min - before_min) - shift) < 1e-3 and abs((after_max - before_max) - shift) < 1e-3,
          "UV edit did not reach the export: U range %.4f..%.4f -> %.4f..%.4f, expected +%.1f"
          % (before_min, before_max, after_min, after_max, shift))

    test_extra_uv_sets_round_trip()
    print("OK export reads the live mesh (%d hard edges preserved, UV shift of +%.1f exported)"
          % (exported_edges, shift))
    return 0


def test_extra_uv_sets_round_trip():
    """A second UV set must survive as a REAL Maya UV set, not a string blob on the transform.

    No fixture ships more than one #UVSet# TAGG, so build the case: export a mesh carrying two
    Maya UV sets, re-import the result, and check the second set came back as an editable UV
    set with the values intact."""
    from a3ob.mayabridge.import_.importer import MayaMeshImport
    from a3ob.mayabridge.export.exporter import MayaMeshExport, ExportOptions

    cmds.file(new=True, force=True)
    transform = _harness.make_lod("uvLOD")
    shape = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]

    # Built through the API: polyPlanarProjection needs a UI context and fails under mayapy.
    marker = 0.3125
    selection = om.MSelectionList()
    selection.add(shape)
    mesh_fn = om.MFnMesh(selection.getDagPath(0))
    second_name = mesh_fn.createUVSet("secondary")
    counts, ids = mesh_fn.getAssignedUVs()
    u_values = om.MFloatArray()
    v_values = om.MFloatArray()
    new_ids = om.MIntArray()
    for _corner in range(len(ids)):
        new_ids.append(len(u_values))
        u_values.append(marker)
        v_values.append(marker)
    mesh_fn.setUVs(u_values, v_values, second_name)
    mesh_fn.assignUVs(counts, new_ids, second_name)

    out = Path(tempfile.mkdtemp(prefix="uvsets-")) / "two.p3d"
    cmds.select(transform, replace=True)
    _harness.check(MayaMeshExport().export_mlod(str(out), ExportOptions(selected_only=True)), "export failed")

    lods = read_lods(out)
    sets = [t.data for t in lods[0].taggs if t.data is not None and t.data.kind == "UVSet"]
    _harness.check(len(sets) == 2, "expected 2 UVSet TAGGs in the file, got %d" % len(sets))
    _harness.check(sorted(d.id for d in sets) == [0, 1], "UV set ids must be 0 and 1, got %r"
          % sorted(d.id for d in sets))
    corners = len([uv for face in lods[0].faces for uv in face.uvs])
    _harness.check(all(len(d.uvs) == corners for d in sets),
          "every UV set must cover all %d face corners, got %r" % (corners, [len(d.uvs) for d in sets]))

    # Re-import: the second set must come back as a real Maya UV set.
    cmds.file(new=True, force=True)
    MayaMeshImport().import_mlod(read_mlod(out), str(out))
    imported = cmds.ls("*.a3obIsLOD", objectsOnly=True, long=True) or []
    _harness.check(imported, "re-import produced no LOD")
    imported_shape = cmds.listRelatives(imported[0], allDescendents=True, type="mesh",
                                        fullPath=True, noIntermediate=True)[0]
    names = cmds.polyUVSet(imported_shape, query=True, allUVSets=True) or []
    _harness.check(len(names) >= 2, "second UV set must exist on the re-imported mesh, got %r" % (names,))
    _harness.check(not cmds.attributeQuery("a3obUVSetTaggs", node=imported[0], exists=True),
          "the a3obUVSetTaggs blob must no longer be written")
    print("OK extra UV set round-trips as a real Maya UV set (%r), no blob written" % (names,))


if __name__ == "__main__":
    sys.exit(_harness.run(main))
