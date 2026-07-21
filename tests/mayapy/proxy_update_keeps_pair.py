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
    transform = _harness.make_lod("body", resolution=1)
    cmds.select(transform + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
    return transform


def build_two_lod_model(path="p\\weapon.p3d", index=1):
    """Two LODs of one model, each carrying the SAME proxy — the ordinary multi-LOD case.

    ``proxy_selection_name`` encodes no LOD identity: both placeholders and both sets read
    ``proxy:p\\weapon.p3d.1``. Any counterpart lookup that scans the scene and takes the
    first match will therefore cross LOD boundaries.

    Both LODs are built through a3obProxy itself: its set-creation gate is scoped per-LOD
    (task 1b), so it now builds both LODs' sets without help — this fixture no longer needs
    to hand-build the second one the way import does.
    """
    cmds.file(new=True, force=True)
    first = _harness.make_lod("res1", resolution=1)
    cmds.select(first + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)

    second = _harness.make_lod("res2", resolution=2)
    cmds.select(second + ".f[0:1]", replace=True)
    cmds.a3obProxy(path=path, index=index, fromSelection=True, update=True)
    return first, second


def set_for_lod(lod):
    """The proxy selection set whose members live under ``lod``.

    Keyed on membership, not on the node name: the whole point of the test is that the
    names and the a3obSelectionName strings are ambiguous across LODs.
    """
    meshes = set(cmds.listRelatives(lod, children=True, type="mesh", fullPath=True) or [])
    for node in proxy_sets():
        for member in cmds.sets(node, query=True) or []:
            for obj in cmds.ls(member, objectsOnly=True, long=True) or []:
                if obj in meshes:
                    return node
    return None


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
    """A standing guard for the orphan-set rule — NOT evidence that the pair fix works.

    sync_proxy_pair only ever renames sets that already exist, so this count is invariant
    under every implementation of it, correct or not: it passes identically with the pair
    fix reverted. What it does catch is a future edit that starts CREATING a counterpart
    set instead of finding one, which is how a3obProxy/a3obUpdateProxy used to leave orphan
    a3ob_proxy_* nodes behind. The pair behaviour is proved by the two tests above and by
    test_updating_one_lod_leaves_the_other_lods_pair_alone.
    """
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
    transform = _harness.make_lod("body")
    cmds.select(transform, replace=True)
    cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=False, update=True)

    placeholder = placeholder_under(transform)
    check(placeholder is not None, "no placeholder was created")
    check(proxy_sets() == [], "fromSelection=False should create no set")

    cmds.select(placeholder, replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=2)
    check(cmds.getAttr(placeholder + ".a3obProxyPath") == "p\\other.p3d",
          "a placeholder without a set failed to update")


OLD_NAME = "proxy:p\\weapon.p3d.1"
NEW_NAME = "proxy:p\\other.p3d.4"


def _check_only_this_lod_moved(target, other, label, other_label):
    """After an update through ``target``, both of ``target``'s halves moved and neither of
    ``other``'s did."""
    target_selection = cmds.getAttr(placeholder_under(target) + ".a3obProxySelection")
    check(target_selection == NEW_NAME,
          "%s's own placeholder was left stale at %r" % (label, target_selection))
    target_set = set_for_lod(target)
    check(target_set is not None, "%s's set vanished" % label)
    target_set_name = cmds.getAttr(target_set + ".a3obSelectionName")
    check(target_set_name == NEW_NAME,
          "%s's own set was left stale at %r" % (label, target_set_name))

    other_selection = cmds.getAttr(placeholder_under(other) + ".a3obProxySelection")
    check(other_selection == OLD_NAME,
          "updating %s changed %s's placeholder to %r — a LOD the user never selected"
          % (label, other_label, other_selection))
    other_set = set_for_lod(other)
    check(other_set is not None, "%s's set vanished" % other_label)
    other_set_name = cmds.getAttr(other_set + ".a3obSelectionName")
    check(other_set_name == OLD_NAME,
          "updating %s retagged %s's set to %r — a LOD the user never selected"
          % (label, other_label, other_set_name))


def test_updating_one_lod_leaves_the_other_lods_pair_alone():
    """The counterpart must be found INSIDE the selected node's LOD, not scene-wide.

    Both LODs carry proxy:p\\weapon.p3d.1. A first-match scan of the whole scene updates
    the selected placeholder and then renames whichever set it happens to reach first —
    leaving one LOD's placeholder with no matching set (the exact a3obValidate failure this
    task exists to eliminate) and the other's set stale. This is the ordinary multi-LOD
    model, not an edge case.

    Both LODs are driven in turn deliberately: a scene-wide first match is right by luck
    for exactly one of them, so testing a single direction can pass against broken code.
    """
    for target_index in (0, 1):
        lods = build_two_lod_model()
        target, other = lods[target_index], lods[1 - target_index]
        labels = ("res1", "res2")
        cmds.select(placeholder_under(target), replace=True)
        cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)
        _check_only_this_lod_moved(target, other, labels[target_index],
                                   labels[1 - target_index])


def test_updating_through_one_lods_set_leaves_the_other_lod_alone():
    """Same ambiguity, entered from the set half: the set resolves its LOD by membership."""
    for target_index in (0, 1):
        lods = build_two_lod_model()
        target, other = lods[target_index], lods[1 - target_index]
        labels = ("res1", "res2")
        # noExpand: selecting a set by name normally selects its MEMBERS, not the set node.
        cmds.select(set_for_lod(target), replace=True, noExpand=True)
        cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)
        _check_only_this_lod_moved(target, other, labels[target_index],
                                   labels[1 - target_index])


def test_a_set_whose_members_are_gone_touches_nothing():
    """No members means no LOD means no counterpart — a silent no-op beats a stranger.

    The set still has to update ITSELF; it simply must not go hunting scene-wide for a
    placeholder it can no longer prove it owns.
    """
    first, second = build_two_lod_model()
    orphan = set_for_lod(second)
    cmds.sets(clear=orphan)
    # By UUID: updating the set RENAMES it, so the name captured here goes stale.
    orphan_uuid = cmds.ls(orphan, uuid=True)[0]
    cmds.select(orphan, replace=True, noExpand=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    orphan = cmds.ls(orphan_uuid)[0]
    check(cmds.getAttr(orphan + ".a3obSelectionName") == NEW_NAME,
          "the selected set itself was not updated")
    for lod, label in ((first, "res1"), (second, "res2")):
        selection = cmds.getAttr(placeholder_under(lod) + ".a3obProxySelection")
        check(selection == OLD_NAME,
              "a memberless set repointed %s's placeholder to %r" % (label, selection))


def test_a_proxy_inside_a_namespace_still_syncs():
    """cmds.ls("*.attr") does not recurse into namespaces; MItDependencyNodes does.

    A proxy in a referenced file or imported into a namespace was invisible to the
    counterpart lookup, and the failure was silent — the set was simply never found and the
    pair was left disagreeing with no error at all.
    """
    cmds.file(new=True, force=True)
    cmds.namespace(add="ref")
    cmds.namespace(set="ref")
    try:
        lod = _harness.make_lod("body", resolution=1)
        cmds.select(lod + ".f[0:1]", replace=True)
        cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=True, update=True)
    finally:
        cmds.namespace(set=":")

    placeholder = placeholder_under(lod)
    check(placeholder is not None, "no placeholder was created inside the namespace")
    check(":" in placeholder, "fixture built no namespaced node: %r" % placeholder)
    sets = proxy_sets()
    check(len(sets) == 1, "expected one namespaced proxy set, got %r" % sets)

    cmds.select(placeholder, replace=True)
    cmds.a3obUpdateProxy(path="p\\other.p3d", index=4)

    selection = cmds.getAttr(placeholder_under(lod) + ".a3obProxySelection")
    check(selection == NEW_NAME, "namespaced placeholder not updated: %r" % selection)
    set_name = cmds.getAttr(proxy_sets()[0] + ".a3obSelectionName")
    check(set_name == NEW_NAME,
          "the namespaced set was never found, so it still names %r" % set_name)


def test_the_same_proxy_can_be_added_to_a_second_lod():
    """a3obProxy's set-creation gate must be per-LOD, not scene-wide.

    proxy_selection_name encodes no LOD identity, so res1 and res2 both key on
    "proxy:p\\weapon.p3d.1". A scene-wide existence check therefore sees res1's set and
    skips creating res2's — leaving res2 with a placeholder and no set, which is exactly
    what a3obValidate reports as "proxy placeholder has no matching selection set"."""
    cmds.file(new=True, force=True)
    res1 = _harness.make_lod("res1", resolution=1)
    res2 = _harness.make_lod("res2", resolution=2)

    for lod in (res1, res2):
        cmds.select(lod + ".f[0:1]", replace=True)
        cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=True, update=True)

    for lod in (res1, res2):
        placeholder = None
        for child in cmds.listRelatives(lod, children=True, type="transform",
                                        fullPath=True) or []:
            if cmds.attributeQuery("a3obIsProxy", node=child, exists=True):
                placeholder = child
        check(placeholder is not None, "%s has no proxy placeholder" % lod)

    proxy_sets = [node for node in cmds.ls(type="objectSet") or []
                  if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]
    check(len(proxy_sets) == 2,
          "expected one proxy set per LOD, got %d: %r" % (len(proxy_sets), proxy_sets))


def test_adding_the_same_proxy_twice_to_ONE_lod_still_creates_one_set():
    """The gate must stay a gate. Re-running a3obProxy on the same LOD with the same path
    and index must not stack a second set on top of the first — that is the duplicate this
    check exists to prevent, and scoping it per-LOD must not lose it."""
    cmds.file(new=True, force=True)
    lod = _harness.make_lod("res1", resolution=1)

    for _ in range(2):
        cmds.select(lod + ".f[0:1]", replace=True)
        cmds.a3obProxy(path="p\\weapon.p3d", index=1, fromSelection=True, update=True)

    proxy_sets = [node for node in cmds.ls(type="objectSet") or []
                  if cmds.attributeQuery("a3obIsProxySelection", node=node, exists=True)]
    check(len(proxy_sets) == 1,
          "re-running a3obProxy on one LOD made %d sets: %r" % (len(proxy_sets), proxy_sets))


def main():
    _harness.load_plugin()
    for test in (test_update_via_the_placeholder_also_renames_the_set,
                 test_update_via_the_set_also_repoints_the_placeholder,
                 test_update_creates_no_extra_set_and_leaves_no_orphan,
                 test_a_placeholder_with_no_set_still_updates,
                 test_updating_one_lod_leaves_the_other_lods_pair_alone,
                 test_updating_through_one_lods_set_leaves_the_other_lod_alone,
                 test_a_set_whose_members_are_gone_touches_nothing,
                 test_a_proxy_inside_a_namespace_still_syncs,
                 test_the_same_proxy_can_be_added_to_a_second_lod,
                 test_adding_the_same_proxy_twice_to_ONE_lod_still_creates_one_set):
        test()
        print("ok:", test.__name__, flush=True)
    print("PROXY UPDATE PAIR: PASS", flush=True)


if __name__ == "__main__":
    try:
        main()
    except AssertionError as error:
        print("FAIL:", error, flush=True)
        sys.exit(1)
