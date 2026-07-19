"""#SharpEdges# must agree with the normals the same file carries (run with mayapy).

Maya keeps two independent notions of smoothing: the per-edge soft/hard FLAG, and locked
custom per-face-vertex NORMALS. When a mesh has locked normals, those are what Maya renders
and what the exported P3D shades with — the edge flag is stale bookkeeping.

Measured on a real DayZ jacket that arrived through FBX: 38131 edges, every one flagged
hard, ZERO soft, alongside 40812 locked normals that are smooth. The viewport looked
correct; export wrote "smooth normals AND every edge sharp" into the same LOD, and Object
Builder — which uses the tagg to recompute normals — showed the whole garment faceted.

So sharpness is decided by the normals: an edge is sharp when the two faces meeting at it
actually disagree about the normal. An edge with only one face has nothing to shade across
and is not written at all (35534 of the jacket's edges were of that kind).

Run:  mayapy.exe tests/mayapy/sharp_edges_follow_normals.py
"""

import os
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402
import maya.api.OpenMaya as om  # noqa: E402

from a3ob.formats.p3d import MLOD  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def new_scene():
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)


def mark_lod(transform):
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    return cmds.ls(transform, long=True)[0]


def interior_edges(shape):
    """Edge ids with two adjacent faces. A plane's border edges have one and can never be
    softened, so a fixture that says "harden one edge" has to name the interior one."""
    selection = om.MSelectionList()
    selection.add(shape)
    edge_it = om.MItMeshEdge(selection.getDagPath(0))
    found = []
    while not edge_it.isDone():
        if len(edge_it.getConnectedFaces()) == 2:
            found.append(edge_it.index())
        edge_it.next()
    return found


def hard_interior_edges(shape):
    selection = om.MSelectionList()
    selection.add(shape)
    edge_it = om.MItMeshEdge(selection.getDagPath(0))
    count = 0
    while not edge_it.isDone():
        if len(edge_it.getConnectedFaces()) == 2 and not edge_it.isSmooth:
            count += 1
        edge_it.next()
    return count


def edge_flags(shape):
    selection = om.MSelectionList()
    selection.add(shape)
    edge_it = om.MItMeshEdge(selection.getDagPath(0))
    hard = soft = 0
    while not edge_it.isDone():
        if edge_it.isSmooth:
            soft += 1
        else:
            hard += 1
        edge_it.next()
    return hard, soft


def exported_sharp_edges(lod_transform, name):
    from a3ob.mayabridge.export.exporter import MayaMeshExport, ExportOptions

    path = os.path.join(tempfile.gettempdir(), name)
    cmds.select(lod_transform, replace=True)
    check(MayaMeshExport().export_mlod(path, ExportOptions(selected_only=True)),
          "export failed for %s" % lod_transform)
    mlod = MLOD.read_file(path)
    return sum(len(tagg.data.edges) for lod in mlod.lods for tagg in lod.taggs
               if tagg.name == "#SharpEdges#")


def test_locked_smooth_normals_beat_a_stale_hard_flag():
    """The jacket's exact state: every edge flagged hard, normals locked smooth."""
    new_scene()
    mesh = cmds.polySphere(name="garment", subdivisionsX=12, subdivisionsY=12, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]

    cmds.polySoftEdge(mesh, angle=180, ch=False)              # smooth normals
    cmds.polyNormalPerVertex(mesh, freezeNormal=True)          # lock them
    cmds.polySoftEdge(mesh, angle=0, ch=False)                 # flag every edge hard

    hard, soft = edge_flags(shape)
    check(soft == 0 and hard > 0,
          "the fixture must reproduce all-hard flags, got %d hard / %d soft" % (hard, soft))

    # ... while the normals themselves stayed smooth: adjacent faces still agree.
    fn = om.MFnMesh(om.MSelectionList().add(shape).getDagPath(0))
    check(fn.getFaceVertexNormal(0, fn.getPolygonVertices(0)[0]).length() > 0, "normals exist")

    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_locked.p3d")
    check(written == 0,
          "smooth locked normals must not export as sharp edges, got %d" % written)


def test_a_genuinely_hard_edge_is_still_written():
    """The control: without locked normals a hard edge really does split the shading."""
    new_scene()
    mesh = cmds.polyCube(name="crate", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(mesh, angle=0, ch=False)

    hard, soft = edge_flags(shape)
    check(soft == 0 and hard == 12, "a cube has 12 edges, all hard, got %d/%d" % (hard, soft))

    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_cube.p3d")
    check(written == 12, "every faceted edge of the cube must be written, got %d" % written)


def test_hand_hardened_edges_with_unlocked_normals_round_trip():
    """The normal authoring case: no locked normals, the modeller hardens edges by hand.

    With unlocked normals Maya derives them from the flags — a hardened edge gives each face
    its own face normal at the shared vertices, a soft one gives the average. So the
    normal-based rule reproduces the hand-set flags exactly, without consulting them."""
    new_scene()
    mesh = cmds.polySphere(name="hand", subdivisionsX=8, subdivisionsY=8, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(mesh, angle=180, ch=False)          # start fully smooth

    picked = ["%s.e[%d]" % (shape, i) for i in range(0, 40, 4)]
    cmds.polySoftEdge(picked, angle=0, ch=False)          # harden a known handful

    locked = cmds.polyNormalPerVertex(shape + ".vtx[*]", query=True, freezeNormal=True) or []
    check(not any(locked), "this case is about UNLOCKED normals")
    hard, _soft = edge_flags(shape)
    check(hard == len(picked), "expected %d hand-hardened edges, got %d" % (len(picked), hard))

    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_hand.p3d")
    check(written == hard,
          "every hand-hardened edge must be exported: %d hardened, %d written"
          % (hard, written))


def test_a_shallow_but_real_crease_is_kept():
    """Sharpness is not an angle threshold — a barely-bent hardened edge still counts."""
    new_scene()
    mesh = cmds.polyPlane(name="crease", subdivisionsX=2, subdivisionsY=1, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    # Lift one row of vertices a hair: a dihedral far below any "hard edge" angle preset.
    cmds.move(0, 0.0005, 0, "%s.vtx[1]" % shape, "%s.vtx[4]" % shape, relative=True)
    cmds.polySoftEdge(mesh, angle=180, ch=False)
    inner = interior_edges(shape)
    check(len(inner) == 1, "a 2x1 plane has one interior edge, got %r" % (inner,))
    cmds.polySoftEdge("%s.e[%d]" % (shape, inner[0]), angle=0, ch=False)
    check(hard_interior_edges(shape) == 1, "that edge must now be hard")

    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_shallow.p3d")
    check(written == 1, "a shallow crease is still a crease, got %d" % written)


def test_coplanar_hardened_edge_with_unlocked_normals_is_kept():
    """Even a flat hardened edge survives, because the flag is the only thing that has it.

    Nothing about the geometry or the normals distinguishes this edge, so a normals-only
    rule would drop it. With normals unlocked the flag IS the authoring, and dropping a
    deliberate hard edge because it happens to be flat would be losing the user's work."""
    new_scene()
    mesh = cmds.polyPlane(name="flat", subdivisionsX=2, subdivisionsY=1, ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(mesh, angle=180, ch=False)
    inner = interior_edges(shape)
    cmds.polySoftEdge("%s.e[%d]" % (shape, inner[0]), angle=0, ch=False)  # hard, but flat
    check(hard_interior_edges(shape) == 1,
          "the fixture needs one hardened coplanar edge, got %d" % hard_interior_edges(shape))
    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_coplanar.p3d")
    check(written == 1, "a hand-set hard edge is kept even when flat, got %d" % written)


def test_locked_normals_that_really_differ_are_still_written():
    """The other half of the locked case: locked normals that DO disagree stay sharp."""
    new_scene()
    mesh = cmds.polyCube(name="crate", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    cmds.polySoftEdge(mesh, angle=0, ch=False)          # faceted
    cmds.polyNormalPerVertex(mesh, freezeNormal=True)    # ... and locked that way

    locked = cmds.polyNormalPerVertex(shape + ".vtx[*]", query=True, freezeNormal=True) or []
    check(any(locked), "the fixture needs locked normals")
    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_lockedhard.p3d")
    check(written == 12, "a locked-faceted cube keeps all 12 edges, got %d" % written)


def test_a_smooth_mesh_writes_nothing():
    new_scene()
    mesh = cmds.polySphere(name="ball", ch=False)[0]
    cmds.polySoftEdge(mesh, angle=180, ch=False)
    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_smooth.p3d")
    check(written == 0, "a fully smooth mesh has no sharp edges, got %d" % written)


def test_open_border_edges_are_not_sharp():
    """A border edge has no second face to disagree with — writing it says nothing."""
    new_scene()
    mesh = cmds.polyPlane(name="patch", subdivisionsX=1, subdivisionsY=1, ch=False)[0]
    cmds.polySoftEdge(mesh, angle=0, ch=False)   # all four borders flagged hard
    shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
    hard, _soft = edge_flags(shape)
    check(hard == 4, "the fixture needs four hard border edges, got %d" % hard)

    written = exported_sharp_edges(mark_lod(mesh), "a3ob_sharp_border.p3d")
    check(written == 0, "border edges must not be exported as sharp, got %d" % written)


def main():
    test_locked_smooth_normals_beat_a_stale_hard_flag()
    test_a_genuinely_hard_edge_is_still_written()
    test_hand_hardened_edges_with_unlocked_normals_round_trip()
    test_a_shallow_but_real_crease_is_kept()
    test_coplanar_hardened_edge_with_unlocked_normals_is_kept()
    test_locked_normals_that_really_differ_are_still_written()
    test_a_smooth_mesh_writes_nothing()
    test_open_border_edges_are_not_sharp()
    print("sharp edges follow normals: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
