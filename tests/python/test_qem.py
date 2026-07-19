"""QEM decimation invariants — pure Python, no Maya.

The decimator feeds MFnMesh.create() directly, so anything malformed it emits becomes
malformed Maya geometry. One invariant matters above the rest: every vertex it returns
must be used by at least one face. A vertex with no faces has no normal, and
`polyNormalPerVertex` segfaults Maya outright when it walks onto one — measured on a
real DayZ garment, where decimating past ~0.25 produced 5 such vertices and took the
whole session down with it.

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


def orphans_of(points, faces):
    """Indices of returned vertices that no face references."""
    used = {index for face in faces for index in face}
    return [i for i in range(len(points)) if i not in used]


def assert_well_formed(points, faces, label):
    check(len(faces) > 0, "%s: decimated to nothing" % label)

    for face in faces:
        check(len(face) == 3, "%s: face is not a triangle: %r" % (label, face))
        check(len(set(face)) == 3, "%s: face repeats a vertex: %r" % (label, face))
        for index in face:
            check(0 <= index < len(points),
                  "%s: face index %d out of range (%d points)" % (label, index, len(points)))

    orphans = orphans_of(points, faces)
    check(not orphans,
          "%s: %d vertex(es) belong to no face — Maya segfaults on these: %r"
          % (label, len(orphans), orphans[:10]))


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


def main():
    test_decimate_emits_no_orphans()
    test_chain_emits_no_orphans()
    print("qem tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
