"""Resolve a P3D texture path (a mod-relative ``mod\\...\\x_co.paa``) to a real file on disk."""

import os

from a3ob.mayabridge.paatex.settings import texture_root

_WALK_DIR_LIMIT = 20000  # guard: never walk an entire huge drive looking for a basename


def _candidate_roots():
    """Roots to try, in order: the configured texture root, then P:\\ (the standard
    Arma/DayZ work drive) so mod textures resolve even if the root points elsewhere."""
    roots = []
    configured = texture_root()
    if configured and os.path.isdir(configured):
        roots.append(configured)
    for drive_root in ("P:/", "P:\\"):
        if os.path.isdir(drive_root) and drive_root not in roots:
            roots.append(drive_root)
            break
    return roots


def resolve_paa_path(texture_path):
    """Resolve a P3D texture path to a real file: absolute hit, then ``<root>/relative`` for
    each candidate root, then a bounded basename search under the configured root."""
    if not texture_path:
        return None
    if os.path.isfile(texture_path):
        return texture_path
    relative = texture_path.replace("\\", "/").lstrip("/")
    for root in _candidate_roots():
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            return candidate
    # Last resort: search by file name, but only under the (bounded) configured root —
    # never under P:\\, which could be an enormous tree.
    configured = texture_root()
    if configured and os.path.isdir(configured):
        base = os.path.basename(relative).lower()
        scanned = 0
        for dirpath, _dirs, files in os.walk(configured):
            scanned += 1
            if scanned > _WALK_DIR_LIMIT:
                break
            for name in files:
                if name.lower() == base:
                    return os.path.join(dirpath, name)
    return None
