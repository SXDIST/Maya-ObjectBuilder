"""Triangle and vertex counts must not double on a skinned mesh (run with mayapy).

A skinned mesh keeps a hidden ``...ShapeOrig`` intermediate shape. Without
``noIntermediate=True``, ``listRelatives`` hands back both the real shape and the
orig, so every count is exactly doubled. This hits two display values and one
computation:

* The LOD-list triangle count is cosmetic but misleading.
* ``_lod_vertex_count`` is the divisor in the Mass From Volume formula
  (``volume * density / vertex_count``). A doubled divisor produces half the
  correct per-vertex mass. Any scene where a rigged model's mass was set through
  the UI has half the value it should — stored data is NOT migrated; only future
  calls are correct after this fix.

The test binds a cube to a single joint, which is enough to trigger the orig
shape, then asserts that counts before and after binding are equal.

Fails against the unfixed code: before fix, counts after binding are 2x the
pre-binding truth, so the assertion fails.

Run:  mayapy.exe tests/mayapy/lod_counts_ignore_intermediates.py
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import maya.standalone  # noqa: E402

maya.standalone.initialize()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.scene.lods import _lod_triangle_count  # noqa: E402
from a3ob.ui.actions.metadata import _lod_vertex_count  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def make_lod(name):
    transform = cmds.polyCube(name=name, ch=False)[0]
    cmds.addAttr(transform, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.addAttr(transform, longName="a3obLodType", attributeType="long")
    cmds.addAttr(transform, longName="a3obResolution", attributeType="long")
    return cmds.ls(transform, long=True)[0]


def test_counts_unchanged_by_skincluster():
    """Vertex and triangle counts must be the same before and after binding."""
    cmds.file(new=True, force=True)
    lod = make_lod("body")

    verts_before = _lod_vertex_count(lod)
    tris_before = _lod_triangle_count(lod)

    # Sanity check the fixture counts: a polyCube has 8 verts and 12 tris.
    check(verts_before == 8, f"fixture: expected 8 verts, got {verts_before}")
    check(tris_before == 12, f"fixture: expected 12 tris, got {tris_before}")

    # Bind to a joint — this is what creates the hidden ShapeOrig.
    cmds.select(clear=True)
    joint = cmds.joint(position=(0, 0, 0), name="Root")
    cmds.skinCluster(joint, lod, toSelectedBones=True)

    # Verify the fixture actually has an intermediate shape, or the test proves nothing.
    shapes = cmds.listRelatives(lod, shapes=True, fullPath=True) or []
    intermediates = [s for s in shapes if cmds.getAttr(s + ".intermediateObject")]
    check(intermediates,
          f"fixture needs a ShapeOrig after skinCluster, got shapes {shapes!r}")

    verts_after = _lod_vertex_count(lod)
    tris_after = _lod_triangle_count(lod)

    check(verts_after == verts_before,
          f"vertex count must not change when a skinCluster is added: "
          f"before={verts_before}, after={verts_after} "
          f"(doubled = intermediate shape not filtered)")
    check(tris_after == tris_before,
          f"triangle count must not change when a skinCluster is added: "
          f"before={tris_before}, after={tris_after} "
          f"(doubled = intermediate shape not filtered)")


def test_mass_from_volume_divisor_is_stable():
    """The per-vertex mass must not halve when a rig is added.

    mass_from_volume_from_ui computes  volume * density / vertex_count.
    If vertex_count doubles after binding, every call assigns half the correct
    mass to the LOD.  The fix is a pre-condition for any rigged model's mass
    being usable at all.
    """
    cmds.file(new=True, force=True)
    lod = make_lod("armour")

    count_before = _lod_vertex_count(lod)

    # Bind — creates the intermediate shape.
    cmds.select(clear=True)
    joint = cmds.joint(position=(0, 0, 0), name="Root")
    cmds.skinCluster(joint, lod, toSelectedBones=True)

    count_after = _lod_vertex_count(lod)

    # The mass formula is  total / count.  If count_after != count_before the
    # per-vertex mass would be wrong by exactly that ratio.
    check(count_after == count_before,
          f"_lod_vertex_count changed after skinCluster ({count_before} -> {count_after}): "
          f"Mass From Volume would assign {count_before / count_after:.2f}x the correct mass")


def test_nested_mesh_inside_lod_is_counted():
    """A mesh parented under a group under the LOD is still included in the count.

    Regression guard: the allDescendents flag must not be replaced with shapes=True,
    which only looks one level deep and misses deeply nested meshes."""
    cmds.file(new=True, force=True)
    lod = make_lod("vehicle")
    grp = cmds.group(empty=True, name="body_parts", parent=lod)
    # Create a separate cube and reparent it under the group.
    inner = cmds.polyCube(name="wheel", ch=False)[0]
    cmds.parent(inner, grp)

    verts = _lod_vertex_count(lod)
    tris = _lod_triangle_count(lod)

    # The LOD's own cube (8v, 12t) + the nested cube (8v, 12t).
    check(verts == 16, f"expected 16 verts (two cubes), got {verts}")
    check(tris == 24, f"expected 24 tris (two cubes), got {tris}")


def main():
    test_counts_unchanged_by_skincluster()
    test_mass_from_volume_divisor_is_stable()
    test_nested_mesh_inside_lod_is_counted()
    print("lod counts ignore intermediates: OK")


if __name__ == "__main__":
    main()
    sys.exit(0)
