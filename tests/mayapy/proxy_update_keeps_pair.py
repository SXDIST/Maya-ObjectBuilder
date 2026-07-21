"""a3obUpdateProxy must leave the placeholder and its selection set agreeing (mayapy).

A proxy is two nodes keyed by the same string, proxy:PATH.INDEX: a placeholder transform
under the LOD and an objectSet holding its components. a3obProxy writes both. Before this
test, a3obUpdateProxy updated only whichever half happened to be selected, so correcting a
path renamed the set while the placeholder still pointed at the old proxy — a state
a3obValidate reports as "proxy placeholder has no matching selection set".

Run:  mayapy.exe tests/mayapy/proxy_update_keeps_pair.py
"""

import sys

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def build_proxy(path="p\\weapon.p3d", index=1):
    """A LOD with a mesh, and a proxy built from two of its faces."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.setAttr(transform + ".a3obResolution", 1)
    cmds.select(transform + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
    return transform


def placeholder_under(lod):
    for child in cmds.listRelatives(lod, children=True, type="transform", fullPath=True) or []:
        if cmds.attributeQuery("a3obIsProxy", node=child, exists=True):
            return child
    return None


def proxy_sets():
    return [node for node in cmds.ls(type="objectSet") or []
            if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]


def pair_state(lod):
    """(placeholder path, placeholder index, placeholder's selection name, set's name)."""
    placeholder = placeholder_under(lod)
    check(placeholder is not None, "no proxy placeholder was created")
    sets = proxy_sets()
    check(len(sets) == 1, "expected exactly one proxy selection set, got %r" % sets)
    return (cmds.getAttr(placeholder + ".a3obProxyPath"),
            cmds.getAttr(placeholder + ".a3obProxyIndex"),
            cmds.getAttr(placeholder + ".a3obProxySelection"),
            cmds.getAttr(sets[0] + ".a3obSelectionName"))


def test_update_via_the_placeholder_also_renames_the_set():
    lod = build_proxy()
    cmds.select(placeholder_under(lod), replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    path, index, placeholder_selection, set_selection = pair_state(lod)
    check(path == "p\\other.p3d", "placeholder path not updated: %r" % path)
    check(index == 4, "placeholder index not updated: %r" % index)
    check(placeholder_selection == "proxy:p\\other.p3d.4",
          "placeholder selection name not updated: %r" % placeholder_selection)
    check(set_selection == placeholder_selection,
          "the set still names %r while the placeholder names %r"
          % (set_selection, placeholder_selection))


def test_update_via_the_set_also_repoints_the_placeholder():
    lod = build_proxy()
    # noExpand: selecting a set by name normally selects its MEMBERS (that is how "quick
    # select sets" work), not the set node itself — a3obUpdateProxy needs the node.
    cmds.select(proxy_sets()[0], replace=True, noExpand=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    path, index, placeholder_selection, set_selection = pair_state(lod)
    check(set_selection == "proxy:p\\other.p3d.4",
          "set selection name not updated: %r" % set_selection)
    check(path == "p\\other.p3d",
          "the placeholder still points at %r after updating through the set" % path)
    check(index == 4, "placeholder index not updated: %r" % index)
    check(placeholder_selection == set_selection,
          "the placeholder names %r while the set names %r"
          % (placeholder_selection, set_selection))


def test_update_creates_no_extra_set_and_leaves_no_orphan():
    lod = build_proxy()
    before = len(cmds.ls(type="objectSet") or [])
    cmds.select(placeholder_under(lod), replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)
    after = len(cmds.ls(type="objectSet") or [])
    check(before == after, "set count changed from %d to %d — an orphan was left behind"
                           % (before, after))


def test_a_placeholder_with_no_set_still_updates():
    """fromSelection=False builds a placeholder alone. Syncing must not require a set."""
    cmds.file(new=True, force=True)
    transform = cmds.polyCube(name="body", ch=False)[0]
    for attribute, kind in (("a3obIsLOD", "bool"), ("a3obLodType", "long"),
                            ("a3obResolution", "long")):
        cmds.addAttr(transform, longName=attribute, attributeType=kind)
    cmds.setAttr(transform + ".a3obIsLOD", True)
    cmds.select(transform, replace=True)
    cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=False, update=True)

    placeholder = placeholder_under(transform)
    check(placeholder is not None, "no placeholder was created")
    check(proxy_sets() == [], "fromSelection=False should create no set")

    cmds.select(placeholder, replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=2)
    check(cmds.getAttr(placeholder + ".a3obProxyPath") == "p\\other.p3d",
          "a placeholder without a set failed to update")


def main():
    _harness.load_plugin()
    for test in (test_update_via_the_placeholder_also_renames_the_set,
                 test_update_via_the_set_also_repoints_the_placeholder,
                 test_update_creates_no_extra_set_and_leaves_no_orphan,
                 test_a_placeholder_with_no_set_still_updates):
        test()
        print("ok:", test.__name__, flush=True)
    print("PROXY UPDATE PAIR: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
