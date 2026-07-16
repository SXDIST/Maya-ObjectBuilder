from maya import cmds
from maya import mel


from a3ob.ui.autolod.helpers import *  # noqa: F401,F403
from a3ob.ui.autolod.lodgen import *  # noqa: F401,F403

def generate_auto_lods(settings=None):
    settings = _merged_settings(settings)
    source = _selected_source_transform()
    if not source:
        cmds.warning("Select a source mesh before generating Auto LODs")
        return []

    generated = []

    # Resolution generation renames/consumes the source into LOD1, so preserve a
    # snapshot of the original geometry for the geometry/view/fire/memory generators
    # (which only read its bounding box) when both families are requested.
    geometry_source = source
    geometry_snapshot = None
    needs_geometry_source = settings["geometry"] or settings["view_geometry"] or settings["fire_geometry"] or settings["memory"]
    if settings["resolution"] and needs_geometry_source:
        geometry_snapshot = cmds.duplicate(source, name="__auto_lod_geometry_source", returnRootsOnly=True)[0]
        cmds.setAttr(geometry_snapshot + ".visibility", False)
        geometry_source = geometry_snapshot

    if settings["resolution"]:
        generated.extend(_generate_resolution_lods(source, settings, _group("visuals")))
    if settings["geometry"] or settings["view_geometry"] or settings["fire_geometry"]:
        geometries = _group("geometries")
        if settings["geometry"]:
            generated.append(_generate_geometry_lod(geometry_source, settings, geometries))
        if settings["view_geometry"]:
            generated.append(_generate_view_geometry_lod(geometry_source, settings, geometries))
        if settings["fire_geometry"]:
            generated.append(_generate_fire_geometry_lod(geometry_source, settings, geometries))
    if settings["memory"]:
        generated.append(_generate_memory_lod(geometry_source, settings, _group("point_clouds")))

    if geometry_snapshot and cmds.objExists(geometry_snapshot):
        cmds.delete(geometry_snapshot)

    generated = [node for node in generated if node and cmds.objExists(node)]
    if generated:
        generated = [(cmds.ls(node, long=True) or [node])[0] for node in generated]
        cmds.select(generated, replace=True)
    return generated


__all__ = [
    "generate_auto_lods",
]
