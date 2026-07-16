"""settings."""

from maya import cmds
from maya import mel





RESOLUTION_PRESETS = {
    "CUSTOM": (0.75, 0.55, 0.38, 0.22),
    "TRIS": (0.82, 0.65, 0.48, 0.30),
    "QUADS": (0.70, 0.50, 0.33, 0.20),
}


DEFAULT_SETTINGS = {
    "resolution": True,
    "geometry": True,
    "memory": False,
    "fire_geometry": False,
    "view_geometry": False,
    "preset": "QUADS",
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
    for key, value in (settings or {}).items():
        if key == "memory_points":
            merged["memory_points"].update(value or {})
        else:
            merged[key] = value
    return merged


__all__ = [
    "RESOLUTION_PRESETS",
    "DEFAULT_SETTINGS",
    "_merged_settings",
]
