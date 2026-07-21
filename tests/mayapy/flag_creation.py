"""Flag sets created from the Selections panel land in that panel's list (mayapy).

The premise of folding Flags into Selections: create_metadata_set writes a3obSelectionName
alongside a3obFlagComponent, and _selection_sets() skips sets WITHOUT a3obSelectionName. So a
flag set already passes the Selections filter and already carries a kind. If that ever stops
being true, this whole panel merge rests on nothing — which is what this test pins.

Run:  mayapy.exe tests/mayapy/flag_creation.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402

from a3ob.ui.scene.selections import selection_sets_for_owner  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_lod():
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    return transform


def test_a_face_flag_appears_in_the_selections_list_with_its_kind():
    lod = build_lod()
    cmds.select(lod + ".f[0:1]", replace=True)
    cmds.a3obSetFlag(component="face", value=8, name="hidden")

    rows = selection_sets_for_owner(lod)
    kinds = [row["kind"] for row in rows]
    check("Face Flag" in kinds,
          "a face flag set is not listed as 'Face Flag'; got kinds %r" % kinds)
    row = [item for item in rows if item["kind"] == "Face Flag"][0]
    check(row["name"] == "hidden", "flag row name is %r, expected 'hidden'" % row["name"])


def test_a_vertex_flag_is_listed_as_vertex_flag():
    lod = build_lod()
    cmds.select(lod + ".vtx[0:3]", replace=True)
    cmds.a3obSetFlag(component="vertex", value=1, name="soft")

    kinds = [row["kind"] for row in selection_sets_for_owner(lod)]
    check("Vertex Flag" in kinds,
          "a vertex flag set is not listed as 'Vertex Flag'; got kinds %r" % kinds)


def test_flag_sets_carry_a_selection_name():
    """The load-bearing premise: _selection_sets() drops any set without a3obSelectionName."""
    lod = build_lod()
    cmds.select(lod + ".f[0]", replace=True)
    cmds.a3obSetFlag(component="face", value=2, name="marker")

    flag_sets = [node for node in cmds.ls(type="objectSet") or []
                 if cmds.attributeQuery("a3obFlagComponent", node=node, exists=True)]
    check(len(flag_sets) == 1, "expected one flag set, got %r" % flag_sets)
    check(cmds.attributeQuery("a3obSelectionName", node=flag_sets[0], exists=True),
          "the flag set has no a3obSelectionName — it would vanish from the Selections list")


def main():
    _harness.load_plugin()
    for test in (test_a_face_flag_appears_in_the_selections_list_with_its_kind,
                 test_a_vertex_flag_is_listed_as_vertex_flag,
                 test_flag_sets_carry_a_selection_name):
        test()
        print("ok:", test.__name__, flush=True)
    print("FLAG CREATION: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
