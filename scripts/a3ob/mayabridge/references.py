"""Reference assets: the DayZ body proxy and the skeleton, saved once and added by a button.

These are Bohemia assets. They ship with the plugin under `assets/references/`, licensed
separately under ADPL-SA (see `assets/references/LICENSE`) since that licence is
non-commercial/Arma-DayZ-only/share-alike and incompatible with this repo's MIT code. The
installer seeds them into the user's Maya folder on install, without overwriting a file the
user already has there; from then on they live in the user's Maya folder and are referenced
by optionVar, the same way the texture root already works.

Workflow: set the body up once (materials, `a3obTexture` / `a3obMaterial` paths, whatever else
belongs on it), save it as a reference, and from then on one button drops it into any scene
with everything already attached.
"""

import os

import maya.cmds as cmds

# kind -> (optionVar, human name, default file stem)
KINDS = {
    "male_body": ("MayaObjectBuilder_ref_male_body", "male body", "dayz_male_body"),
    "female_body": ("MayaObjectBuilder_ref_female_body", "female body", "dayz_female_body"),
    "skeleton": ("MayaObjectBuilder_ref_skeleton", "skeleton", "dayz_skeleton"),
}


def default_directory():
    """Where reference assets live by default: alongside the user's other Maya data."""
    documents = cmds.internalVar(userAppDir=True) or ""
    return os.path.join(documents, "MayaObjectBuilder", "references")


def reference_path(kind):
    """Configured path for a reference kind, or '' when it has not been saved yet."""
    option_var = KINDS[kind][0]
    if cmds.optionVar(exists=option_var):
        path = cmds.optionVar(query=option_var) or ""
        return path if path and os.path.isfile(path) else ""
    return ""


def set_reference_path(kind, path):
    cmds.optionVar(stringValue=(KINDS[kind][0], path or ""))


def save_reference(kind, path=""):
    """Save the current selection as the reference for ``kind``.

    Exports the selection (with its shading networks, so material paths travel with it) to a
    .ma. ASCII on purpose — it survives Maya version changes better than binary, and these
    files are meant to outlive a release."""
    if kind not in KINDS:
        raise ValueError("unknown reference kind '%s'" % kind)
    if not (cmds.ls(selection=True) or []):
        raise ValueError("select the %s (mesh and/or joints) before saving it as a reference"
                         % KINDS[kind][1])

    target = path
    if not target:
        directory = default_directory()
        if not os.path.isdir(directory):
            os.makedirs(directory)
        target = os.path.join(directory, KINDS[kind][2] + ".ma")

    cmds.file(target, exportSelected=True, type="mayaAscii",
              constructionHistory=True, channels=True, expressions=True,
              shader=True, force=True)
    set_reference_path(kind, target)
    return target


def _make_visible(nodes):
    """Force the imported top-level nodes visible.

    A reference is saved from a working scene, and there the body is usually hidden —
    tucked away while a garment is fitted on it. That hidden state travels into the .ma,
    so the asset arrives invisible and reads as an import that silently did nothing.

    ONLY the top-level nodes are touched. The DayZ rig hides a pile of helper transforms
    further down (Face_Hub, Camera1st_lock_dummy and friends) on purpose, and unhiding
    those would dump rig scaffolding into the viewport. A visibility that is locked or
    driven by a connection is left alone: something else owns it."""
    for node in nodes:
        plug = node + ".visibility"
        try:
            if cmds.getAttr(plug, lock=True):
                continue
            if cmds.listConnections(plug, source=True, destination=False):
                continue
            cmds.setAttr(plug, True)
        except Exception:  # noqa: BLE001 - no visibility plug, or Maya refuses; not fatal
            pass


def add_reference(kind):
    """Import the saved reference into the current scene.

    Returns the new top-level nodes. Import, not reference: the body is meant to be a working
    proxy you can hide, move or bind against, not a read-only link."""
    if kind not in KINDS:
        raise ValueError("unknown reference kind '%s'" % kind)

    path = reference_path(kind)
    if not path:
        raise ValueError(
            "no %s reference saved yet — select one in the scene and use Save, or point the "
            "plugin at an existing .ma file" % KINDS[kind][1])

    before = set(cmds.ls(assemblies=True, long=True) or [])
    cmds.file(path, i=True, type="mayaAscii", ignoreVersion=True,
              mergeNamespacesOnClash=True, namespace=":", preserveReferences=True)
    after = set(cmds.ls(assemblies=True, long=True) or [])
    created = sorted(after - before)
    _make_visible(created)
    return created


__all__ = [
    "KINDS",
    "default_directory",
    "reference_path",
    "set_reference_path",
    "save_reference",
    "add_reference",
]
