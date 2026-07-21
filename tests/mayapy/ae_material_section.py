"""The DayZ Material AE section registers, and fires only for a3ob shading engines (mayapy).

Maya 2027 SHIPS AEshadingEngineTemplate.mel, so defining our own would shadow it and replace
the stock Shading Group Attributes section. The supported extension point is the
AETemplateCustomContent hook, and it does reach shading engines:

    AEshadingEngineTemplate -> AEentityTemplate -> AEdependNodeTemplate
                                                   `- callbacks -executeCallbacks
                                                        -hook "AETemplateCustomContent" $nodeName

Three things measured on a live mayapy, which is why this file can exist at all:
  * cmds.callbacks(addCallback=..., hook=..., owner=...) works in batch, and listCallbacks
    returns the function, so registration is verifiable. It returns None, not [], when
    nothing is registered.
  * the Python callbacks command has NO flag for the node name (nodeName= raises
    "Invalid flag"), so the callback must be driven the way MEL drives it — positionally,
    through mel.eval.
  * cmds.editorTemplate(...) does not raise in batch, it no-ops, so the body runs end to end.
    The -callCustom procs are therefore NEVER invoked in batch; the controls they build are
    not reachable from here.

What is NOT testable here is whether the section RENDERS. That stays on the author's
live-Maya list.

`entry.show_plugin_ui` / `entry.hide_plugin_ui` both return immediately under
`cmds.about(batch=True)`, so install/uninstall are called DIRECTLY here rather than through
them — reaching them through the entry points would test nothing at all.

Run:  mayapy.exe tests/mayapy/ae_material_section.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402

from a3ob.ui import ae_template  # noqa: E402


def registered():
    """The callbacks registered under our hook and owner. [] when there are none.

    `cmds.callbacks(listCallbacks=True, ...)` answers None rather than an empty list when
    nothing is registered, which would make `len()` blow up instead of reporting zero."""
    return cmds.callbacks(listCallbacks=True, hook=ae_template.HOOK,
                          owner=ae_template.OWNER) or []


def fire(node):
    """Drive the hook exactly the way Maya's AEdependNodeTemplate does."""
    mel.eval('callbacks -executeCallbacks -hook "AETemplateCustomContent" "%s";' % node)


def shading_group(name, texture=None, material=None):
    """A shading engine, optionally carrying the DayZ metadata attributes."""
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    if texture is not None:
        cmds.addAttr(group, longName="a3obTexture", dataType="string")
        cmds.setAttr(group + ".a3obTexture", texture, type="string")
    if material is not None:
        cmds.addAttr(group, longName="a3obMaterial", dataType="string")
        cmds.setAttr(group + ".a3obMaterial", material, type="string")
    return shader, group


class Recorder:
    """Stands in for the section body, which cannot run in batch anyway.

    Patched onto the module that CALLS it: `build_section` resolves `_begin_section`
    through module globals at call time, so replacing the attribute here is seen by the
    already-registered callback object."""

    def __init__(self):
        self.nodes = []

    def __call__(self, node_name):
        self.nodes.append(node_name)


def offered_for(node):
    """Fire the hook for ``node`` and answer whether the section was offered."""
    recorder = Recorder()
    original = ae_template._begin_section
    ae_template._begin_section = recorder
    try:
        fire(node)
    finally:
        ae_template._begin_section = original
    return recorder.nodes


def test_install_registers_under_our_owner():
    """listCallbacks returns the function for hook AETemplateCustomContent, owner
    MayaObjectBuilder."""
    cmds.file(new=True, force=True)
    ae_template.uninstall()
    _harness.check(registered() == [],
                   "the fixture must start with nothing registered, got %r" % (registered(),))

    ae_template.install()
    found = registered()
    _harness.check(len(found) == 1,
                   "install must register exactly one callback, got %r" % (found,))
    _harness.check(found[0] is ae_template.build_section,
                   "the registered callback must be build_section, got %r" % (found[0],))
    ae_template.uninstall()


def test_uninstall_removes_it():
    """A callback that outlives what it points at is the exit-time crash class."""
    cmds.file(new=True, force=True)
    ae_template.install()
    _harness.check(registered(), "the fixture needs a registered callback to remove")

    ae_template.uninstall()
    _harness.check(registered() == [],
                   "uninstall must clear our callback, %r left over" % (registered(),))

    # And firing the hook afterwards must reach nothing of ours.
    shader, group = shading_group("armour", texture=r"data\helmet_co.paa")
    _harness.check(offered_for(group) == [],
                   "no section may be offered after uninstall")

    # Idempotent: uninstalling again is not an error.
    ae_template.uninstall()
    _harness.check(registered() == [], "a second uninstall must stay clean")


def test_installing_twice_registers_one_callback():
    """show_plugin_ui can run more than once in a session; a second install must not stack a
    duplicate that then builds the section twice."""
    cmds.file(new=True, force=True)
    ae_template.uninstall()
    ae_template.install()
    ae_template.install()
    ae_template.install()
    found = registered()
    _harness.check(len(found) == 1,
                   "three installs must leave one callback, got %d" % (len(found),))

    shader, group = shading_group("armour", texture=r"data\helmet_co.paa")
    offered = offered_for(group)
    _harness.check(offered == [group],
                   "the section must be built exactly once, got %r" % (offered,))
    ae_template.uninstall()


def test_the_section_is_offered_for_an_a3ob_shading_engine():
    """Drive it the way MEL does and assert build_section ran for the node."""
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader, textured = shading_group("armour", texture=r"data\helmet_co.paa")
        _harness.check(offered_for(textured) == [textured],
                       "a shading engine with a3obTexture must be offered the section")

        shader2, rvmatted = shading_group("visor", material=r"data\visor.rvmat")
        _harness.check(offered_for(rvmatted) == [rvmatted],
                       "a3obMaterial alone must also be enough")

        _harness.check(ae_template.should_show_section(textured),
                       "the decision seam must agree with the callback")
    finally:
        ae_template.uninstall()


def test_the_section_is_not_offered_for_a_plain_shading_engine():
    """initialShadingGroup carries no a3ob attributes and must be left alone."""
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        _harness.check(not ae_template.should_show_section("initialShadingGroup"),
                       "initialShadingGroup carries no a3ob metadata")
        _harness.check(offered_for("initialShadingGroup") == [],
                       "no section may be offered for initialShadingGroup")

        shader, plain = shading_group("plain")
        _harness.check(offered_for(plain) == [],
                       "a shading engine without a3ob metadata must be left alone")
    finally:
        ae_template.uninstall()


def test_the_section_is_not_offered_for_a_mesh_or_a_material_node():
    """The hook fires for EVERY node type. A section that appeared on a transform would be
    both wrong and, on a big scene, expensive."""
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        mesh = cmds.polyCube(name="helmet", ch=False)[0]
        shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]
        shader, group = shading_group("armour", texture=r"data\helmet_co.paa")
        cmds.sets(mesh, edit=True, forceElement=group)

        for node in (mesh, shape, shader):
            _harness.check(not ae_template.should_show_section(node),
                           "%s is not a shading engine and must not be offered" % (node,))
            _harness.check(offered_for(node) == [],
                           "no section may be offered for %s" % (node,))

        # The material node carries the metadata too (write_material_metadata fans out to
        # it), and that still must not put the section on the shader's own AE tab — the
        # section belongs to the shading engine, once.
        _harness.check(cmds.attributeQuery("a3obTexture", node=shader, exists=True) is False
                       or not ae_template.should_show_section(shader),
                       "a material node carrying a3obTexture is still not a shading engine")

        # A node that does not exist at all must be a quiet False, not a raise.
        _harness.check(not ae_template.should_show_section("no_such_node"),
                       "a deleted node must answer False rather than raising")
        _harness.check(not ae_template.should_show_section(""),
                       "an empty node name must answer False rather than raising")
    finally:
        ae_template.uninstall()


def test_the_decision_does_not_dirty_the_scene():
    """It runs on every Attribute Editor selection change."""
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        mesh = cmds.polyCube(name="helmet", ch=False)[0]
        shader, textured = shading_group("armour", texture=r"data\helmet_co.paa")
        shader2, plain = shading_group("plain")
        cmds.sets(mesh, edit=True, forceElement=textured)

        cmds.file(modified=False)
        _harness.check(not cmds.file(query=True, modified=True),
                       "the fixture must start from a clean scene or this proves nothing")

        for node in (textured, plain, mesh, shader, "initialShadingGroup", "no_such_node"):
            ae_template.should_show_section(node)
        _harness.check(not cmds.file(query=True, modified=True),
                       "should_show_section must not dirty the scene")

        # Firing the real hook must not dirty it either — the AE fires it on every
        # selection change, and Maya asking "Save changes?" after a read-only session is
        # exactly the regression this guards.
        for node in (textured, plain, mesh, shader, "initialShadingGroup"):
            fire(node)
        _harness.check(not cmds.file(query=True, modified=True),
                       "the AE hook must not dirty the scene")

        # And it must not have INVENTED the attributes on the nodes that lacked them.
        for node in (plain, mesh):
            _harness.check(not cmds.attributeQuery("a3obTexture", node=node, exists=True),
                           "%s must not gain a3obTexture from a read" % (node,))
            _harness.check(not cmds.attributeQuery("a3obMaterial", node=node, exists=True),
                           "%s must not gain a3obMaterial from a read" % (node,))
    finally:
        ae_template.uninstall()


def main():
    test_install_registers_under_our_owner()
    test_uninstall_removes_it()
    test_installing_twice_registers_one_callback()
    test_the_section_is_offered_for_an_a3ob_shading_engine()
    test_the_section_is_not_offered_for_a_plain_shading_engine()
    test_the_section_is_not_offered_for_a_mesh_or_a_material_node()
    test_the_decision_does_not_dirty_the_scene()
    print("ae material section: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
