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


def resolve_paa_path_with_source(texture_path):
    """Resolve a P3D texture path, and report WHICH strategy found it.

    Returns (path or None, source) where source is "absolute", "configured", "drive",
    "search" or "" — the Preferences window states this, because a configured root that does
    not exist otherwise fails silently while P:/ quietly does the work."""
    if not texture_path:
        return None, ""
    if os.path.isfile(texture_path):
        return texture_path, "absolute"
    relative = texture_path.replace("\\", "/").lstrip("/")
    configured = texture_root()
    for root in _candidate_roots():
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            same = configured and os.path.normcase(os.path.abspath(root)) == os.path.normcase(
                os.path.abspath(configured))
            return candidate, "configured" if same else "drive"
    # Last resort: search by file name, but only under the (bounded) configured root —
    # never under P:\\, which could be an enormous tree.
    if configured and os.path.isdir(configured):
        base = os.path.basename(relative).lower()
        scanned = 0
        for dirpath, _dirs, files in os.walk(configured):
            scanned += 1
            if scanned > _WALK_DIR_LIMIT:
                break
            for name in files:
                if name.lower() == base:
                    return os.path.join(dirpath, name), "search"
    return None, ""


def resolve_paa_path(texture_path):
    """Resolve a P3D texture path to a real file, or None. The import pipeline's entry point;
    signature and answer unchanged — see resolve_paa_path_with_source for the reasoning."""
    return resolve_paa_path_with_source(texture_path)[0]
