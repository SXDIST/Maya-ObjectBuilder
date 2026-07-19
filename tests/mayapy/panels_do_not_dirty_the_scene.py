"""Panel reads must not mutate scene state (mayapy).

``_selection_sets()`` is reached from ``selection_sets_for_owner()`` on every
``SelectionChanged`` (debounced, but still fired per component-selection step on a dense
mesh).  Before the fix it unconditionally called ``_normalize_object_builder_sets()``,
which ran ``cmds.addAttr`` + ``cmds.setAttr`` on every a3ob* objectSet on every dock
refresh.  Those writes dirty the scene file even though undo is suppressed, so Maya
prompts "Save changes?" on close after a purely read-only session.

Run:  mayapy.exe tests/mayapy/panels_do_not_dirty_the_scene.py
"""

import os
import sys
import tempfile

import _harness

_harness.bootstrap()

import maya.cmds as cmds

from a3ob.ui.scene.selections import _selection_sets, selection_sets_for_owner


def _snapshot_a3ob_attrs(set_node):
    """Dict of every a3ob* attribute (plus hiddenInOutliner) on set_node."""
    snapshot = {}
    for attr_name in cmds.listAttr(set_node) or []:
        if attr_name.startswith("a3ob") or attr_name == "hiddenInOutliner":
            try:
                snapshot[attr_name] = cmds.getAttr(f"{set_node}.{attr_name}")
            except Exception:
                pass
    return snapshot


def _make_bare_selection_set(mesh_node, name):
    """A set with only ``a3obSelectionName`` — the minimal / old-style a3ob set form.

    The normalization pass that ran inside ``_selection_sets()`` would add
    ``a3obTechnicalSet`` and write ``hiddenInOutliner``, dirtying the scene.
    This is the exact form that ``dock_panel_sync.py:make_selection_set`` produces
    so the two tests share the same fixture.
    """
    shape = cmds.listRelatives(mesh_node, shapes=True)[0]
    node = cmds.sets(f"{shape}.f[0:2]", name=name)
    cmds.addAttr(node, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(node + ".a3obSelectionName", name, type="string")
    return node


def test_panel_refresh_does_not_dirty_the_scene():
    """Calling ``_selection_sets()`` twice must not mark the scene modified.

    The fixture deliberately creates a bare set (no ``a3obTechnicalSet``) so that the
    old normalization code would add the attribute, changing both the attribute dump
    AND the scene-modified flag.  After the fix neither changes.
    """
    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="test_mesh", ch=False)[0]
    set_node = _make_bare_selection_set(mesh, "a3ob_SEL_camo")

    before = _snapshot_a3ob_attrs(set_node)

    path = os.path.join(tempfile.gettempdir(), "panels_no_dirty.ma")
    cmds.file(rename=path)
    cmds.file(save=True, type="mayaAscii")
    _harness.check(not cmds.file(query=True, modified=True),
          "scene must be clean right after saving")

    # Simulate two SelectionChanged-driven dock refreshes.
    _selection_sets()
    _selection_sets()
    lod_owner = cmds.ls(mesh, long=True)[0]
    selection_sets_for_owner(lod_owner)
    selection_sets_for_owner(lod_owner)

    _harness.check(not cmds.file(query=True, modified=True),
          "panel refresh must not mark the scene modified "
          "(normalization must not run on every query)")

    after = _snapshot_a3ob_attrs(set_node)
    _harness.check(before == after,
          f"a3ob* attrs must not change during a panel refresh, "
          f"before={before!r} after={after!r}")


def test_sets_created_through_write_path_are_hidden():
    """Sets made by the normal create path must be hidden — behaviour moved, not lost.

    Every set-creation site calls ``attr.mark_technical_set()`` or the equivalent
    cmds-based ``_hide_object_builder_set()`` at write time.  This test proves that
    the hiding works without any panel refresh being required.
    """
    import maya.api.OpenMaya as om
    from a3ob.mayabridge import attributes as attr

    cmds.file(new=True, force=True)
    mesh = cmds.polyCube(name="write_path_mesh", ch=False)[0]
    shape = cmds.listRelatives(mesh, shapes=True)[0]

    set_name = cmds.sets(f"{shape}.f[0:2]", name="a3ob_SEL_write_path")
    cmds.addAttr(set_name, longName="a3obSelectionName", dataType="string")
    cmds.setAttr(set_name + ".a3obSelectionName", "write_path", type="string")

    sel = om.MSelectionList()
    sel.add(set_name)
    set_obj = sel.getDependNode(0)
    attr.mark_technical_set(set_obj)

    _harness.check(cmds.attributeQuery("a3obTechnicalSet", node=set_name, exists=True),
          "mark_technical_set must add a3obTechnicalSet")
    _harness.check(bool(cmds.getAttr(set_name + ".a3obTechnicalSet")),
          "a3obTechnicalSet must be True after mark_technical_set")
    if cmds.attributeQuery("hiddenInOutliner", node=set_name, exists=True):
        _harness.check(bool(cmds.getAttr(set_name + ".hiddenInOutliner")),
              "hiddenInOutliner must be True after mark_technical_set")


def test_find_components_marks_its_sets_technical():
    """The real write path, not the helper in isolation.

    ``test_sets_created_through_write_path_are_hidden`` calls
    ``mark_technical_set()`` itself and then asserts it worked, so it passes whether
    or not any command actually calls it. a3obFindComponents was the one creation
    site that did NOT — it built component sets and left them unmarked, which is
    only visible once the panel refresh stops covering for it. Drive the command.
    """
    plugin = os.path.join(_harness.REPO, "plug-ins", "MayaObjectBuilder.py")
    if not cmds.pluginInfo(plugin, query=True, loaded=True):
        cmds.loadPlugin(plugin)

    cmds.file(new=True, force=True)
    lod = cmds.polyCube(name="components_lod", ch=False)[0]
    cmds.addAttr(lod, longName="a3obIsLOD", attributeType="bool")
    cmds.setAttr(lod + ".a3obIsLOD", True)

    cmds.select(lod, replace=True)
    cmds.a3obFindComponents()

    created = [node for node in cmds.ls(type="objectSet") or []
               if node.startswith("a3ob_Component")]
    _harness.check(created, "a3obFindComponents must create Component sets on a closed cube")
    for node in created:
        _harness.check(cmds.attributeQuery("a3obTechnicalSet", node=node, exists=True)
              and bool(cmds.getAttr(node + ".a3obTechnicalSet")),
              f"a3obFindComponents left {node} unmarked — nothing hides it now that "
              f"the panel refresh no longer normalizes on read")


def main():
    test_panel_refresh_does_not_dirty_the_scene()
    test_sets_created_through_write_path_are_hidden()
    test_find_components_marks_its_sets_technical()
    print("panels do not dirty the scene: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
