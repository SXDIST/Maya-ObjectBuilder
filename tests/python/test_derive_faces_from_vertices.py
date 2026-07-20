"""``derive_faces_pure`` — pure Python, no Maya.

The exporter derives a selection's face-set from its vertex-set by picking every face whose
corners lie entirely inside the vertex-set. The inverted algorithm (walk incident faces of
member vertices) must produce the same set as the naive walk (visit every face and superset-
test it). The gate for that equivalence is here rather than in a Maya workflow, because
gaming a byte-identical .p3d already covers the integration side.

Run:  python tests/python/test_derive_faces_from_vertices.py
"""

import importlib.util
import os
import random
import sys

# Load the pure kernel directly from its file, bypassing the ``a3ob.mayabridge.export``
# package's __init__ which pulls in Maya. The kernel is Maya-free by design; the isolated
# load makes that testable under a plain system Python.
_PURE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "scripts", "a3ob", "mayabridge", "export", "pure.py")
_spec = importlib.util.spec_from_file_location("_export_pure", _PURE_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
derive_faces_pure = _module.derive_faces_pure


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def _incident_table(face_table, vertex_count):
    incident = [[] for _ in range(vertex_count)]
    for face_index, corners in enumerate(face_table):
        for vertex in corners:
            if 0 <= vertex < vertex_count:
                incident[vertex].append(face_index)
    return incident


def _naive_derive(face_table, vertices, faces):
    """The pre-refactor implementation, kept here as the reference oracle."""
    if not vertices:
        return
    for index, face_vertices in enumerate(face_table):
        if face_vertices and vertices.issuperset(face_vertices):
            faces.add(index)


def test_matches_naive_on_a_small_mesh():
    # Two touching quads sharing an edge, one triangle floating below.
    #   0---1---2
    #   | A | B |
    #   3---4---5
    #      /|
    #     6 7
    face_table = [
        (0, 1, 4, 3),   # quad A
        (1, 2, 5, 4),   # quad B
        (4, 7, 6),      # triangle C
    ]
    incident = _incident_table(face_table, 8)

    cases = [
        set(),                # empty selection selects nothing
        {0, 1, 3, 4},         # covers quad A only
        {0, 1, 3, 4, 6},      # still only quad A — 6 is a stray
        {1, 2, 4, 5},         # covers quad B only
        {0, 1, 2, 3, 4, 5},   # covers both quads, not the triangle
        {4, 6, 7},            # covers the triangle
        set(range(8)),        # whole mesh
    ]
    for vertices in cases:
        expected = set()
        _naive_derive(face_table, vertices, expected)
        actual = set()
        derive_faces_pure(face_table, incident, vertices, actual)
        check(actual == expected, "%s: naive %s vs inverted %s" % (vertices, expected, actual))
    print("OK derive_faces_pure matches the naive walk on a hand-built mesh")


def test_matches_naive_on_random_meshes():
    rng = random.Random(20260720)
    for trial in range(40):
        vertex_count = rng.randint(20, 200)
        face_count = rng.randint(30, 400)
        face_table = []
        for _ in range(face_count):
            corners = rng.choice((3, 4))
            face = tuple(rng.sample(range(vertex_count), corners))
            face_table.append(face)
        incident = _incident_table(face_table, vertex_count)
        for _ in range(5):
            size = rng.randint(0, vertex_count)
            vertices = set(rng.sample(range(vertex_count), size))
            expected = set()
            _naive_derive(face_table, vertices, expected)
            actual = set()
            derive_faces_pure(face_table, incident, vertices, actual)
            check(actual == expected,
                  "trial %d size %d: mismatch %s" % (trial, size, expected ^ actual))
    print("OK derive_faces_pure matches the naive walk on 200 random selections")


def test_preserves_faces_already_present():
    # Callers pre-seed ``faces`` with any explicit f[...] members from the objectSet reader;
    # derive_faces_pure must add to that set, never replace it.
    face_table = [(0, 1, 2), (0, 2, 3), (4, 5, 6)]
    incident = _incident_table(face_table, 7)
    faces = {2}  # face 2 already selected explicitly, and its vertices (4,5,6) are NOT in the set
    derive_faces_pure(face_table, incident, {0, 1, 2, 3}, faces)
    check(faces == {0, 1, 2}, "explicit face 2 must survive; 0 and 1 must be added")
    print("OK derive_faces_pure preserves pre-seeded faces")


def test_empty_face_is_ignored():
    # An empty face-vertex tuple is a degenerate mesh row; the naive walk excluded it
    # explicitly ("face_vertices and ..."), so the inverted walk must exclude it too.
    face_table = [(0, 1, 2), ()]
    incident = _incident_table(face_table, 3)
    incident.append([])  # no vertex refers to the empty face, so this is a no-op
    faces = set()
    derive_faces_pure(face_table, incident, {0, 1, 2}, faces)
    check(faces == {0}, "empty face row must not be added")
    print("OK derive_faces_pure ignores empty face-vertex rows")


def main():
    test_matches_naive_on_a_small_mesh()
    test_matches_naive_on_random_meshes()
    test_preserves_faces_already_present()
    test_empty_face_is_ignored()
    print("test_derive_faces_from_vertices: PASS")


if __name__ == "__main__":
    main()
