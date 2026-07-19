"""Mesh topology helpers: polygon validity checks and closed-face-island detection for a3obFindComponents and a3obValidate."""

import maya.api.OpenMaya as om

from a3ob.mayabridge.commands.helpers.primitives import *  # noqa: F401,F403


EdgeKey = lambda a, b: (a, b) if a < b else (b, a)  # noqa: E731


def polygon_has_repeated_vertices(vertices):
    seen = set()
    for v in vertices:
        if v in seen:
            return True
        seen.add(v)
    return False


def polygon_has_near_zero_area(points):
    if len(points) < 3:
        return True
    origin = points[0]
    area = 0.0
    for i in range(1, len(points) - 1):
        a = points[i] - origin
        b = points[i + 1] - origin
        area += (a ^ b).length() * 0.5
    return area < 1.0e-10


def closed_face_islands(mesh_fn):
    it = om.MItMeshPolygon(mesh_fn.object())
    num_polygons = mesh_fn.numPolygons
    edge_faces = {}
    face_edges = [[] for _ in range(num_polygons)]
    while not it.isDone():
        vertices = it.getVertices()
        face_index = it.index()
        n = len(vertices)
        for i in range(n):
            key = EdgeKey(vertices[i], vertices[(i + 1) % n])
            edge_faces.setdefault(key, []).append(face_index)
            face_edges[face_index].append(key)
        it.next()

    adjacency = [[] for _ in range(num_polygons)]
    for key, faces in edge_faces.items():
        if len(faces) == 2:
            adjacency[faces[0]].append(faces[1])
            adjacency[faces[1]].append(faces[0])

    visited = [False] * num_polygons
    islands = []
    for start in range(num_polygons):
        if visited[start]:
            continue
        island_faces = set()
        island_vertices = set()
        closed = True
        queue = [start]
        visited[start] = True
        while queue:
            face = queue.pop(0)
            island_faces.add(face)
            for key in face_edges[face]:
                island_vertices.add(key[0])
                island_vertices.add(key[1])
            for nxt in adjacency[face]:
                if not visited[nxt]:
                    visited[nxt] = True
                    queue.append(nxt)
        for face in island_faces:
            for key in face_edges[face]:
                count = sum(1 for ef in edge_faces[key] if ef in island_faces)
                if count != 2:
                    closed = False
        islands.append((island_faces, island_vertices, closed))
    return islands


# =============================================================================
# component selection collection
# =============================================================================


__all__ = [
    "EdgeKey",
    "polygon_has_repeated_vertices",
    "polygon_has_near_zero_area",
    "closed_face_islands",
]
