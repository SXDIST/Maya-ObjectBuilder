"""QEM decimation invariants — pure Python, no Maya.

The decimator feeds MFnMesh.create() directly, so anything malformed it emits becomes
malformed Maya geometry. One invariant matters above the rest: the vertices it returns
and the vertices its faces reference must be the SAME set.

Neither direction is free. A returned vertex no face uses has no normal, and
`polyNormalPerVertex` segfaults Maya outright when it walks onto one — measured on a
real DayZ garment, where decimating past ~0.25 produced 5 such vertices and took the
whole session down with it. A face referencing a vertex that was not returned is a
dangling index, which is the same class of bug approached from the other side.

Run:  python tests/python/test_qem.py
"""

import importlib.util
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
except ImportError:  # pragma: no cover - numpy is an optional accelerator elsewhere
    print("SKIP test_qem: numpy not available")
    sys.exit(0)

# qem.py is Maya-free, but a3ob.ui.autolod.__init__ imports maya.cmds — so load the
# module straight from its path rather than through the package.
_QEM_PATH = os.path.join(_REPO, "scripts", "a3ob", "ui", "autolod", "qem.py")
_spec = importlib.util.spec_from_file_location("a3ob_qem_standalone", _QEM_PATH)
_qem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_qem)

decimate = _qem.decimate
decimate_chain = _qem.decimate_chain
_Decimator = _qem._Decimator


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def grid_mesh(side, extra_shells=0):
    """A triangulated grid, optionally with small detached shells beside it.

    The detached shells are the point. A DayZ garment is not one surface — it carries
    pouches, patches and buckles as separate islands. Decimating hard collapses a small
    island away entirely long before the overall face target is met, and its vertices
    stay behind attached to nothing. That is where the orphans came from on the real
    model; a single clean grid never produces one."""
    points = []
    for y in range(side):
        for x in range(side):
            # A little height noise keeps the quadrics from being perfectly degenerate.
            points.append([float(x), float(y), 0.05 * ((x * 7 + y * 13) % 5)])
    faces = []
    for y in range(side - 1):
        for x in range(side - 1):
            a = y * side + x
            b = a + 1
            c = a + side
            d = c + 1
            faces.append([a, b, c])
            faces.append([b, d, c])

    for shell in range(extra_shells):
        base = len(points)
        offset = float(side + 2 + shell * 2)
        points.append([offset, 0.0, 0.0])
        points.append([offset + 0.3, 0.0, 0.0])
        points.append([offset, 0.3, 0.0])
        points.append([offset + 0.3, 0.3, 0.05])
        faces.append([base, base + 1, base + 2])
        faces.append([base + 1, base + 3, base + 2])

    return np.array(points, dtype=np.float64), faces


def assert_vertex_face_sets_agree(points, faces, label):
    """The emitted vertices and the vertices the faces reference must be the SAME set.

    Both directions are load-bearing, and they fail differently:
      * emitted-but-unreferenced is an orphan point — no normal, and `polyNormalPerVertex`
        segfaults Maya on it;
      * referenced-but-not-emitted is a dangling index into the returned point array.
    `snapshot()` derives one from the other so neither can happen; this pins that."""
    emitted = set(range(len(points)))
    referenced = {index for face in faces for index in face}

    orphans = sorted(emitted - referenced)
    check(not orphans,
          "%s: %d emitted vertex(es) no face references — Maya segfaults on these: %r"
          % (label, len(orphans), orphans[:10]))

    dangling = sorted(referenced - emitted)
    check(not dangling,
          "%s: %d face index(es) reference a vertex that was not emitted: %r"
          % (label, len(dangling), dangling[:10]))


def assert_well_formed(points, faces, label):
    check(len(faces) > 0, "%s: decimated to nothing" % label)

    for face in faces:
        check(len(face) == 3, "%s: face is not a triangle: %r" % (label, face))
        check(len(set(face)) == 3, "%s: face repeats a vertex: %r" % (label, face))
        for index in face:
            check(0 <= index < len(points),
                  "%s: face index %d out of range (%d points)" % (label, index, len(points)))

    assert_vertex_face_sets_agree(points, faces, label)


def test_decimate_emits_no_orphans():
    points, faces = grid_mesh(24, extra_shells=6)
    for target in (800, 400, 200, 100, 50, 20, 10):
        out_points, out_faces, orig = decimate(points, faces, target)
        assert_well_formed(out_points, out_faces, "decimate(target=%d)" % target)
        check(len(orig) == len(out_faces),
              "orig_face_index must line up with the faces returned")
    print("OK decimate emits no orphan vertices at any target")


def test_chain_emits_no_orphans():
    points, faces = grid_mesh(24, extra_shells=6)
    targets = [800, 400, 200, 100, 50, 20, 10]
    chain = decimate_chain(points, faces, targets)
    check(set(chain) == set(targets), "every target must be snapshotted")
    for target, (out_points, out_faces, _orig) in sorted(chain.items()):
        assert_well_formed(out_points, out_faces, "decimate_chain(target=%d)" % target)
    print("OK decimate_chain emits no orphan vertices at any target")


def awkward_mesh():
    """A grid plus the topology that stresses the collapse bookkeeping.

    `snapshot()` can only stay consistent if `vfaces[b]` really does list every live face
    touching `b` when `run_to` retires `b`. The shapes that could plausibly break that
    accounting are all here: an edge shared by three faces (non-manifold), a face
    duplicated onto the same three vertices, a zero-area sliver, and a face that repeats a
    vertex — the last one also puts a self-edge `(x, x)` into the collapse heap."""
    points, faces = grid_mesh(10, extra_shells=2)
    points = list(points)

    base = len(points)
    points.append([2.0, 2.0, 2.5])          # apex fanning an existing interior edge
    faces.append([11, 12, base])            # third face on edge (11, 12) -> non-manifold
    faces.append([11, 12, 21])              # exact duplicate of an existing grid face
    faces.append([33, 34, 33])              # repeats a vertex -> self-edge in the heap

    base2 = len(points)
    points.append([-3.0, 0.0, 0.0])
    points.append([-3.0, 1.0, 0.0])
    points.append([-3.0, 2.0, 0.0])         # exactly collinear -> zero-area sliver
    faces.append([base2, base2 + 1, base2 + 2])

    return np.array(points, dtype=np.float64), faces


def test_awkward_topology_stays_consistent():
    points, faces = awkward_mesh()
    for target in (300, 150, 60, 20, 8, 4, 1):
        out_points, out_faces, orig = decimate(points, faces, target)
        assert_vertex_face_sets_agree(out_points, out_faces,
                                      "awkward decimate(target=%d)" % target)
        check(len(orig) == len(out_faces),
              "awkward decimate(target=%d): orig_face_index must line up" % target)
    print("OK non-manifold/degenerate topology keeps vertices and faces in step")


def test_live_face_never_references_a_retired_vertex():
    """The precondition that makes the KeyError unreachable, checked white-box.

    `snapshot()` renumbers from the surviving faces alone. That is only equivalent to the
    old `alive_v[i] and i in used` filter because `run_to` never leaves a live face
    pointing at a retired vertex. Assert it directly at every step, so a future edit to
    the `vfaces` bookkeeping is caught here rather than as a mangled LOD in Maya."""
    points, faces = awkward_mesh()
    decimator = _Decimator(points, faces)

    for target in (300, 150, 60, 20, 8, 4, 1):
        decimator.run_to(target)
        for face_index, face in enumerate(decimator.F):
            if not decimator.alive_f[face_index]:
                continue
            for vertex in face[:3]:
                check(decimator.alive_v[vertex],
                      "target=%d: live face %d %r references retired vertex %d"
                      % (target, face_index, face, vertex))
                check(face_index in decimator.vfaces[vertex],
                      "target=%d: vfaces[%d] has drifted — it is missing live face %d %r"
                      % (target, vertex, face_index, face))
    print("OK no live face ever references a retired vertex (vfaces stays in sync)")


def main():
    test_decimate_emits_no_orphans()
    test_chain_emits_no_orphans()
    test_awkward_topology_stays_consistent()
    test_live_face_never_references_a_retired_vertex()
    print("qem tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
