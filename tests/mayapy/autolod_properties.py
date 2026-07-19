"""Auto LOD must not invent named properties (run with mayapy).

`1.000e+13` is the Geometry LOD's RESOLUTION SIGNATURE — the float that goes in the LOD's
resolution field and is how the format encodes "this is a Geometry LOD". In the Blender
add-on this repo was ported from, the string appears exactly once, as a key in the table
mapping signatures to LOD types (`io/data_p3d.py`); it is not a named property and that
add-on writes no property called "lod".

The port turned that table entry into `_set_named_properties(node, (("lod", "1.000e+13")))`,
so every generated Geometry LOD arrived in Object Builder carrying a junk property named
"lod". It is the same class of mistake as the `autocenter=0` artifact removed earlier.

Run:  mayapy.exe tests/mayapy/autolod_properties.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds


def properties_on(node):
    if not cmds.attributeQuery("a3obProperties", node=node, exists=True):
        return []
    raw = cmds.getAttr(node + ".a3obProperties") or ""
    return [chunk for chunk in raw.split(";") if chunk]


def new_scene():
    cmds.file(new=True, force=True)
    cmds.loadPlugin("MayaObjectBuilder.py", quiet=True)
    return cmds.polyCube(name="source", ch=False)[0]


def test_box_geometry_lod_has_no_invented_properties():
    source = new_scene()
    from a3ob.ui.autolod.lodgen import _generate_geometry_lod

    parent = cmds.createNode("transform", name="geometries")
    node = _generate_geometry_lod(
        source, {"geometry_type": "BOX", "geometry_name": "Geometry"}, parent)

    found = properties_on(node)
    _harness.check(found == [], "a generated Geometry LOD carries no named properties, got %r" % (found,))
    _harness.check(cmds.getAttr(node + ".a3obLodType") == 6, "it is still a Geometry LOD")


def test_empty_geometry_lod_has_no_invented_properties():
    source = new_scene()
    from a3ob.ui.autolod.lodgen import _generate_geometry_lod

    parent = cmds.createNode("transform", name="geometries")
    node = _generate_geometry_lod(
        source, {"geometry_type": "NONE", "geometry_name": "Geometry"}, parent)

    found = properties_on(node)
    _harness.check(found == [], "an empty Geometry LOD carries none either, got %r" % (found,))


def test_a_property_the_user_sets_is_still_kept():
    """Only the invented one goes; the panel must still be able to write properties."""
    new_scene()
    node = cmds.createNode("transform", name="Geometry")
    cmds.addAttr(node, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(node + ".a3obIsLOD", True)
    cmds.addAttr(node, longName="a3obLodType", attributeType="long")
    cmds.setAttr(node + ".a3obLodType", 6)
    cmds.addAttr(node, longName="a3obResolution", attributeType="long")

    cmds.select(node, replace=True)
    cmds.a3obNamedProperty(s="autocenter=0")
    _harness.check(properties_on(node) == ["autocenter=0"],
          "a deliberately set property must survive, got %r" % (properties_on(node),))


def main():
    test_box_geometry_lod_has_no_invented_properties()
    test_empty_geometry_lod_has_no_invented_properties()
    test_a_property_the_user_sets_is_still_kept()
    print("autolod properties: OK")


if __name__ == "__main__":
    sys.exit(_harness.run(main))
