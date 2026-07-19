"""Pure-Python skin-weight outlier test (no Maya).

Builds a tiny synthetic skin: a 6-vertex chain weighted smoothly across two bones, with one
vertex deliberately bound to a third, unrelated bone (the weight-transfer artefact this
module exists to catch). Asserts that only that vertex is flagged, that a smooth gradient is
not, and that two adjacent artefacts still get detected despite masking each other.

Run:  python tests/python/test_skinweights.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from a3ob.mayabridge.skinweights import (  # noqa: E402
    MIN_ENCODABLE_WEIGHT,
    deviation,
    find_candidates,
    find_outliers,
    prune_normalize,
    bake_string,
    parse_bake_string,
    weights_from_bake,
)

INFLUENCES = 3  # Hip, Knee, Foot
CLEAN = [
    [1.0, 0.0, 0.0],
    [0.8, 0.2, 0.0],
    [0.6, 0.4, 0.0],
    [0.4, 0.6, 0.0],
    [0.2, 0.8, 0.0],
    [0.0, 1.0, 0.0],
]
# Same chain with vertex 3 rebound to the unrelated third bone (the transfer artefact).
CHAIN = [row[:] for row in CLEAN]
CHAIN[3] = [0.0, 0.0, 1.0]
NEIGHBOURS = [[1], [0, 2], [1, 3], [2, 4], [3, 5], [4]]


def flat(rows):
    return [w for row in rows for w in row]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    weights = flat(CHAIN)

    check(deviation(CHAIN[0], CHAIN[0]) == 0.0, "identical rows must have zero deviation")
    check(abs(deviation([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]) - 1.0) < 1e-9,
          "disjoint rows must have deviation 1.0")

    # A smooth two-bone gradient must stay clean even under a much stricter threshold.
    check(find_outliers(flat(CLEAN), INFLUENCES, NEIGHBOURS, threshold=0.25) == [],
          "smooth gradient must produce no outliers")

    outliers = find_outliers(weights, INFLUENCES, NEIGHBOURS)
    check([v for v, _clean in outliers] == [3],
          "expected only vertex 3 flagged, got %r" % (outliers,))

    # An artefact drags its direct neighbours over the threshold, so pass 1 sweeps up the
    # healthy vertices 2 and 4 at a stricter threshold...
    check([v for v, _s in find_candidates(weights, INFLUENCES, NEIGHBOURS, threshold=0.35)] == [2, 3, 4],
          "pass 1 must show neighbour contamination")
    # ...and pass 2 must throw them out again by judging against clean neighbours only.
    confirmed = find_outliers(weights, INFLUENCES, NEIGHBOURS, threshold=0.35)
    check([v for v, _clean in confirmed] == [3],
          "pass 2 must drop contaminated neighbours, got %r" % (confirmed,))
    check(confirmed[0][1] == [2, 4],
          "the artefact must be judged against its clean neighbours, got %r" % (confirmed[0][1],))

    # Top-4 cap and the 1/254 encoding floor.

    capped = prune_normalize([0.3, 0.25, 0.2, 0.15, 0.1], max_influences=4)
    check(capped[4] == 0.0, "5th influence must be dropped, got %r" % (capped,))
    check(abs(sum(capped) - 1.0) < 1e-9, "capped row must renormalize, got %r" % (capped,))

    below_floor = prune_normalize([1.0, MIN_ENCODABLE_WEIGHT * 0.5])
    check(below_floor[1] == 0.0, "sub-1/254 weight must be pruned, got %r" % (below_floor,))

    check(prune_normalize([0.0, 0.0, 0.0]) == [0.0, 0.0, 0.0], "all-zero row must stay zero")

    # Two ADJACENT artefacts partly mask each other: each sits in the other's neighbour
    # mean, pulling the measured deviation down. Detection must still survive it on a real
    # mesh, where a vertex has 5-7 neighbours rather than the chain's 1-2.
    grid_w, grid_h = 6, 5
    grid, grid_neighbours = [], []
    for j in range(grid_h):
        for i in range(grid_w):
            upper = i / float(grid_w - 1)
            grid.append([1.0 - upper, upper, 0.0])
    for j in range(grid_h):
        for i in range(grid_w):
            near = []
            if i > 0: near.append(j * grid_w + i - 1)
            if i < grid_w - 1: near.append(j * grid_w + i + 1)
            if j > 0: near.append((j - 1) * grid_w + i)
            if j < grid_h - 1: near.append((j + 1) * grid_w + i)
            grid_neighbours.append(near)
    first, second = 1 * grid_w + 5, 2 * grid_w + 5  # adjacent, both on the far column
    grid[first] = [0.0, 0.0, 1.0]
    grid[second] = [0.0, 0.0, 1.0]
    found = find_outliers(flat(grid), INFLUENCES, grid_neighbours)
    check(sorted(v for v, _clean in found) == sorted([first, second]),
          "both adjacent artefacts must still be detected, got %r" % ([v for v, _c in found],))

    # -- restoring a bake onto a rig ------------------------------------------------
    #
    # Baking exists so weights outlive the skeleton; restoring is what puts them back on a
    # skinCluster afterwards. It has to survive the rig not being identical to the one that
    # was baked, because that is the whole reason someone re-binds.
    bones = ["Hip", "Knee", "Foot"]
    original = [[1.0, 0.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.25, 0.75]]
    baked = bake_string(bones, flat(original), INFLUENCES)

    restored, missing = weights_from_bake(parse_bake_string(baked), bones, len(original))
    check(not missing, "every bone is on the rig, got missing=%r" % (missing,))
    check(all(abs(a - b) < 1e-9 for a, b in zip(restored, flat(original))),
          "a full round trip must reproduce the weights exactly, got %r" % (restored,))

    # A bone the rig no longer has: its share is renormalized across the bones that remain,
    # never left as a row summing to 0.75 for Maya to silently redistribute.
    fewer = ["Hip", "Knee"]
    restored, missing = weights_from_bake(parse_bake_string(baked), fewer, len(original))
    check(missing == ["Foot"], "the absent bone must be reported, got %r" % (missing,))
    rows = [restored[i * len(fewer):(i + 1) * len(fewer)] for i in range(len(original))]
    check(abs(sum(rows[1]) - 1.0) < 1e-9, "an untouched row still sums to 1, got %r" % (rows[1],))
    check(abs(rows[2][1] - 1.0) < 1e-9,
          "the row that lost Foot goes fully to Knee, got %r" % (rows[2],))
    check(abs(sum(rows[0]) - 1.0) < 1e-9, "and Hip's row is unchanged, got %r" % (rows[0],))

    # A vertex whose every bone is gone stays at zero — inventing weights would be worse
    # than reporting that the rig cannot hold this bake.
    restored, missing = weights_from_bake(parse_bake_string(baked), ["Elbow"], len(original))
    check(missing == bones, "all three bones are missing, got %r" % (missing,))
    check(all(value == 0.0 for value in restored), "nothing is invented, got %r" % (restored,))

    # A bake made on a denser mesh must not write past the end of this one.
    restored, _missing = weights_from_bake(parse_bake_string(baked), bones, 2)
    check(len(restored) == 2 * INFLUENCES, "the array follows the mesh, got %d" % len(restored))

    print("skin weight tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
