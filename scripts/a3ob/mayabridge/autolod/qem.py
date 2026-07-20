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

_ZERO_QUADRIC = (0.0,) * 10

# Collapses between two monitor polls. Small enough that Esc still feels immediate (a few
# hundred collapses are ~1 ms), large enough that the poll itself costs nothing measurable.
_MONITOR_INTERVAL = 256


def _quadric_add(p, q):
    return (p[0] + q[0], p[1] + q[1], p[2] + q[2], p[3] + q[3], p[4] + q[4],
            p[5] + q[5], p[6] + q[6], p[7] + q[7], p[8] + q[8], p[9] + q[9])


def _face_plane(V, f):
    """The face's unit plane ``(nx, ny, nz, w)`` as four plain floats, or None if degenerate.

    Plain floats, not numpy: this runs once per face at setup but the same arithmetic style
    is used all through the collapse loop below, where numpy's ~1-2 us per-call dispatch
    overhead on 3- and 4-vectors dwarfs the handful of multiplies it performs."""
    p0 = V[f[0]]
    p1 = V[f[1]]
    p2 = V[f[2]]
    ax = p1[0] - p0[0]
    ay = p1[1] - p0[1]
    az = p1[2] - p0[2]
    bx = p2[0] - p0[0]
    by = p2[1] - p0[1]
    bz = p2[2] - p0[2]
    nx = ay * bz - az * by
    ny = az * bx - ax * bz
    nz = ax * by - ay * bx
    ln = (nx * nx + ny * ny + nz * nz) ** 0.5
    if ln < 1e-12:
        return None
    nx /= ln
    ny /= ln
    nz /= ln
    return (nx, ny, nz, -(nx * p0[0] + ny * p0[1] + nz * p0[2]))


def _plane_quadric(p, weight=1.0):
    """The symmetric 4x4 quadric ``weight * p p^T``, stored as its 10 distinct floats.

    Order is row-major upper triangle::

        [ q0 q1 q2 q3 ]
        [ q1 q4 q5 q6 ]
        [ q2 q5 q7 q8 ]
        [ q3 q6 q8 q9 ]

    A 4x4 numpy array holds the same 16 numbers but costs an allocation per face and an
    ``np.add`` dispatch per accumulation; ten floats in a tuple cost neither."""
    a, b, c, d = p
    # The outer product is formed first and scaled after, matching ``np.outer(p, p) * w``
    # term for term — scaling a factor instead would round differently.
    return (a * a * weight, a * b * weight, a * c * weight, a * d * weight,
            b * b * weight, b * c * weight, b * d * weight,
            c * c * weight, c * d * weight,
            d * d * weight)


def _quadric_error(q, x, y, z):
    """``[x y z 1] Q [x y z 1]^T`` for the packed symmetric quadric ``q``."""
    return (q[0] * x * x + q[4] * y * y + q[7] * z * z + q[9]
            + 2.0 * (q[1] * x * y + q[2] * x * z + q[3] * x
                     + q[5] * y * z + q[6] * y + q[8] * z))


class _Decimator:
    def __init__(self, V, F, preserve_boundary=True):
        # Plain lists of floats, not an (N, 3) array: every access below is a single point,
        # and indexing a numpy row to reach .x/.y/.z is far slower than a list of lists.
        # ``snapshot`` builds the numpy array callers expect on the way out.
        self.V = [[float(p[0]), float(p[1]), float(p[2])] for p in V]
        self.F = [list(map(int, f)) for f in F]
        self.n = len(self.V)
        self.alive_f = [True] * len(self.F)
        self.alive_v = [True] * self.n
        self.vfaces = defaultdict(set)
        for fi, f in enumerate(self.F):
            for v in f:
                self.vfaces[v].add(fi)
        self.nf = len(self.F)
        self.nf0 = self.nf  # for progress reporting: faces removed = nf0 - nf
        self._build_quadrics(preserve_boundary)
        self._build_heap()

    def _build_quadrics(self, preserve_boundary):
        V, F = self.V, self.F
        Q = [_ZERO_QUADRIC] * self.n
        for f in F:
            p = _face_plane(V, f)
            if p is None:
                continue
            K = _plane_quadric(p)
            for v in f:
                Q[v] = _quadric_add(Q[v], K)
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
                pa = V[a]
                pb = V[b]
                ex = pb[0] - pa[0]
                ey = pb[1] - pa[1]
                ez = pb[2] - pa[2]
                bx = ey * p[2] - ez * p[1]
                by = ez * p[0] - ex * p[2]
                bz = ex * p[1] - ey * p[0]
                ln = (bx * bx + by * by + bz * bz) ** 0.5
                if ln < 1e-12:
                    continue
                bx /= ln
                by /= ln
                bz /= ln
                K = _plane_quadric(
                    (bx, by, bz, -(bx * pa[0] + by * pa[1] + bz * pa[2])), BOUNDARY_WEIGHT)
                Q[a] = _quadric_add(Q[a], K)
                Q[b] = _quadric_add(Q[b], K)
        self.Q = Q

    def _eval(self, a, b):
        qa = self.Q[a]
        qb = self.Q[b]
        q = (qa[0] + qb[0], qa[1] + qb[1], qa[2] + qb[2], qa[3] + qb[3], qa[4] + qb[4],
             qa[5] + qb[5], qa[6] + qb[6], qa[7] + qb[7], qa[8] + qb[8], qa[9] + qb[9])
        va = self.V[a]
        vb = self.V[b]
        ax, ay, az = va[0], va[1], va[2]
        bx, by, bz = vb[0], vb[1], vb[2]
        mx = 0.5 * (ax + bx)
        my = 0.5 * (ay + by)
        mz = 0.5 * (az + bz)

        best_cost = _quadric_error(q, ax, ay, az)
        best_pos = [ax, ay, az]
        cost = _quadric_error(q, bx, by, bz)
        if cost < best_cost:
            best_cost = cost
            best_pos = [bx, by, bz]
        cost = _quadric_error(q, mx, my, mz)
        if cost < best_cost:
            best_cost = cost
            best_pos = [mx, my, mz]
        return best_cost, best_pos

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
                o0 = V[f[0]]
                o1 = V[f[1]]
                o2 = V[f[2]]
                n0 = newpos if (f[0] == a or f[0] == b) else o0
                n1 = newpos if (f[1] == a or f[1] == b) else o1
                n2 = newpos if (f[2] == a or f[2] == b) else o2
                oux = o1[0] - o0[0]
                ouy = o1[1] - o0[1]
                ouz = o1[2] - o0[2]
                ovx = o2[0] - o0[0]
                ovy = o2[1] - o0[1]
                ovz = o2[2] - o0[2]
                nux = n1[0] - n0[0]
                nuy = n1[1] - n0[1]
                nuz = n1[2] - n0[2]
                nvx = n2[0] - n0[0]
                nvy = n2[1] - n0[1]
                nvz = n2[2] - n0[2]
                onx = ouy * ovz - ouz * ovy
                ony = ouz * ovx - oux * ovz
                onz = oux * ovy - ouy * ovx
                nnx = nuy * nvz - nuz * nvy
                nny = nuz * nvx - nux * nvz
                nnz = nux * nvy - nuy * nvx
                if onx * nnx + ony * nny + onz * nnz < 0.0:
                    return True
        return False

    def run_to(self, target_faces, monitor=None):
        """Collapse until ``target_faces`` remain. Returns False when ``monitor`` reported
        cancellation, True otherwise.

        A cancelled decimator is left MID-COLLAPSE and must not be snapshotted: callers bail
        on False rather than handing a half-reduced mesh back to Maya.

        ``monitor`` is duck-typed (``cancelled()`` / ``step(done)``) so this module stays
        Maya-free; ``a3ob.mayabridge.progress.Progress`` is what actually gets passed in.
        ``done`` counts faces removed since construction, so one monitor spans a whole
        ``decimate_chain`` ladder."""
        V, F = self.V, self.F
        since_check = 0
        while self.nf > target_faces and self.heap:
            if monitor is not None:
                since_check += 1
                if since_check >= _MONITOR_INTERVAL:
                    since_check = 0
                    if monitor.cancelled():
                        return False
                    monitor.step(self.nf0 - self.nf)
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
            self.Q[a] = _quadric_add(self.Q[a], self.Q[b])
            nbrs = set()
            for fi in self.vfaces[a]:
                if self.alive_f[fi]:
                    for vv in F[fi]:
                        if vv != a and self.alive_v[vv]:
                            nbrs.add(vv)
            for vv in nbrs:
                self._push(a, vv)
        return True

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


def decimate(V, F, target_faces, preserve_boundary=True, monitor=None):
    """Collapse the triangle mesh ``(V, F)`` down to ~``target_faces`` triangles.
    Returns ``(points, faces, orig_face_index)`` — ``orig_face_index[j]`` is the index of
    the input face that survivor ``j`` came from (faces are only removed/reindexed, never
    split, so a surviving face keeps its original identity — used to carry materials).

    Returns None instead if ``monitor`` reported cancellation; see ``run_to``."""
    d = _Decimator(V, F, preserve_boundary)
    if not d.run_to(target_faces, monitor):
        return None
    return d.snapshot()


def decimate_chain(V, F, targets, preserve_boundary=True, monitor=None):
    """Progressive decimation: one collapse pass, snapshotting at each target face
    count. ``targets`` is any iterable of triangle counts; returns a dict
    ``{target: (points, faces, orig_face_index)}``. Cheaper than decimating the base
    separately per LOD.

    Returns None instead if ``monitor`` reported cancellation. Nothing partial comes back —
    a cancelled ladder yields no snapshots at all, so the caller cannot accidentally push a
    half-collapsed mesh into the scene."""
    d = _Decimator(V, F, preserve_boundary)
    out = {}
    for t in sorted(set(int(x) for x in targets), reverse=True):
        if not d.run_to(t, monitor):
            return None
        out[t] = d.snapshot()
    return out
