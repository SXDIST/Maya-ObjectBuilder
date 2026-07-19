"""Influence-name rules — pure Python, no Maya.

The mask decides what the dock's influence list shows, and the removability rule is the
only thing standing between a broad selection and a mesh with no influences left (which
cannot deform at all). Both are pure string logic, so they get a fast test here rather
than a Maya one.

Run:  python tests/python/test_influences.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "scripts"))

from a3ob.mayabridge.influences import leaf_name, match_names, removable


def check(condition, message):
    if not condition:
        raise AssertionError(message)


BONES = [
    "|Pelvis|Spine|Neck|Head",
    "|Pelvis|Spine|Neck",
    "rig:Face_Jawbone",
    "Face_Chin",
    "EyeLeft",
    "LeftHand",
]


def test_leaf_name():
    check(leaf_name("|Pelvis|Spine|Neck|Head") == "Head", "DAG path must reduce to the leaf")
    check(leaf_name("rig:Face_Jawbone") == "Face_Jawbone", "namespace must be stripped")
    check(leaf_name("LeftHand") == "LeftHand", "a bare name must survive unchanged")
    print("OK leaf_name strips paths and namespaces")


def test_match_names():
    check(match_names(BONES, "Face_*") == ["rig:Face_Jawbone", "Face_Chin"],
          "mask must match on the leaf, keeping the original name")
    check(match_names(BONES, "Eye*") == ["EyeLeft"], "Eye* must match the eye only")
    check(match_names(BONES, "Nothing*") == [], "a mask with no match must return nothing")
    print("OK match_names filters on the leaf name")


def test_empty_mask_matches_nothing():
    # An empty filter box must never arm a control that would strip an entire rig.
    check(match_names(BONES, "") == [], "an empty mask must match NOTHING, not everything")
    check(match_names(BONES, None) == [], "a missing mask must match nothing too")
    print("OK an empty mask matches nothing")


def test_removable_keeps_one():
    allowed, reason = removable(BONES, ["Face_Chin", "EyeLeft"])
    check(allowed == ["Face_Chin", "EyeLeft"], "requested bones present must be removable")
    check(reason == "", "a valid request needs no reason, got %r" % (reason,))

    allowed, reason = removable(BONES, list(BONES))
    check(allowed == [], "removing every influence must be refused")
    check("at least one" in reason, "the refusal must explain itself, got %r" % (reason,))

    allowed, reason = removable(BONES, ["NotOnThisMesh"])
    check(allowed == [], "bones that are not influences must not be reported as removable")
    check(reason, "an empty request must explain itself")
    print("OK removable refuses to strip the last influence")


def main():
    test_leaf_name()
    test_match_names()
    test_empty_mask_matches_nothing()
    test_removable_keeps_one()
    print("influence tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
