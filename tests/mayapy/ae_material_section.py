"""The DayZ Material AE section registers, discriminates, and writes edits (mayapy).

The section used to be declared with `editorTemplate -callCustom`. Measured in a live Maya 2027
session: **callCustom never fires from inside the AETemplateCustomContent hook.** beginLayout and
endLayout DO take effect, so the section rendered as an empty frame on every shading engine,
marked or not, and no headless test could see it — cmds.editorTemplate no-ops in batch.

`-addControl` does work, takes a `-label` override, and its change command fires with the NODE
name. Maya then re-points the controls itself when the AE switches nodes, which is why every trace
of per-tab section bookkeeping is gone.

What this file CANNOT prove is that anything renders. That stays on the author's live-Maya list.

Run:  mayapy.exe tests/mayapy/ae_material_section.py
"""

import _harness

_harness.bootstrap()

import maya.cmds as cmds  # noqa: E402
import maya.mel as mel  # noqa: E402
import maya.OpenMaya as om1  # noqa: E402 - API 1.0 has the command-output callback

from a3ob.mayabridge.attributes import A  # noqa: E402
from a3ob.ui import ae_template  # noqa: E402

TEXTURE_ATTR = A.SG_TEXTURE[0]
MATERIAL_ATTR = A.SG_MATERIAL[0]


def registered():
    """The callbacks registered under our hook and owner. [] when there are none.

    `cmds.callbacks(listCallbacks=True, ...)` answers None rather than an empty list when
    nothing is registered, which would make `len()` blow up instead of reporting zero."""
    return cmds.callbacks(listCallbacks=True, hook=ae_template.HOOK,
                          owner=ae_template.OWNER) or []


def fire(node):
    """Drive the hook exactly the way Maya's AEdependNodeTemplate does.

    Positionally, through MEL: the Python `callbacks` command has no flag for the node name
    (`nodeName=` raises "Invalid flag")."""
    mel.eval('callbacks -executeCallbacks -hook "AETemplateCustomContent" "%s";' % node)


def shading_group(name, texture=None, material=None):
    """A shading engine, optionally carrying the DayZ metadata attributes."""
    shader = cmds.shadingNode("lambert", asShader=True, name=name)
    group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(shader + ".outColor", group + ".surfaceShader", force=True)
    if texture is not None:
        cmds.addAttr(group, longName=TEXTURE_ATTR, dataType="string")
        cmds.setAttr(group + "." + TEXTURE_ATTR, texture, type="string")
    if material is not None:
        cmds.addAttr(group, longName=MATERIAL_ATTR, dataType="string")
        cmds.setAttr(group + "." + MATERIAL_ATTR, material, type="string")
    return shader, group


def read(node, attr):
    if not cmds.attributeQuery(attr, node=node, exists=True):
        return None
    return cmds.getAttr(node + "." + attr)


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
    """Fire the hook for ``node`` and answer which nodes the section was declared for."""
    recorder = Recorder()
    original = ae_template._begin_section
    ae_template._begin_section = recorder
    try:
        fire(node)
    finally:
        ae_template._begin_section = original
    return recorder.nodes


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
    duplicate that then declares the section twice on every tab."""
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
                   "the section must be declared exactly once, got %r" % (offered,))
    ae_template.uninstall()


def test_the_section_is_offered_for_an_a3ob_shading_engine():
    """Drive it the way MEL does and assert the declaration ran for the node."""
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
    """The predicate asymmetry the callCustom design needed is GONE.

    `-callCustom` had to declare the section for every shading engine and then show or hide it
    from the replace proc, because the AE caches a template per node TYPE and only re-points it
    afterwards. Native `-addControl` controls are re-pointed by Maya itself, so there is no
    cached-template problem to work around and the section can simply not be declared at all —
    which is also what removes the empty-frame-on-plain-materials defect the live check found.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        _harness.check(not ae_template.should_show_section("initialShadingGroup"),
                       "initialShadingGroup carries no a3ob metadata")
        _harness.check(offered_for("initialShadingGroup") == [],
                       "a plain shading engine must get no section at all")

        shader, plain = shading_group("plain")
        _harness.check(not ae_template.should_show_section(plain),
                       "a bare shading engine carries no a3ob metadata either")
        _harness.check(offered_for(plain) == [],
                       "and must get no section, not an empty frame")
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
        cmds.addAttr(shader, longName=TEXTURE_ATTR, dataType="string")
        cmds.setAttr(shader + "." + TEXTURE_ATTR, r"data\helmet_co.paa", type="string")
        _harness.check(cmds.attributeQuery(TEXTURE_ATTR, node=shader, exists=True),
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


def test_begin_section_declares_addcontrol_not_callcustom():
    """Pins the ONE thing `offered_for()` cannot see: what `_begin_section`'s body itself
    calls. Every other test in this file patches `_begin_section` out with `Recorder` before
    firing the hook, so its real body never runs anywhere else here — and reverting it to the
    old `cmds.editorTemplate(callCustom=(NEW_PROC, REPLACE_PROC, "message"))` form leaves
    every other test green. This is the false-pass shape the addControl rewrite exists to
    correct, and this test is the one that would have caught it.

    Monkeypatches `cmds.editorTemplate` itself (not `_begin_section`) to record the call
    sequence, then asserts it is beginLayout -> two addControl calls carrying SG_TEXTURE and
    SG_MATERIAL, the CHANGE_PROC name, and the label overrides -> endLayout, with `callCustom`
    appearing nowhere. It does NOT prove the section renders — `cmds.editorTemplate` no-ops
    in batch either way — only that the call shape is the addControl one and not the
    callCustom one.
    """
    calls = []

    def recorder(*args, **kwargs):
        calls.append((args, kwargs))

    original = cmds.editorTemplate
    cmds.editorTemplate = recorder
    try:
        ae_template._begin_section("someSG")
    finally:
        cmds.editorTemplate = original

    _harness.check(len(calls) == 4,
                   "expected beginLayout, two addControl, endLayout - got %r" % (calls,))

    _, begin_kwargs = calls[0]
    _harness.check(begin_kwargs.get("beginLayout") == ae_template.SECTION_LABEL,
                   "the first call must open the section, got %r" % (calls[0],))
    _harness.check(begin_kwargs.get("collapse") is False,
                   "the section must open expanded, got %r" % (calls[0],))

    texture_args, texture_kwargs = calls[1]
    _harness.check(texture_args == (TEXTURE_ATTR, ae_template.CHANGE_PROC),
                   "the texture control must be addControl'd against a3obTexture with the "
                   "change proc, got %r" % (calls[1],))
    _harness.check(texture_kwargs == {"addControl": True, "label": "Texture"},
                   "got %r" % (calls[1],))

    material_args, material_kwargs = calls[2]
    _harness.check(material_args == (MATERIAL_ATTR, ae_template.CHANGE_PROC),
                   "the material control must be addControl'd against a3obMaterial with the "
                   "change proc, got %r" % (calls[2],))
    _harness.check(material_kwargs == {"addControl": True, "label": "Material"},
                   "got %r" % (calls[2],))

    _, end_kwargs = calls[3]
    _harness.check(end_kwargs.get("endLayout") is True,
                   "the last call must close the section, got %r" % (calls[3],))

    for _, kwargs in calls:
        _harness.check("callCustom" not in kwargs,
                       "callCustom must never appear here - its procs never fire from "
                       "inside the AETemplateCustomContent hook, got %r" % (kwargs,))


def test_the_mel_shim_routes_to_on_attribute_edited():
    """Pins the MEL string interpolation in `_MEL_PROCS`, which is otherwise only proven not
    to be a syntax error (by `install()` succeeding elsewhere in this file).

    After `install()`, calls the registered MEL proc directly by name - the same way Maya's
    native `-addControl` change command calls it - and asserts the Python side actually ran
    with the node name the MEL call was given. This does NOT prove Maya itself invokes the
    proc on a real field edit; that stays on the live-Maya list.
    """
    cmds.file(new=True, force=True)
    ae_template.uninstall()
    ae_template.install()
    try:
        seen = []

        def recorder(node_name):
            seen.append(node_name)
            return set()

        original = ae_template.on_attribute_edited
        ae_template.on_attribute_edited = recorder
        try:
            mel.eval('%s("someSG")' % ae_template.CHANGE_PROC)
        finally:
            ae_template.on_attribute_edited = original

        _harness.check(seen == ["someSG"],
                       "the MEL shim must call on_attribute_edited with the node name it "
                       "was passed, got %r" % (seen,))
    finally:
        ae_template.uninstall()


def test_the_decision_is_silent_and_does_not_dirty_the_scene():
    """It runs for every node the user selects in the Attribute Editor.

    CLAUDE.md's rule for anything the UI calls on a refresh path is "a SILENT query that must
    not WRITE". A warning here would turn clicking any prop into Script Editor spam, and a read
    that dirtied the scene would make Maya ask "Save changes?" after a read-only session — this
    codebase has shipped both.

    The silence half needs a POSITIVE CONTROL in this same file, or it passes vacuously the
    moment the output listener stops working. `dock_panel_sync.test_list_influences_is_silent`
    is the pattern.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        mesh = cmds.polyCube(name="helmet", ch=False)[0]
        shader, armour = shading_group("armour", texture=r"data\helmet_co.paa")
        shader2, plain = shading_group("plain")
        cmds.sets(mesh, edit=True, forceElement=armour)

        # --- positive control, first, on a real ae_template path -----------------------
        # `on_attribute_edited` delegates the node-kind guard to `write_material_metadata`,
        # which warns when the node is neither a shading engine nor a material. A transform
        # carrying the attributes reaches exactly that warning. If the listener cannot hear
        # this, every silence check below is worthless.
        stray = cmds.polyCube(name="stray", ch=False)[0]
        cmds.addAttr(stray, longName=TEXTURE_ATTR, dataType="string")
        cmds.setAttr(stray + "." + TEXTURE_ATTR, r"data\stray_co.paa", type="string")
        _, control = listen(lambda: ae_template.on_attribute_edited(stray),
                            "neither a shading engine nor a material")
        _harness.check(control,
                       "the output callback hears nothing at all — every silence check "
                       "below would pass vacuously")

        # --- silence ------------------------------------------------------------------
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

        # --- no scene dirt ------------------------------------------------------------
        cmds.file(modified=False)
        _harness.check(not cmds.file(query=True, modified=True),
                       "the fixture must start from a clean scene or this proves nothing")

        for node in (armour, plain, mesh, shader, "initialShadingGroup", "no_such_node"):
            ae_template.should_show_section(node)
        _harness.check(not cmds.file(query=True, modified=True),
                       "should_show_section must not dirty the scene")

        for node in (armour, plain, mesh, shader, "initialShadingGroup"):
            fire(node)
        _harness.check(not cmds.file(query=True, modified=True),
                       "the AE hook must not dirty the scene")

        # And it must not have INVENTED the attributes on the nodes that lacked them.
        for node in (plain, mesh):
            for attr in (TEXTURE_ATTR, MATERIAL_ATTR):
                _harness.check(not cmds.attributeQuery(attr, node=node, exists=True),
                               "%s must not gain %s from a read" % (node, attr))
    finally:
        ae_template.uninstall()


def test_an_edit_persists_both_paths_normalised():
    """`on_attribute_edited(node)` is the change command's whole job — call it directly.

    Maya's native control has already written the user's raw text to the attribute by the time
    the change command fires. The handler's job is to read both attributes back, normalise them
    and fan them out through `write_material_metadata` — so the node ends up holding the
    normalised path, not the raw one the user typed.
    """
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader, armour = shading_group("armour", texture=r"data\helmet_co.paa",
                                       material=r"data\helmet.rvmat")
        # What a native textField edit leaves behind: an absolute, forward-slashed path.
        cmds.setAttr(armour + "." + TEXTURE_ATTR, "P:/data/armour_co.paa", type="string")

        written = ae_template.on_attribute_edited(armour)
        _harness.check(armour in written,
                       "the edit must persist to the shading engine, wrote %r" % (written,))
        _harness.check(shader in written,
                       "and fan out to the material feeding it, wrote %r" % (written,))

        stored = read(armour, TEXTURE_ATTR)
        _harness.check(stored == r"data\armour_co.paa",
                       "the stored texture must be the NORMALISED path, got %r" % (stored,))
        _harness.check(read(shader, TEXTURE_ATTR) == r"data\armour_co.paa",
                       "and the material must hold the same normalised path, got %r"
                       % (read(shader, TEXTURE_ATTR),))
        _harness.check(read(armour, MATERIAL_ATTR) == r"data\helmet.rvmat",
                       "the untouched material path must survive the edit, got %r"
                       % (read(armour, MATERIAL_ATTR),))

        # The handler is given the NODE name, not an attribute name — that is what the live
        # session measured the change command receiving.
        _harness.check(ae_template.on_attribute_edited(armour + "." + TEXTURE_ATTR) == set(),
                       "an attribute name is not a node and must write nothing")
    finally:
        ae_template.uninstall()


def test_an_edit_on_a_node_that_lost_its_attributes_writes_nothing_and_does_not_raise():
    """A change command can fire against a node whose attributes were deleted out from under
    it — and re-adding them from a stale edit would silently mark a node the plugin never
    marked, fanning out to its material and every shading engine sharing it."""
    cmds.file(new=True, force=True)
    ae_template.install()
    try:
        shader, plain = shading_group("plain")
        written = ae_template.on_attribute_edited(plain)
        _harness.check(written == set(),
                       "a shading engine with neither attribute must be written nothing, "
                       "wrote %r" % (written,))
        for node in (plain, shader):
            for attr in (TEXTURE_ATTR, MATERIAL_ATTR):
                _harness.check(not cmds.attributeQuery(attr, node=node, exists=True),
                               "%s must not have gained %s" % (node, attr))

        # A node deleted between the keystroke and the callback.
        shader2, doomed = shading_group("doomed", texture=r"data\doomed_co.paa")
        cmds.delete(doomed)
        _harness.check(ae_template.on_attribute_edited(doomed) == set(),
                       "a deleted node must write nothing rather than raising")
        _harness.check(ae_template.on_attribute_edited("") == set(),
                       "an empty node name must write nothing rather than raising")
        _harness.check(ae_template.on_attribute_edited("no_such_node") == set(),
                       "a node that never existed must write nothing rather than raising")
    finally:
        ae_template.uninstall()


def main():
    test_install_registers_under_our_owner()
    test_uninstall_removes_it()
    test_installing_twice_registers_one_callback()
    test_the_section_is_offered_for_an_a3ob_shading_engine()
    test_the_section_is_not_offered_for_a_plain_shading_engine()
    test_the_section_is_not_offered_for_a_mesh_or_a_material_node()
    test_begin_section_declares_addcontrol_not_callcustom()
    test_the_mel_shim_routes_to_on_attribute_edited()
    test_the_decision_is_silent_and_does_not_dirty_the_scene()
    test_an_edit_persists_both_paths_normalised()
    test_an_edit_on_a_node_that_lost_its_attributes_writes_nothing_and_does_not_raise()
    print("ae material section: OK")


if __name__ == "__main__":
    import sys
    sys.exit(_harness.run(main))
