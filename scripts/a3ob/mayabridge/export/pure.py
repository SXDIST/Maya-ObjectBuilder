"""Maya-free kernels used by the P3D export path.

Kept as a plain module (no Maya imports) so the algorithm can be unit-tested with a system
Python interpreter — the byte gate cannot see logic bugs that happen to produce the same
output on the two golden fixtures, so the important equivalences deserve tests of their own.
"""


def derive_faces_pure(face_table, incident_table, vertices, faces):
    """Add every face whose corners lie entirely in ``vertices`` to ``faces``.

    Semantics are identical to the naive walk (visit every face, superset-test its vertex
    tuple against ``vertices``). See tests/python/test_derive_faces_from_vertices.py for
    the equivalence proof against that oracle.

    Inverted from the naive form: for a selection with a small vertex-set, walking incident
    faces of member vertices is O(|vertices| * avg_valence) instead of O(|faces|) — on a
    12k-face LOD with 40 named selections that was the hot spot of the exporter."""
    if not vertices:
        return
    seen = set()
    for vertex in vertices:
        if 0 <= vertex < len(incident_table):
            for face_index in incident_table[vertex]:
                if face_index in seen:
                    continue
                seen.add(face_index)
                face_vertices = face_table[face_index]
                if face_vertices and vertices.issuperset(face_vertices):
                    faces.add(face_index)


__all__ = ["derive_faces_pure"]
