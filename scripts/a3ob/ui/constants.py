"""Pure data tables for the MayaObjectBuilder UI — no Maya/Qt dependencies."""

UI_MARGIN = 8
UI_SPACING = 6

KNOWN_NAMED_PROPS = {
    "animated": [],
    "aicovers": ["0", "1"],
    "armor": [],
    "autocenter": ["0", "1"],
    "buoyancy": ["0", "1"],
    "cratercolor": [],
    "canbeoccluded": ["0", "1"],
    "canocclude": ["0", "1"],
    "class": [
        "breakablehouseanimated",
        "bridge",
        "building",
        "bushhard",
        "bushsoft",
        "church",
        "clutter",
        "forest",
        "house",
        "housesimulated",
        "land_decal",
        "man",
        "none",
        "pond",
        "road",
        "streetlamp",
        "thing",
        "thingx",
        "tower",
        "treehard",
        "treesoft",
        "vehicle",
        "wall"
    ],
    "damage": [
        "building",
        "engine",
        "no",
        "tent",
        "tree",
        "wall",
        "wreck"
    ],
    "destroysound": [
        "treebroadleaf",
        "treepalm"
    ],
    "drawimportance": [],
    "explosionshielding": [],
    "forcenotalpha": ["0", "1"],
    "frequent": ["0", "1"],
    "keyframe": ["0", "1"],
    "loddensitycoef": [],
    "lodnoshadow": ["0", "1"],
    "map": [
        "main road",
        "road",
        "track",
        "trail",
        "building",
        "fence",
        "wall",
        "bush",
        "small tree",
        "tree",
        "rock",
        "bunker",
        "fortress",
        "fuelstation",
        "hospital",
        "lighthouse",
        "quay",
        "view-tower",
        "ruin",
        "busstop",
        "church",
        "chapel",
        "cross",
        "fountain",
        "power lines",
        "powersolar",
        "powerwave",
        "powerwind",
        "railway",
        "shipwreck",
        "stack",
        "tourism",
        "transmitter",
        "watertower",
        "hide"
    ],
    "mass": [],
    "maxsegments": [],
    "minsegments": [],
    "notl": [],
    "placement": [
        "slope",
        "slopez",
        "slopex",
        "slopelandcontact",
        "vertical"
    ],
    "prefershadowvolume": ["0", "1"],
    "reversed": [],
    "sbsource": [
        "explicit",
        "none",
        "shadow",
        "shadowvolume",
        "visual",
        "visualex"
    ],
    "shadow": ["hybrid"],
    "shadowlod": [],
    "shadowvolumelod": [],
    "shadowbufferlod": [],
    "shadowbufferlodvis": [],
    "shadowoffset": [],
    "viewclass": [],
    "viewdensitycoef": [],
    "xcount": [],
    "xsize": [],
    "xstep": [],
    "ycount": [],
    "ysize": []
}

LOD_DEFINITIONS = [
    {"type": 0, "label": "Resolution", "has_resolution": True, "default_resolution": 1},
    {"type": 1, "label": "View Gunner", "has_resolution": False, "default_resolution": 0},
    {"type": 2, "label": "View Pilot", "has_resolution": False, "default_resolution": 0},
    {"type": 3, "label": "View Cargo", "has_resolution": True, "default_resolution": 1},
    {"type": 4, "label": "ShadowVolume", "has_resolution": True, "default_resolution": 0},
    {"type": 5, "label": "Edit", "has_resolution": True, "default_resolution": 0},
    {"type": 6, "label": "Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 7, "label": "Geometry Buoyancy", "has_resolution": False, "default_resolution": 0},
    {"type": 8, "label": "Geometry PhysX", "has_resolution": False, "default_resolution": 0},
    {"type": 9, "label": "Memory", "has_resolution": False, "default_resolution": 0},
    {"type": 10, "label": "LandContact", "has_resolution": False, "default_resolution": 0},
    {"type": 11, "label": "Roadway", "has_resolution": False, "default_resolution": 0},
    {"type": 12, "label": "Paths", "has_resolution": False, "default_resolution": 0},
    {"type": 13, "label": "HitPoints", "has_resolution": False, "default_resolution": 0},
    {"type": 14, "label": "View Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 15, "label": "Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 16, "label": "View Cargo Geometry", "has_resolution": True, "default_resolution": 1},
    {"type": 17, "label": "View Cargo Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 18, "label": "View Commander", "has_resolution": False, "default_resolution": 0},
    {"type": 19, "label": "View Commander Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 20, "label": "View Commander Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 21, "label": "View Pilot Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 22, "label": "View Pilot Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 23, "label": "View Gunner Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 24, "label": "View Gunner Fire Geometry", "has_resolution": False, "default_resolution": 0},
    {"type": 25, "label": "Subparts", "has_resolution": False, "default_resolution": 0},
    {"type": 26, "label": "Shadow View Cargo", "has_resolution": True, "default_resolution": 0},
    {"type": 27, "label": "Shadow View Pilot", "has_resolution": False, "default_resolution": 0},
    {"type": 28, "label": "Shadow View Gunner", "has_resolution": False, "default_resolution": 0},
    {"type": 29, "label": "Wreckage", "has_resolution": False, "default_resolution": 0},
    {"type": 30, "label": "Underground", "has_resolution": False, "default_resolution": 0},
    {"type": 31, "label": "GroundLayer", "has_resolution": False, "default_resolution": 0},
    {"type": 32, "label": "Navigation", "has_resolution": False, "default_resolution": 0},
]
LOD_TYPE_NAMES = {definition["type"]: definition["label"] for definition in LOD_DEFINITIONS}
RESOLUTION_LOD_TYPE = 0  # Resolution LOD: the only type carrying a numeric resolution
MEMORY_LOD_TYPE = 9      # Memory LOD: holds named locator points
# Geometry-family LOD types (mirrors the grouping in lod_type_icon below) — mass is
# USUAL here. It is never restricted to these types at export (a3obMassValues drives
# the mass TAGG regardless of a3obLodType), so this only decides whether the Mass
# detail area starts expanded or collapsed — never whether it exists or works.
GEOMETRY_FAMILY_LOD_TYPES = (6, 7, 8, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24)


def lod_type_icon(lod_type):
    """Maya resource icon for a LOD type, grouped by family (combo + LOD list rows)."""
    if lod_type == 0:
        return ":/polyMesh.png"                                  # Resolution
    if lod_type == 9:
        return ":/locator.png"                                   # Memory
    if lod_type in (1, 2, 3, 18):
        return ":/eye.png"                                       # View (gunner/pilot/cargo/commander)
    if lod_type in (4, 26, 27, 28):
        return ":/ghostOff.png"                                  # Shadow
    if lod_type in (6, 7, 8, 14, 15, 16, 17, 19, 20, 21, 22, 23, 24):
        return ":/polyCube.png"                                  # Geometry family
    return ":/out_mesh.png"


# One-line descriptions for the well-known DayZ/Arma named properties (combo tooltip).
NAMED_PROP_DESCRIPTIONS = {
    "autocenter": "Auto-center the model at import (0 = keep the authored origin).",
    "lodnoshadow": "1 = this LOD casts no shadow (pair it with a dedicated shadow LOD).",
    "buoyancy": "1 = the geometry participates in water buoyancy.",
    "class": "Object class (house, tree, vehicle, …) — drives engine behaviour.",
    "map": "Category/icon shown for the object on the in-game 2D map.",
    "damage": "Damage / destruction model class.",
    "sbsource": "Shadow-buffer source (visual / shadowvolume / explicit / none).",
    "prefershadowvolume": "1 = prefer stencil shadow volumes over the shadow buffer.",
    "forcenotalpha": "1 = force the LOD to render opaque (skip alpha sorting).",
    "canocclude": "1 = this geometry can occlude others (occlusion culling).",
    "canbeoccluded": "1 = this geometry can be occluded by others.",
    "frequent": "1 = frequently used LOD (engine LOD-switching hint).",
    "shadow": "Shadow mode (e.g. hybrid).",
    "loddensitycoef": "Density coefficient influencing LOD switch distance.",
}
