"""Skin-weight outlier detection — pure math, no Maya imports.

A weight-transfer pass (body -> garment) occasionally binds a single vertex to a bone
belonging to a completely different body part: the ray/closest-point lookup jumps a gap and
lands on the wrong side. Such a vertex is invisible in bind pose — it only shows once the
skeleton is posed — but Object Builder paints *selection membership*, so it appears as a
stray weighted vertex far from the bone.

The detector is skeleton-agnostic: a vertex is an outlier when its weight distribution is
almost disjoint from the mean distribution of its connected neighbours. Deviation is the
total-variation distance ``0.5 * sum|a - b|`` between the two distributions, which is 0.0
for identical weights and 1.0 when they share no influence at all. Real geometry has smooth
weight gradients, so honest vertices stay well below the threshold even across bone
boundaries, while transfer artefacts sit at ~1.0.

This module only *reports*. Repairing weights is Maya's own job — `Skin > Smooth Skin
Weights` and `Skin > Prune Small Weights` do it properly, and an exporter has no business
rewriting a rig behind the user's back. `a3obSkinWeights` selects the suspects so those
tools can be pointed straight at them.

Deliberately Maya-free so it can be unit-tested with a plain interpreter;
``a3ob.mayabridge.commands.skin`` supplies the Maya-side plumbing.
"""

MAX_INFLUENCES = 4

# Selection weights are stored as one byte with a 1/254 step (see
# ``p3d.SelectionTaggData.encode_weight``), so anything below this quantizes to zero. Such a
# vertex would still be *listed* in the selection with weight 0.0 — noise in Object Builder.
MIN_ENCODABLE_WEIGHT = 1.0 / 254.0

DEFAULT_OUTLIER_THRESHOLD = 0.5


def vertex_row(weights, influence_count, vertex):
    """The ``influence_count`` weights of one vertex out of a flat getWeights() array."""
    base = vertex * influence_count
    return list(weights[base:base + influence_count])


def deviation(row_a, row_b):
    """Total-variation distance between two weight rows: 0.0 identical, 1.0 disjoint."""
    return 0.5 * sum(abs(a - b) for a, b in zip(row_a, row_b))


def mean_row(rows, influence_count):
    """Component-wise mean of several weight rows (zeros when there are none)."""
    if not rows:
        return [0.0] * influence_count
    total = [0.0] * influence_count
    for row in rows:
        for i in range(influence_count):
            total[i] += row[i]
    count = float(len(rows))
    return [value / count for value in total]


def neighbour_mean(weights, influence_count, neighbours):
    """Mean weight row of the given neighbour vertex ids."""
    return mean_row([vertex_row(weights, influence_count, v) for v in neighbours], influence_count)


def prune_normalize(row, max_influences=MAX_INFLUENCES, epsilon=MIN_ENCODABLE_WEIGHT):
    """Keep the strongest ``max_influences`` weights above ``epsilon`` and renormalize.

    Returns a full-width row summing to 1.0, or all zeros when nothing survives."""
    pairs = [(weight, i) for i, weight in enumerate(row) if weight > epsilon]
    pairs.sort(reverse=True)
    pairs = pairs[:max_influences]
    total = sum(weight for weight, _i in pairs)
    result = [0.0] * len(row)
    if total <= 0.0:
        return result
    for weight, i in pairs:
        result[i] = weight / total
    return result


def find_candidates(weights, influence_count, neighbours_of, threshold=DEFAULT_OUTLIER_THRESHOLD,
                    min_neighbours=2):
    """First pass: vertex ids whose weights disagree with their neighbours beyond ``threshold``.

    ``neighbours_of`` maps a vertex id to its connected vertex ids. Vertices with fewer than
    ``min_neighbours`` neighbours are skipped — a single neighbour is not evidence.

    These are *candidates*, not verdicts: an artefact drags its own neighbours over the
    threshold too, so a correctly-weighted vertex next to one gets swept up here. Run
    ``confirm_outliers`` to drop those. Returns ``(vertex, deviation)`` pairs."""
    if influence_count <= 0:
        return []
    candidates = []
    for vertex in range(len(weights) // influence_count):
        neighbours = neighbours_of[vertex]
        if len(neighbours) < min_neighbours:
            continue
        row = vertex_row(weights, influence_count, vertex)
        if sum(row) <= 0.0:
            continue
        score = deviation(row, neighbour_mean(weights, influence_count, neighbours))
        if score > threshold:
            candidates.append((vertex, score))
    return candidates


def confirm_outliers(weights, influence_count, neighbours_of, candidates,
                     threshold=DEFAULT_OUTLIER_THRESHOLD, min_clean_neighbours=2):
    """Second pass: re-judge each candidate against its trustworthy neighbours only.

    A neighbour is distrusted when it is itself a candidate that deviates at least as much
    as the vertex being judged — never average from something that looks even more broken
    than you do. Merely excluding *every* candidate would strand the true artefact with no
    neighbours at all, since it is precisely the vertex that pulled them over the threshold.

    Returns ``(vertex, clean_neighbours)`` for candidates whose disagreement survives the
    clean comparison and that have enough clean neighbours to be judged against."""
    scores = dict(candidates)
    confirmed = []
    for vertex, score in candidates:
        clean = [n for n in neighbours_of[vertex] if scores.get(n, -1.0) < score]
        if len(clean) < min_clean_neighbours:
            continue
        row = vertex_row(weights, influence_count, vertex)
        if deviation(row, neighbour_mean(weights, influence_count, clean)) > threshold:
            confirmed.append((vertex, clean))
    return confirmed


def find_outliers(weights, influence_count, neighbours_of, threshold=DEFAULT_OUTLIER_THRESHOLD,
                  min_neighbours=2, min_clean_neighbours=2):
    """Confirmed outlier ``(vertex, clean_neighbours)`` pairs — both passes."""
    candidates = find_candidates(weights, influence_count, neighbours_of, threshold, min_neighbours)
    return confirm_outliers(weights, influence_count, neighbours_of, candidates,
                            threshold, min_clean_neighbours)


# -- baking ------------------------------------------------------------------
#
# Weights live in the skinCluster, and deleting the skeleton deletes the skinCluster with it:
# the weights are simply gone, and export then writes a file with no bone selections at all.
# Baking copies them onto the LOD transform so they survive that, and so a rigged model can be
# exported from a scene that no longer carries the rig.
#
# Format: "bone:index=weight,index=weight;bone:..." — only non-zero weights are stored, which
# is what keeps it to a few hundred KB rather than vertices x bones.


def bake_string(influence_names, weights, influence_count):
    """Serialize a getWeights() array as "bone:index=weight,..." per influencing bone."""
    parts = []
    vertex_count = len(weights) // influence_count if influence_count else 0
    for index, name in enumerate(influence_names):
        pairs = []
        for vertex in range(vertex_count):
            value = weights[vertex * influence_count + index]
            if value > MIN_ENCODABLE_WEIGHT:
                pairs.append("%d=%s" % (vertex, repr(float(value))))
        if pairs:
            parts.append("%s:%s" % (name, ",".join(pairs)))
    return ";".join(parts)


def parse_bake_string(value):
    """Inverse of bake_string: returns [(bone, [(vertex, weight), ...]), ...]."""
    result = []
    for chunk in (value or "").split(";"):
        if not chunk or ":" not in chunk:
            continue
        name, _, body = chunk.partition(":")
        pairs = []
        for item in body.split(","):
            index, _, weight = item.partition("=")
            try:
                pairs.append((int(index), float(weight)))
            except ValueError:
                continue
        if name and pairs:
            result.append((name, pairs))
    return result


__all__ = [
    "MAX_INFLUENCES",
    "MIN_ENCODABLE_WEIGHT",
    "DEFAULT_OUTLIER_THRESHOLD",
    "vertex_row",
    "deviation",
    "mean_row",
    "neighbour_mean",
    "prune_normalize",
    "find_candidates",
    "confirm_outliers",
    "find_outliers",
    "bake_string",
    "parse_bake_string",
]
