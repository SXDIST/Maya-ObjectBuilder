"""settings."""





def _geometric_ladder(step, levels=4):
    # Each successive LOD keeps ``step`` of the PREVIOUS LOD's triangles, i.e. a clean
    # geometric decimation ladder (ratios are relative to the full-res base, so level i
    # keeps step**i). This matches how a decimate/LOD chain is expected to fall off,
    # instead of the former hand-tuned absolute ratios.
    return tuple(round(step ** i, 4) for i in range(1, levels + 1))


# Reduction strength = per-step retention of the previous LOD's triangles.
#   aggressive = 0.50 -> (0.5, 0.25, 0.125, 0.0625)   standard halving, light distant LODs
#   balanced   = 0.60 -> (0.6, 0.36, 0.216, 0.1296)   gentler falloff
#   light      = 0.70 -> (0.7, 0.49, 0.343, 0.2401)   minimal reduction per step
REDUCTION_FACTORS = {"aggressive": 0.50, "balanced": 0.60, "light": 0.70}

# Legacy single "preset" -> (output, reduction), so old calls / tests keep working.
_PRESET_COMPAT = {
    "QUADS": ("quads", "aggressive"),
    "TRIS": ("triangles", "balanced"),
    "CUSTOM": ("triangles", "light"),
}

# Back-compat table (still used if anything reads RESOLUTION_PRESETS directly).
RESOLUTION_PRESETS = {
    "QUADS": _geometric_ladder(0.50),
    "TRIS": _geometric_ladder(0.60),
    "CUSTOM": _geometric_ladder(0.70),
}


def reduction_ladder(reduction):
    return _geometric_ladder(REDUCTION_FACTORS.get(reduction, 0.50))


DEFAULT_SETTINGS = {
    "resolution": True,
    "geometry": True,
    "memory": False,
    "fire_geometry": False,
    "view_geometry": False,
    "output": "quads",          # quads | triangles — the LOD face type
    "reduction": "aggressive",  # aggressive | balanced | light — per-step strength
    "first_lod": "LOD1",
    "lod_prefix": "Resolution ",
    "geometry_type": "BOX",
    "geometry_name": "Geometry",
    "view_geometry_name": "View Geometry",
    "fire_quality": 2,
    "memory_points": {
        "invview": True,
        "bounding_box": True,
        "radius": True,
        "center": True,
    },
}


def _merged_settings(settings):
    merged = dict(DEFAULT_SETTINGS)
    merged["memory_points"] = dict(DEFAULT_SETTINGS["memory_points"])
    settings = settings or {}
    # Legacy: derive output/reduction from a single "preset" when the new keys are absent.
    if "preset" in settings and "output" not in settings and "reduction" not in settings:
        out, red = _PRESET_COMPAT.get(settings["preset"], ("quads", "aggressive"))
        merged["output"], merged["reduction"] = out, red
    for key, value in settings.items():
        if key == "memory_points":
            merged["memory_points"].update(value or {})
        else:
            merged[key] = value
    return merged


__all__ = [
    "RESOLUTION_PRESETS",
    "REDUCTION_FACTORS",
    "reduction_ladder",
    "DEFAULT_SETTINGS",
    "_merged_settings",
]
