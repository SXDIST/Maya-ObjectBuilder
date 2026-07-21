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
"""

import maya.cmds as cmds
import maya.mel as mel

OWNER = "MayaObjectBuilder"
HOOK = "AETemplateCustomContent"
SECTION_LABEL = "DayZ Material"

NEW_PROC = "a3obDayZMaterialSectionNew"
REPLACE_PROC = "a3obDayZMaterialSectionReplace"

# The controls the -callCustom procs build, and the node they are currently showing. The
# Attribute Editor reuses ONE set of controls per template and re-points it at whichever node
# the user selected (that is what the new/replace proc pair is for), so the node has to live
# beside the control names: an edit callback fired later must write to the node on screen now,
# not the one that happened to be selected when the controls were created.
_CONTROLS = {}

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
    _CONTROLS.clear()
    cmds.callbacks(clearCallbacks=True, hook=HOOK, owner=OWNER)


# ------------------------------------------------------------------------------- decision


def should_show_section(node_name):
    """True only for a ``shadingEngine`` carrying ``a3obTexture`` or ``a3obMaterial``.

    The Qt-free, AE-free decision seam, and a SILENT read — see the module docstring. Every
    branch answers False rather than raising: the hook fires for every node kind, including
    ones that were deleted between the selection and the refresh.
    """
    if not node_name:
        return False
    if not cmds.objExists(node_name):
        return False
    try:
        if not cmds.objectType(node_name, isType="shadingEngine"):
            return False
    except (RuntimeError, ValueError):
        return False
    for attr in ("a3obTexture", "a3obMaterial"):
        try:
            if cmds.attributeQuery(attr, node=node_name, exists=True):
                return True
        except (RuntimeError, ValueError):
            continue
    return False


def build_section(node_name):
    """The ``AETemplateCustomContent`` callback. Returns immediately when the node is not
    ours — which is almost every time it fires."""
    if not should_show_section(node_name):
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
    """Build the section's controls once. Called by the MEL ``-callCustom`` new proc."""
    node = _node_of(plug)
    cmds.setUITemplate("attributeEditorTemplate", pushTemplate=True)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=2)
    _CONTROLS["texture"] = _path_row(
        "Texture", "The DayZ .paa this material uses (mod-relative, e.g. data\\helmet_co.paa)",
        "texture", "Texture (*.paa);;All Files (*.*)")
    _CONTROLS["material"] = _path_row(
        "Material", "The DayZ .rvmat this material uses (mod-relative)",
        "rvmat", "Material (*.rvmat);;All Files (*.*)")
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(145, 220),
                   columnAttach=[(1, "right", 5), (2, "both", 0)])
    cmds.text(label="")
    _CONTROLS["faces"] = cmds.button(
        label="Select Faces", command=lambda *_: _select_faces(),
        annotation="Select the faces this material is assigned to, on the selected mesh(es). "
                   "Hypershade can select objects by material but not faces.")
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.setUITemplate(popTemplate=True)
    _repoint(node)


def section_replace(plug):
    """Re-point the existing controls at whichever node the AE is now showing."""
    _repoint(_node_of(plug))


def _node_of(plug):
    return (plug or "").split(".")[0]


def _path_row(label, annotation, recent_key, file_filter):
    """A label, an editable path field, and browse / recent / clear buttons.

    Plain Maya UI (``rowLayout``/``textField``), not Qt: these controls live inside Maya's own
    Attribute Editor layout and have to be parented into it.
    """
    cmds.rowLayout(numberOfColumns=5, adjustableColumn=2,
                   columnWidth5=(145, 200, 26, 26, 26),
                   columnAttach=[(1, "right", 5), (2, "both", 0), (3, "both", 2),
                                 (4, "both", 2), (5, "both", 2)])
    cmds.text(label=label)
    field = cmds.textField(annotation=annotation, changeCommand=lambda *_: _write_from_controls())
    cmds.symbolButton(image="fileOpen.png", annotation="Browse for a file",
                      command=lambda *_: _browse(field, file_filter))
    recent = cmds.symbolButton(image="menuIconEdit.png",
                               annotation="Recently used paths")
    cmds.popupMenu(parent=recent, button=1,
                   postMenuCommand=lambda menu, *_: _fill_recent_menu(menu, field, recent_key))
    cmds.symbolButton(image="deleteActive.png", annotation="Clear this path",
                      command=lambda *_: _set_field(field, "", write=True))
    cmds.setParent("..")
    return field


def _repoint(node):
    """Show ``node``'s stored paths. A read — it must not write anything back."""
    _CONTROLS["node"] = node
    for key, attr in (("texture", "a3obTexture"), ("material", "a3obMaterial")):
        field = _CONTROLS.get(key)
        if field and cmds.textField(field, exists=True):
            _set_field(field, _read_attr(node, attr))


def _read_attr(node, attr):
    if not node or not cmds.objExists(node):
        return ""
    try:
        if not cmds.attributeQuery(attr, node=node, exists=True):
            return ""
        return cmds.getAttr(node + "." + attr) or ""
    except (RuntimeError, ValueError):
        return ""


def _set_field(field, value, write=False):
    if not field or not cmds.textField(field, exists=True):
        return
    cmds.textField(field, edit=True, text=value or "")
    if write:
        _write_from_controls()


def _fill_recent_menu(menu, field, recent_key):
    from a3ob.ui.recent import recent_paths

    cmds.popupMenu(menu, edit=True, deleteAllItems=True)
    paths = recent_paths(recent_key)
    if not paths:
        cmds.menuItem(parent=menu, label="No recent paths", enable=False)
        return
    for path in paths:
        cmds.menuItem(parent=menu, label=path,
                      command=lambda _flag=False, _path=path: _set_field(field, _path, write=True))


def _browse(field, file_filter):
    selected = cmds.fileDialog2(fileMode=1, fileFilter=file_filter,
                                caption="Select a DayZ path")
    if not selected:
        return
    _set_field(field, selected[0], write=True)


def _write_from_controls():
    """Persist both paths onto the shading network. Edits are instant — there is no Apply
    button and none is added.

    Imported inside the function: ``a3ob.ui.actions.materials`` star-imports
    ``a3ob.ui.entry``, and this module must stay a leaf.
    """
    node = _CONTROLS.get("node")
    if not node or not cmds.objExists(node):
        return set()
    texture = _field_text("texture")
    material = _field_text("material")

    from a3ob.ui.actions.materials import write_material_metadata

    written = write_material_metadata(node, texture, material)
    if not written:
        cmds.warning("Material metadata target was deleted")
        return written
    # Show what was actually stored: write_material_metadata normalises the paths, and a
    # field still showing "P:/data/x.paa" beside an attribute holding "data\x.paa" is a lie
    # the user has no way to see through.
    _repoint(node)
    _reresolve_textures()
    return written


def _reresolve_textures():
    from a3ob.mayabridge import paatex

    try:
        return paatex.assign_pending_textures()
    except Exception:  # noqa: BLE001 - a missing/undecodable .paa must not block the edit
        return 0


def _field_text(key):
    field = _CONTROLS.get(key)
    if not field or not cmds.textField(field, exists=True):
        return ""
    return cmds.textField(field, query=True, text=True) or ""


def _select_faces():
    from a3ob.ui.actions.materials import select_faces_for_shading_group

    node = _CONTROLS.get("node")
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
    "should_show_section",
    "build_section",
    "section_new",
    "section_replace",
]
