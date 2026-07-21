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

What IS reachable is the per-section STATE layer — `_register_section`, `_repoint`,
`_write_from_controls` — and that is where both AE-tab defects live, so they are tested here
directly. `section_new` itself cannot run in batch (`setUITemplate "attributeEditorTemplate"`
raises: the template only exists once the AE has been opened), and every Maya layout command
answers False there, so these tests register sections by name and drive the state layer the
way `section_new` does. `_layout_exists` treats batch as "alive" for exactly that reason.

What is NOT testable here is whether the section RENDERS, or whether hiding a layout with
`-manage false` looks right. That stays on the author's live-Maya list.

`entry.show_plugin_ui` / `entry.hide_plugin_ui` both return immediately under
`cmds.about(batch=True)`, so install/uninstall are called DIRECTLY here rather than through
them — reaching them through the entry points would test nothing at all.

Run:  mayapy.exe tests/mayapy/ae_material_section.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.OpenMaya as om1  # noqa: E402 - API 1.0 has the command-output callback

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


def section(layout):
    """Register a built section under ``layout``, the way `section_new` does.

    `section_new` cannot run in batch — its first call is
    `setUITemplate "attributeEditorTemplate"`, and that template only exists once the
    Attribute Editor has been opened. Its controls would all be False here anyway. What this
    reaches is the state layer underneath, which is where the tab bugs are.
    """
    ae_template._SECTIONS.clear()
    return ae_template._register_section(layout)


def listen(call, needle=None):
    """Run ``call`` and return its result plus what Maya said — all of it, or only the lines
    containing ``needle``.

    The same MCommandMessage listener `dock_panel_sync.test_list_influences_is_silent` uses:
    om.MGlobal cannot be monkey-patched, so the only way to assert silence is to hear it.
    """
    said = []
    callback = om1.MCommandMessage.addCommandOutputCallback(
        lambda message, message_type, data: said.append(message))
    try:
        result = call()
    finally:
        om1.MMessage.removeCallback(callback)
    return result, [line for line in said if needle is None or needle in line]


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


def test_the_section_is_declared_for_a_plain_shading_engine_but_hidden():
    """The AE caches a template per node TYPE, so the section must be DECLARED for every
    shading engine and then shown or hidden by the replace proc.

    Gating the build on the full predicate made the section order-dependent: open a plain
    shading engine first and the template was cached without it, so every a3ob shading engine
    afterwards got only `section_replace` and the section never appeared at all.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        _harness.check(not ae_template.should_show_section("initialShadingGroup"),
                       "initialShadingGroup carries no a3ob metadata")
        _harness.check(offered_for("initialShadingGroup") == ["initialShadingGroup"],
                       "the section must still be DECLARED for a plain shading engine")

        shader, plain = shading_group("plain")
        _harness.check(offered_for(plain) == [plain],
                       "a plain shading engine declares the section too — it is hidden on "
                       "the replace path, not skipped on the build path")
        _harness.check(not ae_template.should_show_section(plain),
                       "but the predicate still says it must not be shown")
    finally:
        ae_template.uninstall()


def test_a_plain_shading_engine_opened_first_does_not_suppress_the_section():
    """The order-dependence itself, driven the way the AE drives it.

    The AE builds the template once per node type per tab. Whichever shading engine is opened
    FIRST is the one that decides what got built — so building for a plain one and then
    re-pointing at an a3ob one must still end with the section shown.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader, plain = shading_group("plain")
        shader2, armour = shading_group("armour", texture=r"data\helmet_co.paa")

        # The plain one is opened first: the template is built from it.
        _harness.check(offered_for(plain) == [plain],
                       "the plain shading engine must still build the section")

        # It is that ONE built section the AE now re-points. Selecting the a3ob shading
        # engine fires only the replace proc, never the build.
        key = section("plainFirstLayout")
        ae_template._repoint(key, plain)
        _harness.check(not ae_template._SECTIONS[key]["shown"],
                       "the section starts hidden on the plain shading engine")

        shown = ae_template.section_replace(armour + ".message")
        _harness.check(ae_template._SECTIONS[shown]["shown"],
                       "re-pointing at an a3ob shading engine must SHOW the section — "
                       "this is the case that used to leave it invisible forever")
        _harness.check(ae_template._SECTIONS[shown]["node"] == armour,
                       "and point it at that node, got %r"
                       % (ae_template._SECTIONS[shown]["node"],))
    finally:
        ae_template.uninstall()


def test_replace_onto_a_plain_shading_engine_disarms_the_write():
    """The silent wrong write.

    With the section built for an a3ob shading engine, selecting a plain one fired only
    `section_replace`, which re-pointed with no predicate. The section stayed visible with
    blank fields, and one keystroke ran `write_material_metadata` against a node the plugin
    never marked — fanning out to its material and every shading engine sharing it.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader, armour = shading_group("armour", texture=r"data\helmet_co.paa")
        key = section("armourLayout")
        _harness.check(ae_template._repoint(key, armour),
                       "the fixture must start with the section shown, or this proves nothing")

        shown = ae_template._repoint(key, "initialShadingGroup")
        _harness.check(not shown, "re-pointing at a plain shading engine must hide the section")
        _harness.check(ae_template._SECTIONS[key]["node"] is None,
                       "and must forget the node, or the write path stays armed on a hidden "
                       "section; got %r" % (ae_template._SECTIONS[key]["node"],))

        written = ae_template._write_from_controls(key)
        _harness.check(written == set(),
                       "a keystroke on a hidden section must write nothing, wrote %r"
                       % (written,))
        for node in ("initialShadingGroup", "initialParticleSE"):
            for attr in ("a3obTexture", "a3obMaterial"):
                _harness.check(not cmds.attributeQuery(attr, node=node, exists=True),
                               "%s must not have gained %s" % (node, attr))
    finally:
        ae_template.uninstall()


def test_each_ae_tab_writes_to_its_own_node():
    """A torn-off or duplicated AE tab builds the template a SECOND time.

    The per-section state used to be one module-global dict, so the second build overwrote
    the first tab's field names AND its node. Typing in the stale tab then read the new tab's
    field and wrote it to the new tab's node — silently, and to the wrong model.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader_a, first = shading_group("first", texture=r"data\first_co.paa")
        shader_b, second = shading_group("second", texture=r"data\second_co.paa")

        ae_template._SECTIONS.clear()
        tab_a = ae_template._register_section("tabALayout")
        tab_b = ae_template._register_section("tabBLayout")
        _harness.check(tab_a != tab_b, "two builds must be two distinct sections")
        ae_template._repoint(tab_a, first)
        ae_template._repoint(tab_b, second)

        # The second build must not have moved the first tab's node out from under it.
        _harness.check(ae_template._SECTIONS[tab_a]["node"] == first,
                       "tab A must still be showing %s, got %r"
                       % (first, ae_template._SECTIONS[tab_a]["node"]))

        written_a = ae_template._write_from_controls(tab_a)
        _harness.check(first in written_a,
                       "a keystroke in tab A must write to %s, wrote %r" % (first, written_a))
        _harness.check(second not in written_a,
                       "and must NOT touch tab B's node %s, wrote %r" % (second, written_a))

        written_b = ae_template._write_from_controls(tab_b)
        _harness.check(second in written_b and first not in written_b,
                       "and tab B must write only to %s, wrote %r" % (second, written_b))
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

        # write_material_metadata fans the metadata out to the material node as well, and
        # that still must not put the section on the shader's own AE tab — the section
        # belongs to the shading engine, once. Put the attribute on the shader for real:
        # `shading_group()` adds it to the SET only, so asserting this against a bare shader
        # tested nothing at all.
        cmds.addAttr(shader, longName="a3obTexture", dataType="string")
        cmds.setAttr(shader + ".a3obTexture", r"data\helmet_co.paa", type="string")
        _harness.check(cmds.attributeQuery("a3obTexture", node=shader, exists=True),
                       "the fixture must actually put a3obTexture on the shader, or the "
                       "check below passes vacuously")
        _harness.check(not ae_template.should_show_section(shader),
                       "a material node carrying a3obTexture is still not a shading engine")
        _harness.check(offered_for(shader) == [],
                       "and the hook must not declare the section on its tab either")

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


def test_the_decision_is_silent():
    """It runs for every node the user selects in the Attribute Editor.

    CLAUDE.md's rule for anything a panel calls is "a SILENT query that must not WRITE" —
    `test_the_decision_does_not_dirty_the_scene` covers the write half, this covers the
    silence. A warning on this path would turn clicking any prop into Script Editor spam,
    which this codebase has shipped before.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        mesh = cmds.polyCube(name="helmet", ch=False)[0]
        shader, armour = shading_group("armour", texture=r"data\helmet_co.paa")
        shader2, plain = shading_group("plain")

        # Positive control FIRST, in this file, on this module. Asserting silence is
        # worthless unless the listener can be heard to work: a callback that stopped firing
        # would pass every check below no matter what the predicate said.
        # `_select_faces` warns when the material is on no selected face — a real path in
        # `ae_template`, not a synthetic `cmds.warning`.
        key = section("silenceLayout")
        ae_template._repoint(key, armour)
        cmds.select(mesh, replace=True)
        _, control = listen(lambda: ae_template._select_faces(key), "not assigned")
        _harness.check(control,
                       "the output callback hears nothing at all — every silence check "
                       "below would pass vacuously")

        for node in (armour, plain, mesh, shader, "initialShadingGroup", "no_such_node", ""):
            _, noise = listen(lambda _n=node: ae_template.should_show_section(_n))
            _harness.check(not noise,
                           "should_show_section(%r) must stay silent, said: %r"
                           % (node, noise))
            _, noise = listen(lambda _n=node: ae_template.is_shading_engine(_n))
            _harness.check(not noise,
                           "is_shading_engine(%r) must stay silent, said: %r" % (node, noise))

        # The hook itself is what actually fires on every AE selection change.
        for node in (armour, plain, mesh, shader, "initialShadingGroup"):
            _, noise = listen(lambda _n=node: fire(_n))
            _harness.check(not noise,
                           "the AE hook must stay silent for %r, said: %r" % (node, noise))
    finally:
        ae_template.uninstall()


def main():
    test_install_registers_under_our_owner()
    test_uninstall_removes_it()
    test_installing_twice_registers_one_callback()
    test_the_section_is_offered_for_an_a3ob_shading_engine()
    test_the_section_is_declared_for_a_plain_shading_engine_but_hidden()
    test_a_plain_shading_engine_opened_first_does_not_suppress_the_section()
    test_replace_onto_a_plain_shading_engine_disarms_the_write()
    test_each_ae_tab_writes_to_its_own_node()
    test_the_section_is_not_offered_for_a_mesh_or_a_material_node()
    test_the_decision_does_not_dirty_the_scene()
    test_the_decision_is_silent()
    print("ae material section: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
