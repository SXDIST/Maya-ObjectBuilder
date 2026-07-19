"""Influence-name rules for ``a3obInfluence`` — no Maya imports.

Deliberately Maya-free so it can be unit-tested with a plain interpreter, the same way
``skinweights.py`` is; ``a3ob.mayabridge.commands.influence`` supplies the Maya plumbing.
"""

import fnmatch


def leaf_name(name):
    """The bare joint name out of a DAG path with an optional namespace."""
    return (name or "").split("|")[-1].split(":")[-1]


def match_names(names, pattern):
    """Names whose leaf matches a shell-style mask, in the order given.

    An empty mask matches NOTHING rather than everything. The mask drives what the dock's
    influence list shows, and an empty filter box must never fill that list with the whole
    rig sitting one click away from removal."""
    if not pattern:
        return []
    return [name for name in names if fnmatch.fnmatch(leaf_name(name), pattern)]


def removable(all_names, requested):
    """``(names that may go, reason nothing may)``.

    A skinCluster must keep at least one influence: a mesh with none cannot deform, and a
    request covering every bone is a slip rather than an instruction."""
    wanted = set(requested or [])
    present = [name for name in all_names if name in wanted]
    if not present:
        return [], "none of the requested influences are on this mesh"
    if len(present) >= len(all_names):
        return [], ("that would remove every influence (%d) — a skinCluster must keep at "
                    "least one, or the mesh stops deforming" % len(all_names))
    return present, ""


__all__ = ["leaf_name", "match_names", "removable"]
