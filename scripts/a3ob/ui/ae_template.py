"""The "DayZ Material" section in Maya's Attribute Editor.

Phase 3d retires the Materials dock panel: per-material editing belongs where a Maya user
already looks for material attributes. Selecting a mesh face-assigned to a DayZ material and
opening the Attribute Editor's shading-group tab now shows Texture, Material and Select Faces
right under Maya's own Shading Group Attributes.

**Why a callback and not a template file.** Maya 2027 ships its own
``AEshadingEngineTemplate.mel``, and this repo's ``scripts/`` is on ``MAYA_SCRIPT_PATH`` — a
file of that name here would SHADOW the stock one and destroy the Shading Group Attributes
section entirely. The supported extension point is the ``AETemplateCustomContent`` hook, and
it does reach shading engines::

    AEshadingEngineTemplate -> AEentityTemplate -> AEdependNodeTemplate
                                                   `- callbacks -executeCallbacks
                                                        -hook "AETemplateCustomContent" $nodeName

The node name arrives POSITIONALLY: the Python ``callbacks`` command has no flag for it
(``nodeName=`` raises "Invalid flag"), so the hook hands the callback one bare argument.

**This module is a leaf.** ``maya.cmds``, ``maya.mel`` and ``a3ob.ui.recent`` only. Every
module in ``a3ob.ui.actions`` star-imports ``a3ob.ui.entry``, so importing one at module level
would close the very cycle ``entry._build_qt_dock``'s lazy import exists to prevent — the
write helpers are therefore imported INSIDE the functions that call them.

**``should_show_section`` is a silent read.** It runs for every node the user selects in the
Attribute Editor. It must not warn, must not write, and must not dirty the scene: a refresh
path that warned once turned clicking any prop into Script Editor spam, and a read path that
normalised on read dirtied the scene so Maya asked "Save changes?" after a read-only session.

**The predicate gates BOTH the build and the replace.** The AE builds a template once per
node TYPE per tab and thereafter only re-points it, so ``build_section`` declares the section
for every ``shadingEngine`` and ``section_replace`` shows or hides it from
``should_show_section``. Gating the build on the full predicate instead made the section
order-dependent — a plain shading engine opened first meant it never appeared again — while
leaving the replace path ungated let a keystroke write a3ob attributes onto an unmarked node.
"""

import maya.cmds as cmds
import maya.mel as mel

OWNER = "MayaObjectBuilder"
HOOK = "AETemplateCustomContent"
SECTION_LABEL = "DayZ Material"

NEW_PROC = "a3obDayZMaterialSectionNew"
REPLACE_PROC = "a3obDayZMaterialSectionReplace"

# One entry per BUILT section, keyed by the columnLayout `section_new` created:
#
#     {layout: {"texture": field, "material": field, "node": node, "shown": bool}}
#
# Keyed, not global. The Attribute Editor reuses one set of controls per template and
# re-points it at whichever node the user selected (that is what the new/replace proc pair is
# for) — but "per template" is not "once per session": a torn-off or duplicated AE tab builds
# the template a SECOND time. A single module-global dict let the second build overwrite the
# first tab's field names and node, so typing in the stale tab wrote the other tab's path to
# the other tab's node. Every control callback captures its own layout key, so an edit always
# resolves the fields and the node belonging to the section it was typed into.
#
# The node still lives beside the control names inside each entry: an edit callback fired
# later must write to the node that section is showing NOW, not the one that happened to be
# selected when its controls were created.
_SECTIONS = {}

_MEL_PROCS = """
global proc %(new)s(string $plug) {
    python("import a3ob.ui.ae_template as _a3ob_ae; _a3ob_ae.section_new('" + $plug + "')");
}
global proc %(replace)s(string $plug) {
    python("import a3ob.ui.ae_template as _a3ob_ae; _a3ob_ae.section_replace('" + $plug + "')");
}
""" % {"new": NEW_PROC, "replace": REPLACE_PROC}


# --------------------------------------------------------------------------- registration


def install():
    """Register the section callback under our own owner. Idempotent.

    Clears first: ``show_plugin_ui`` can run more than once in a session, and a second
    registration would stack a duplicate that then builds the section twice on every tab.
    """
    uninstall()
    mel.eval(_MEL_PROCS)
    cmds.callbacks(addCallback=build_section, hook=HOOK, owner=OWNER)


def uninstall():
    """Clear the section callback. Safe to call when nothing is registered.

    A callback that outlives what it points at is the exit-time crash class
    ``entry._delete_qt_dock`` names — this is the half of that pairing for the AE hook.
    """
    _SECTIONS.clear()
    cmds.callbacks(clearCallbacks=True, hook=HOOK, owner=OWNER)


# ------------------------------------------------------------------------------- decision


def is_shading_engine(node_name):
    """True for an existing ``shadingEngine``, whether or not it carries a3ob metadata.

    Silent, and False rather than raising for anything missing or deleted — same contract as
    :func:`should_show_section`, which builds on it.
    """
    if not node_name:
        return False
    if not cmds.objExists(node_name):
        return False
    try:
        return bool(cmds.objectType(node_name, isType="shadingEngine"))
    except (RuntimeError, ValueError):
        return False


def should_show_section(node_name):
    """True only for a ``shadingEngine`` carrying ``a3obTexture`` or ``a3obMaterial``.

    The Qt-free, AE-free decision seam, and a SILENT read — see the module docstring. Every
    branch answers False rather than raising: the hook fires for every node kind, including
    ones that were deleted between the selection and the refresh.
    """
    if not is_shading_engine(node_name):
        return False
    for attr in ("a3obTexture", "a3obMaterial"):
        try:
            if cmds.attributeQuery(attr, node=node_name, exists=True):
                return True
        except (RuntimeError, ValueError):
            continue
    return False


def build_section(node_name):
    """The ``AETemplateCustomContent`` callback. Declares the section for EVERY shading
    engine, and returns immediately for every other node kind — which is almost every time
    it fires.

    Why the weaker predicate here. The Attribute Editor builds a template ONCE per node type
    per tab and thereafter only re-points it through the replace proc — that is the whole
    reason the new/replace pair exists. Gating the BUILD on ``should_show_section`` therefore
    made the section order-dependent: if the first shading engine opened in a session was a
    plain one, the template was built without the section and every a3ob shading engine
    selected afterwards got only ``section_replace``, so the section never appeared at all.

    So among shading engines the section is always declared, and ``section_replace`` shows or
    hides it from ``should_show_section``. The predicate is authoritative on BOTH paths; the
    build path only decides whether the node is a shading engine in the first place.
    """
    if not is_shading_engine(node_name):
        return
    _begin_section(node_name)


def _begin_section(node_name):
    """Declare the section on the template currently being built.

    ``editorTemplate`` no-ops in batch rather than raising, so this body runs end to end
    under mayapy while building nothing — which is exactly why the mayapy test can drive the
    hook at all, and equally why it can prove nothing about how the section RENDERS.

    ``-callCustom`` with a new/replace proc pair is the idiom every stock template uses. The
    attribute passed is ``message``: every node has it, so the procs receive a plug they can
    split the node name off, without this depending on WHICH of the two a3ob attributes the
    node happens to carry.
    """
    cmds.editorTemplate(beginLayout=SECTION_LABEL, collapse=False)
    cmds.editorTemplate(callCustom=(NEW_PROC, REPLACE_PROC, "message"))
    cmds.editorTemplate(endLayout=True)


# -------------------------------------------------------------------------------- section


def section_new(plug):
    """Build the section's controls once. Called by the MEL ``-callCustom`` new proc.

    Returns the section key — the created layout — which is also what every control callback
    captures, so an edit resolves ITS OWN section's fields and node no matter how many AE
    tabs have built the template.
    """
    node = _node_of(plug)
    cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
    try:
        key = _register_section(cmds.columnLayout(adjustableColumn=True, rowSpacing=2))
        _SECTIONS[key]["texture"] = _path_row(
            key, "Texture",
            "The DayZ .paa this material uses (mod-relative, e.g. data\\helmet_co.paa)",
            "texture", "Texture (*.paa);;All Files (*.*)")
        _SECTIONS[key]["material"] = _path_row(
            key, "Material", "The DayZ .rvmat this material uses (mod-relative)",
            "rvmat", "Material (*.rvmat);;All Files (*.*)")
        cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 220),
                       columnAttach=[(1, "right", 5), (2, "both", 0)])
        cmds.text(label="")
        _SECTIONS[key]["faces"] = cmds.button(
            label="Select Faces", command=lambda *_, _k=key: _select_faces(_k),
            annotation="Select the faces this material is assigned to, on the selected "
                       "mesh(es). Hypershade can select objects by material but not faces.")
        cmds.setParent("..")
        cmds.setParent("..")
    finally:
        cmds.setUITemplate(popTemplate=True)
    _repoint(key, node)
    return key


def section_replace(plug):
    """Re-point the existing controls at whichever node the AE is now showing, and show or
    hide the whole section from ``should_show_section``.

    This is where the predicate is enforced for every selection after the first. Without it
    the section stayed visible on a plain shading engine with blank fields, and one keystroke
    wrote ``a3obTexture``/``a3obMaterial`` onto a node the plugin never marked — fanning out,
    through ``write_material_metadata``, to its material and every other shading engine
    sharing it.
    """
    key = _resolve_section()
    if key is None:
        return None
    _repoint(key, _node_of(plug))
    return key


def _node_of(plug):
    return (plug or "").split(".")[0]


def _register_section(layout):
    """Record a freshly built section under its own layout and return that key.

    Dead sections are pruned first: a closed AE tab takes its layout with it, and an entry
    that outlives its controls would otherwise be a candidate ``_resolve_section`` could
    hand a later edit to.
    """
    _forget_dead_sections()
    _SECTIONS[layout] = {"texture": None, "material": None, "faces": None,
                         "node": None, "shown": False}
    return layout


def _forget_dead_sections():
    for key in [k for k in _SECTIONS if not _layout_exists(k)]:
        del _SECTIONS[key]


def _layout_exists(key):
    """Whether a section's layout is still alive.

    In batch no UI is built at all — every Maya layout command answers False — so there is
    nothing to prune and pruning by that answer would drop every section the moment it was
    registered. Batch says "alive", which is also what lets the mayapy tests drive the state
    layer that both AE-tab bugs actually live in.
    """
    if not key:
        return True
    try:
        if cmds.about(batch=True):
            return True
        return bool(cmds.layout(key, exists=True))
    except (RuntimeError, ValueError):
        return False


def _resolve_section():
    """The section the AE is currently re-pointing, or None.

    Maya calls the replace proc with the UI parent set to where the section was built, so the
    registered layout is that parent or a child of it. Anything left over — a single live
    section, else the most recently built one — is the fallback for the ordinary case of one
    AE tab, which is also the only case reachable in batch.

    Only ``section_replace`` needs to guess, and the guess is NOT harmless. Every CONTROL
    callback captured its own key when it was created, so which FIELDS an edit reads is
    never in doubt — but the node is not captured, it is state this function's caller
    writes: ``_repoint`` stores ``section["node"]``. Resolve to tab A while the AE is
    re-pointing tab B and tab A's stored node becomes B's, so a later keystroke in A writes
    to B's node. Display and write stay consistent with each other (the fields were
    repointed too), and ``_repoint`` only ever stores a node that passed
    ``should_show_section``, so an UNMARKED node still cannot be written to — that is the
    dangerous class and it stays closed. What is left is a wrong-marked-node write, bounded
    to two or more AE tabs, and it is unproven either way: this is the one heuristic here,
    and only a live session can exercise it.
    """
    _forget_dead_sections()
    if not _SECTIONS:
        return None
    try:
        parent = cmds.setParent(query=True) or ""
    except (RuntimeError, ValueError):
        parent = ""
    if parent:
        for key in _SECTIONS:
            if key and (key == parent or key.startswith(parent + "|")):
                return key
    return list(_SECTIONS)[-1]


def _path_row(key, label, annotation, recent_key, file_filter):
    """A label, an editable path field, and browse / recent / clear buttons.

    Plain Maya UI (``rowLayout``/``textField``), not Qt: these controls live inside Maya's own
    Attribute Editor layout and have to be parented into it.

    Every callback binds ``key`` as a default argument, so it keeps addressing the section it
    was built for even after another AE tab builds a second one.
    """
    cmds.rowLayout(numberOfColumns=5, adjustableColumn=2,
                   columnWidth5=(145, 200, 26, 26, 26),
                   columnAttach=[(1, "right", 5), (2, "both", 0), (3, "both", 2),
                                 (4, "both", 2), (5, "both", 2)])
    cmds.text(label=label)
    field = cmds.textField(annotation=annotation,
                           changeCommand=lambda *_, _k=key: _write_from_controls(_k))
    cmds.symbolButton(image="fileOpen.png", annotation="Browse for a file",
                      command=lambda *_, _k=key: _browse(_k, field, file_filter))
    recent = cmds.symbolButton(image="menuIconEdit.png",
                               annotation="Recently used paths")
    cmds.popupMenu(parent=recent, button=1,
                   postMenuCommand=lambda menu, *_, _k=key:
                   _fill_recent_menu(_k, menu, field, recent_key))
    cmds.symbolButton(image="deleteActive.png", annotation="Clear this path",
                      command=lambda *_, _k=key: _set_field(_k, field, "", write=True))
    cmds.setParent("..")
    return field


def _repoint(key, node):
    """Show ``node``'s stored paths, and show or hide the section. A read — it must not write
    anything back.

    When the node is not ours the section is hidden AND its node is forgotten, so a callback
    that somehow fires against a hidden section has nothing to write to. Hiding alone would
    leave the write path armed.
    """
    section = _SECTIONS.get(key)
    if section is None:
        return False
    shown = should_show_section(node)
    section["node"] = node if shown else None
    section["shown"] = shown
    _manage_layout(key, shown)
    for which, attr in (("texture", "a3obTexture"), ("material", "a3obMaterial")):
        _set_field(key, section.get(which), _read_attr(node, attr) if shown else "")
    return shown


def _manage_layout(key, shown):
    """Show or hide the section's layout. No-ops in batch, where nothing was built."""
    if not key:
        return
    try:
        if cmds.layout(key, exists=True):
            cmds.layout(key, edit=True, manage=bool(shown))
    except (RuntimeError, ValueError):
        pass


def _read_attr(node, attr):
    if not node or not cmds.objExists(node):
        return ""
    try:
        if not cmds.attributeQuery(attr, node=node, exists=True):
            return ""
        return cmds.getAttr(node + "." + attr) or ""
    except (RuntimeError, ValueError):
        return ""


def _set_field(key, field, value, write=False):
    if not field or not cmds.textField(field, exists=True):
        return
    cmds.textField(field, edit=True, text=value or "")
    if write:
        _write_from_controls(key)


def _fill_recent_menu(key, menu, field, recent_key):
    from a3ob.ui.recent import recent_paths

    cmds.popupMenu(menu, edit=True, deleteAllItems=True)
    paths = recent_paths(recent_key)
    if not paths:
        cmds.menuItem(parent=menu, label="No recent paths", enable=False)
        return
    for path in paths:
        cmds.menuItem(parent=menu, label=path,
                      command=lambda _flag=False, _path=path, _k=key:
                      _set_field(_k, field, _path, write=True))


def _browse(key, field, file_filter):
    selected = cmds.fileDialog2(fileMode=1, fileFilter=file_filter,
                                caption="Select a DayZ path")
    if not selected:
        return
    _set_field(key, field, selected[0], write=True)


def _write_from_controls(key):
    """Persist ``key``'s two paths onto the shading network it is showing. Edits are instant —
    there is no Apply button and none is added.

    ``key`` addresses ONE section, so a keystroke in a stale AE tab writes that tab's field
    text to that tab's node. Reading the fields out of a module global instead let a second
    template build silently redirect the write.

    A section that ``_repoint`` hid has no node, so this is a no-op for it — the predicate
    gates the write as well as the display.

    Imported inside the function: ``a3ob.ui.actions.materials`` star-imports
    ``a3ob.ui.entry``, and this module must stay a leaf.
    """
    section = _SECTIONS.get(key)
    if section is None:
        return set()
    node = section.get("node")
    if not node or not cmds.objExists(node):
        return set()
    texture = _field_text(key, "texture")
    material = _field_text(key, "material")

    from a3ob.ui.actions.materials import write_material_metadata

    written = write_material_metadata(node, texture, material)
    if not written:
        cmds.warning("Material metadata target was deleted")
        return written
    # Show what was actually stored: write_material_metadata normalises the paths, and a
    # field still showing "P:/data/x.paa" beside an attribute holding "data\x.paa" is a lie
    # the user has no way to see through.
    _repoint(key, node)
    _reresolve_textures()
    return written


def _reresolve_textures():
    """Re-resolve texture files after a path edit. Never blocks the edit.

    A missing or undecodable ``.paa`` must not stop the attribute write that already
    succeeded — but swallowing everything silently also hid programming errors in
    ``assign_pending_textures``, which is why the failure is reported rather than dropped.
    """
    from a3ob.mayabridge import paatex

    try:
        return paatex.assign_pending_textures()
    except Exception as error:  # noqa: BLE001 - an undecodable .paa must not block the edit
        cmds.warning("Could not re-resolve textures: %s: %s"
                     % (type(error).__name__, error))
        return 0


def _field_text(key, which):
    section = _SECTIONS.get(key)
    field = section.get(which) if section else None
    if not field or not cmds.textField(field, exists=True):
        return ""
    return cmds.textField(field, query=True, text=True) or ""


def _select_faces(key):
    from a3ob.ui.actions.materials import select_faces_for_shading_group

    section = _SECTIONS.get(key)
    node = section.get("node") if section else None
    if not node or not cmds.objExists(node):
        return 0
    count = select_faces_for_shading_group(node)
    if count:
        cmds.inViewMessage(assistMessage="Selected %d face(s)" % count,
                           position="midCenter", fade=True)
    return count


__all__ = [
    "OWNER",
    "HOOK",
    "SECTION_LABEL",
    "install",
    "uninstall",
    "is_shading_engine",
    "should_show_section",
    "build_section",
    "section_new",
    "section_replace",
]
