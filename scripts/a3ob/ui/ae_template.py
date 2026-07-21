"""The "DayZ Material" section in Maya's Attribute Editor.

Phase 3d retires the Materials dock panel: per-material editing belongs where a Maya user
already looks for material attributes. Selecting a mesh face-assigned to a DayZ material and
opening the Attribute Editor's shading-group tab now shows Texture and Material right under
Maya's own Shading Group Attributes.

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

**Why ``-addControl`` and not ``-callCustom``.** Measured in a live Maya 2027 session, with the
hook confirmed firing: **``editorTemplate -callCustom`` never invokes its procs from inside the
``AETemplateCustomContent`` hook.** ``beginLayout``/``endLayout`` DO take effect, so the section
rendered as an empty frame on every shading engine. ``-addControl`` works, ``-label`` overrides
Maya's auto-prettified "A 3ob Texture", and the change command fires with the NODE name. Maya
owns those native controls and re-points them itself when the AE switches nodes, which is why
this module keeps no per-tab bookkeeping at all — the whole ``_SECTIONS`` layer the proc pair
needed is gone with it. Building raw UI into the hook's parent renders, but cannot re-point (the
hook fires once per node type per tab), so it was rejected.

None of that is provable from a headless test: ``cmds.editorTemplate`` no-ops in batch. What the
mayapy suite pins is registration, the predicate, and :func:`on_attribute_edited` called
directly; whether the section RENDERS stays on the author's live-Maya list.

**This module is a leaf.** ``maya.cmds``, ``maya.mel`` and the Maya-free attribute schema only.
Every module in ``a3ob.ui.actions`` star-imports ``a3ob.ui.entry``, so importing one at module
level would close the very cycle ``entry._build_qt_dock``'s lazy import exists to prevent — the
write helpers are therefore imported INSIDE the functions that call them.

**``should_show_section`` is a silent read.** It runs for every node the user selects in the
Attribute Editor. It must not warn, must not write, and must not dirty the scene: a refresh
path that warned once turned clicking any prop into Script Editor spam, and a read path that
normalised on read dirtied the scene so Maya asked "Save changes?" after a read-only session.

**The predicate gates the declaration, once.** With native controls there is no cached-template
problem to work around, so the section is declared only for a shading engine that already
carries the metadata — a plain one gets nothing at all, rather than an empty frame.
"""

import maya.cmds as cmds
import maya.mel as mel

from a3ob.mayabridge.attributes import A

OWNER = "MayaObjectBuilder"
HOOK = "AETemplateCustomContent"
SECTION_LABEL = "DayZ Material"

# The SHADING GROUP entries, not the shader ones: the long names are identical and only the
# short names differ (`a3sgtx`/`a3sgmt` vs `a3tx`/`a3mt`), and this section lives on a
# `shadingEngine`. Never change a short name — 33 long+short pairs are a hard on-scene contract
# pinned by tests/python/test_attr_schema.py.
SG_TEXTURE = A.SG_TEXTURE[0]
SG_MATERIAL = A.SG_MATERIAL[0]

CHANGE_PROC = "a3obDayZMaterialAttributeChanged"

# `editorTemplate` takes a proc NAME, so the change command needs a MEL shim. It receives the
# node name — measured, not the attribute name.
_MEL_PROCS = """
global proc %(change)s(string $node) {
    python("import a3ob.ui.ae_template as _a3ob_ae; _a3ob_ae.on_attribute_edited('" + $node + "')");
}
""" % {"change": CHANGE_PROC}


# --------------------------------------------------------------------------- registration


def install():
    """Register the section callback under our own owner. Idempotent.

    Clears first: ``show_plugin_ui`` can run more than once in a session, and a second
    registration would stack a duplicate that then declares the section twice on every tab.
    """
    uninstall()
    mel.eval(_MEL_PROCS)
    cmds.callbacks(addCallback=build_section, hook=HOOK, owner=OWNER)


def uninstall():
    """Clear the section callback. Safe to call when nothing is registered.

    A callback that outlives what it points at is the exit-time crash class
    ``entry._delete_qt_dock`` names — this is the half of that pairing for the AE hook.
    """
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
    for attr in (SG_TEXTURE, SG_MATERIAL):
        try:
            if cmds.attributeQuery(attr, node=node_name, exists=True):
                return True
        except (RuntimeError, ValueError):
            continue
    return False


def build_section(node_name):
    """The ``AETemplateCustomContent`` callback. Declares the section for a shading engine
    carrying the DayZ metadata, and returns immediately for everything else — which is almost
    every time it fires.

    The old ``-callCustom`` design had to declare the section for EVERY shading engine and
    then show or hide it from the replace proc, because the AE caches a template per node type
    per tab and thereafter only re-points it. Native ``-addControl`` controls are re-pointed by
    Maya itself, so that asymmetry is gone and the predicate can gate the declaration directly.
    """
    if not should_show_section(node_name):
        return
    _begin_section(node_name)


def _begin_section(node_name):
    """Declare the section with native controls.

    ``-callCustom`` is NOT used: measured in live Maya, its procs never fire from inside the
    ``AETemplateCustomContent`` hook, which is what made this section render as an empty frame.
    ``-addControl`` works, ``-label`` overrides Maya's auto-prettified "A 3ob Texture", and the
    change command receives the node name. Maya re-points these controls on its own.

    ``editorTemplate`` no-ops in batch rather than raising, so this body runs end to end under
    mayapy while building nothing — which is why the mayapy test can drive the hook at all, and
    equally why it can prove nothing about how the section RENDERS.
    """
    cmds.editorTemplate(beginLayout=SECTION_LABEL, collapse=False)
    for attribute, label in ((SG_TEXTURE, "Texture"), (SG_MATERIAL, "Material")):
        cmds.editorTemplate(attribute, CHANGE_PROC, addControl=True, label=label)
    cmds.editorTemplate(endLayout=True)


# ----------------------------------------------------------------------------------- edits


def on_attribute_edited(node_name):
    """Persist an edit the native control already wrote to ``node_name``. Returns the set of
    node names written to.

    The change command's whole job, and the reason it is a plain function taking a node name:
    it is callable — and therefore testable — with no UI at all.

    Maya's own control has already stored the user's raw text on the attribute by the time this
    fires, so both paths are read BACK off the node and pushed through
    ``write_material_metadata``, which normalises them ("P:/data/x.paa" -> "data\\x.paa"),
    records them in the recent-path history, and fans them out to the material node and every
    other shading engine sharing it.

    A node carrying NEITHER attribute is left alone: the section is never declared for one, so
    a callback reaching here against one is stale, and writing would silently mark a node the
    plugin never marked.

    A name containing a ``.`` is rejected outright. The change command was measured receiving
    the NODE name, but ``cmds.objExists`` and ``attributeQuery`` both answer happily for a PLUG
    ("armourSG.a3obTexture"), so a future change that passed one instead would sail past both
    guards and raise ``ValueError: No object matches name: armourSG.a3obTexture.surfaceShader``
    from inside ``materials.py``. Failing here, quietly and at the seam, is the alternative.


    Imported inside the function: ``a3ob.ui.actions.materials`` star-imports ``a3ob.ui.entry``,
    and this module must stay a leaf.
    """
    if not node_name or "." in node_name or not cmds.objExists(node_name):
        return set()
    if not (_has_attr(node_name, SG_TEXTURE) or _has_attr(node_name, SG_MATERIAL)):
        return set()
    texture = _read_attr(node_name, SG_TEXTURE)
    material = _read_attr(node_name, SG_MATERIAL)

    from a3ob.ui.actions.materials import write_material_metadata

    written = write_material_metadata(node_name, texture, material)
    if not written:
        cmds.warning("Material metadata target was deleted")
        return written
    _reresolve_textures()
    return written


def _has_attr(node, attr):
    try:
        return bool(cmds.attributeQuery(attr, node=node, exists=True))
    except (RuntimeError, ValueError):
        return False


def _read_attr(node, attr):
    if not node or not cmds.objExists(node):
        return ""
    try:
        if not cmds.attributeQuery(attr, node=node, exists=True):
            return ""
        return cmds.getAttr(node + "." + attr) or ""
    except (RuntimeError, ValueError):
        return ""


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


__all__ = [
    "OWNER",
    "HOOK",
    "SECTION_LABEL",
    "SG_TEXTURE",
    "SG_MATERIAL",
    "CHANGE_PROC",
    "install",
    "uninstall",
    "is_shading_engine",
    "should_show_section",
    "build_section",
    "on_attribute_edited",
]
