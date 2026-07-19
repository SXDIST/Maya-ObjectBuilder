"""Quadric Error Metric (QEM) edge-collapse decimation — a faithful port of the
Garland-Heckbert algorithm that Blender's *Decimate → Collapse* modifier uses.

Maya's ``polyReduce`` is also QEM but its implementation leaves lumpy, sliver-heavy
triangles on smooth surfaces (nothing like Blender's even output), so the resolution
LODs are decimated with this instead. It is Maya-independent (numpy in, numpy out) and
adaptive: flat regions (e.g. house walls) stay sparse while curved detail keeps density,
exactly like Blender — so it scales to 40k-poly hard-surface models, not just spheres.

``decimate_chain`` collapses once and snapshots at every LOD target, so a whole LOD
ladder costs a single decimation pass.
"""

import heapq
from collections import defaultdict

import numpy as np

BOUNDARY_WEIGHT = 1000.0  # how hard open borders resist collapsing (Blender keeps them)


def _face_plane(V, f):
    p0, p1, p2 = V[f[0]], V[f[1]], V[f[2]]
    nrm = np.cross(p1 - p0, p2 - p0)
    ln = np.linalg.norm(nrm)
    if ln < 1e-12:
        return None
    nrm = nrm / ln
    return np.array([nrm[0], nrm[1], nrm[2], -nrm.dot(p0)])


class _Decimator:
    def __init__(self, V, F, preserve_boundary=True):
        self.V = V.astype(np.float64).copy()
        self.F = [list(map(int, f)) for f in F]
        self.n = len(self.V)
        self.alive_f = [True] * len(self.F)
        self.alive_v = [True] * self.n
        self.vfaces = defaultdict(set)
        for fi, f in enumerate(self.F):
            for v in f:
                self.vfaces[v].add(fi)
        self.nf = len(self.F)
        self._build_quadrics(preserve_boundary)
        self._build_heap()

    def _build_quadrics(self, preserve_boundary):
        V, F = self.V, self.F
        Q = [np.zeros((4, 4)) for _ in range(self.n)]
        for f in F:
            p = _face_plane(V, f)
            if p is None:
                continue
            K = np.outer(p, p)
            for v in f:
                Q[v] += K
        if preserve_boundary:
            edge_faces = defaultdict(list)
            for fi, f in enumerate(F):
                for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                    edge_faces[(min(a, b), max(a, b))].append(fi)
            for (a, b), fs in edge_faces.items():
                if len(fs) != 1:
                    continue
                p = _face_plane(V, F[fs[0]])
                if p is None:
                    continue
                # a plane through the boundary edge, perpendicular to the face — collapsing
                # the edge off this plane now costs error, so the silhouette is preserved.
                bn = np.cross(V[b] - V[a], p[:3])
                ln = np.linalg.norm(bn)
                if ln < 1e-12:
                    continue
                bn = bn / ln
                bp = np.array([bn[0], bn[1], bn[2], -bn.dot(V[a])])
                K = np.outer(bp, bp) * BOUNDARY_WEIGHT
                Q[a] += K
                Q[b] += K
        self.Q = Q

    def _eval(self, a, b):
        Qs = self.Q[a] + self.Q[b]
        best = None
        for c in (self.V[a], self.V[b], 0.5 * (self.V[a] + self.V[b])):
            p4 = np.array([c[0], c[1], c[2], 1.0])
            co = float(p4.dot(Qs).dot(p4))
            if best is None or co < best[0]:
                best = (co, c.copy())
        return best

    def _push(self, a, b):
        e = (min(a, b), max(a, b))
        co, pos = self._eval(a, b)
        self.ver[e] += 1
        heapq.heappush(self.heap, (co, self.ver[e], e[0], e[1], pos))

    def _build_heap(self):
        self.ver = defaultdict(int)
        self.heap = []
        seen = set()
        for f in self.F:
            for a, b in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])):
                e = (min(a, b), max(a, b))
                if e not in seen:
                    seen.add(e)
                    self._push(a, b)

    def _flips(self, a, b, newpos):
        V, F = self.V, self.F
        for v in (a, b):
            for fi in self.vfaces[v]:
                if not self.alive_f[fi]:
                    continue
                f = F[fi]
                if a in f and b in f:
                    continue  # this face is removed by the collapse
                pts = [newpos if (x == a or x == b) else V[x] for x in f]
                on = np.cross(V[f[1]] - V[f[0]], V[f[2]] - V[f[0]])
                nn = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                if on.dot(nn) < 0.0:
                    return True
        return False

    def run_to(self, target_faces):
        V, F = self.V, self.F
        while self.nf > target_faces and self.heap:
            co, vs, a, b, pos = heapq.heappop(self.heap)
            e = (min(a, b), max(a, b))
            if vs != self.ver[e] or not self.alive_v[a] or not self.alive_v[b]:
                continue
            shared = [fi for fi in self.vfaces[a] if self.alive_f[fi] and b in F[fi]]
            if not shared:
                continue
            if self._flips(a, b, pos):
                self.ver[e] += 1  # invalidate; try other edges first
                continue
            V[a] = pos
            for fi in shared:
                self.alive_f[fi] = False
                for vv in F[fi]:
                    self.vfaces[vv].discard(fi)
            self.nf -= len(shared)
            for fi in list(self.vfaces[b]):
                if not self.alive_f[fi]:
                    continue
                F[fi] = [a if x == b else x for x in F[fi]]
                self.vfaces[a].add(fi)
                g = F[fi]
                if g[0] == g[1] or g[1] == g[2] or g[2] == g[0]:
                    self.alive_f[fi] = False
                    for vv in set(g):
                        self.vfaces[vv].discard(fi)
                    self.nf -= 1
            self.vfaces[b] = set()
            self.alive_v[b] = False
            self.Q[a] = self.Q[a] + self.Q[b]
            nbrs = set()
            for fi in self.vfaces[a]:
                if self.alive_f[fi]:
                    for vv in F[fi]:
                        if vv != a and self.alive_v[vv]:
                            nbrs.add(vv)
            for vv in nbrs:
                self._push(a, vv)

    def snapshot(self):
        """The surviving geometry, renumbered.

        The surviving faces are the single source of truth for which vertices exist: the
        emitted set is exactly the set they reference, so the two sides cannot disagree.
        That symmetry is the point, and it is enforced by construction rather than
        checked, because BOTH ways of breaking it are bugs with teeth:

        * Emitting a vertex no face references produces a point with no normal, and
          ``polyNormalPerVertex`` segfaults Maya outright when it walks onto one —
          measured on a real DayZ garment: 5 such points at ratio 0.25, 62 at 0.0625,
          and a dead session.
        * Emitting a face whose vertex was dropped is a dangling index into ``o2n``.

        Note ``alive_v`` is deliberately NOT consulted here, in either direction. It
        over-reports: a vertex stays alive after the last face around it collapses into a
        degenerate one and is dropped, which happens to a whole small shell (a pouch, a
        patch, a buckle) long before the overall face target is reached — so filtering on
        ``used`` alone is what removes those. It never under-reports (a live face can
        never reference a dead vertex: ``run_to`` only clears ``alive_v[b]`` after
        remapping every face in ``vfaces[b]``, and a face is only ever dropped from a
        ``vfaces`` entry once it is already dead), so intersecting with it would be a
        no-op that merely made the two loops disagree about their input."""
        # f[:3], not f: the face loop below emits three corners, so collecting more than
        # three here would count a vertex as used that nothing ends up referencing.
        used = set()
        for fi, f in enumerate(self.F):
            if self.alive_f[fi]:
                used.update(f[:3])

        o2n = {}
        NV = []
        for i in sorted(used):
            o2n[i] = len(NV)
            NV.append(self.V[i])

        NF = []
        orig = []  # original face slot of each surviving face (for per-face material carry)
        for fi, f in enumerate(self.F):
            if self.alive_f[fi]:
                NF.append([o2n[f[0]], o2n[f[1]], o2n[f[2]]])
                orig.append(fi)
        # An empty result must keep the (0, 3) shape callers index into.
        return (np.array(NV) if NV else np.zeros((0, 3))), NF, orig


def decimate(V, F, target_faces, preserve_boundary=True):
    """Collapse the triangle mesh ``(V, F)`` down to ~``target_faces`` triangles.
    Returns ``(points, faces, orig_face_index)`` — ``orig_face_index[j]`` is the index of
    the input face that survivor ``j`` came from (faces are only removed/reindexed, never
    split, so a surviving face keeps its original identity — used to carry materials)."""
    d = _Decimator(V, F, preserve_boundary)
    d.run_to(target_faces)
    return d.snapshot()


def decimate_chain(V, F, targets, preserve_boundary=True):
    """Progressive decimation: one collapse pass, snapshotting at each target face
    count. ``targets`` is any iterable of triangle counts; returns a dict
    ``{target: (points, faces, orig_face_index)}``. Cheaper than decimating the base
    separately per LOD."""
    d = _Decimator(V, F, preserve_boundary)
    out = {}
    for t in sorted(set(int(x) for x in targets), reverse=True):
        d.run_to(t)
        out[t] = d.snapshot()
    return out
