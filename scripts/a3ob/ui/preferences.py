"""The Preferences window: the two GLOBAL PAA settings the retired Materials panel also held.

A leaf, like dialogs.py: Qt and maya.cmds only, no import from a3ob.ui.actions — every module
there star-imports a3ob.ui.entry, and importing back into it would close the actions/entry/dock
cycle that entry._build_qt_dock's lazy import exists to prevent.

The panel (scripts/a3ob/ui/panels/materials.py) bundled per-material editing together with two
settings that are scene-global, not per-material: the texture root and alpha->transparency.
Per-material editing has moved to the DayZ Material section in the Attribute Editor
(ui/ae_template.py); these two get their own window instead, reached from the MayaObjectBuilder
menu independently of whether the dock is open. The panel's own copies of both controls are left
in place — panels/materials.py is not this task's file, and a later task retires it wholesale.

texture_root_status(), resolution_source_label() and scene_texture_source_report() are the
testable seams — see tests/mayapy/preferences_texture_root.py. show_preferences() builds a real
QDialog and is NOT covered there: a QWidget under mayapy segfaults with no traceback unless a
QApplication existed before maya.standalone.initialize() ran.

No dock to borrow _path_picker (dock.py) from here: this window must open whether or not the
dock is up (it is reached from the menu, which exists independently of the dock), and
dock._path_picker is a bound method on the dock instance, not a free function. The texture-root
row is therefore built directly, deliberately without the dock's recent-paths dropdown — that
mechanism (dock._show_recent_paths_menu) is likewise a dock method, and duplicating it for a
window that holds exactly one path field was judged not worth it.

The window originally also had a free-text "Check a texture path" box wired to
resolution_source_label(). That is gone: this window is scoped to exactly the two GLOBAL
settings above, and a debug text box was never one of them. What that box was FOR — saying
which source is actually resolving textures, so a stale/unused root cannot fail silently — is
still required, so it is now automatic: scene_texture_source_report() walks the scene's real
a3obTexture values (no user input) and the window displays its message, refreshed on open and
via an explicit Refresh button only. It exists specifically because texture_root_status() can
only say a configured root is present on disk — which is not evidence it is the one actually
resolving anything (the measured failure: an existing root, with P:/ quietly doing the work).
"""

import os

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.widgets import _icon_button, _hint  # noqa: F401


def texture_root_status():
    """{"root": str, "exists": bool, "message": str} — the testable seam behind the window's
    texture-root row.

    A configured root that does not exist is reported as such rather than staying silent: the
    measured scene had MayaObjectBuilder_texture_root pointing at a directory that did not
    exist, and textures kept resolving anyway via P:/ with nothing telling the user why.
    """
    from a3ob.mayabridge.paatex import settings

    root = settings.texture_root()
    if not root:
        return {
            "root": "",
            "exists": False,
            "message": "No texture root configured — .paa textures resolve only via an "
                       "absolute path or P:/.",
        }
    exists = os.path.isdir(root)
    if exists:
        return {"root": root, "exists": True, "message": "Texture root: %s" % root}
    return {
        "root": root,
        "exists": False,
        "message": "Texture root does not exist: %s — it resolves nothing. Textures will "
                   "only be found via P:/ or an absolute path until this is fixed." % root,
    }


_SOURCE_LABELS = {
    "absolute": "an absolute path",
    "configured": "the configured texture root",
    "drive": "P:/",
    "search": "a filename search under the configured texture root",
}


def resolution_source_label(texture_path):
    """Human string naming which source resolved ``texture_path``, built on
    resolve_paa_path_with_source — so the window can say WHICH source actually did the work
    (configured root, P:/, or the basename search) rather than just found/not-found."""
    from a3ob.mayabridge.paatex.resolve import resolve_paa_path_with_source

    resolved, source = resolve_paa_path_with_source(texture_path)
    if resolved is None:
        return "Not found — checked the configured texture root, P:/, and a filename search."
    return "Found via %s: %s" % (_SOURCE_LABELS.get(source, source or "unknown"), resolved)


_SCENE_MATERIAL_LIMIT = 500  # bound: a scene can hold a great many shading engines — sample only
                             # this many rather than scanning unbounded. Same precedent as
                             # resolve.py's _WALK_DIR_LIMIT (a mutable module attribute so a
                             # test can shrink it rather than creating hundreds of real nodes).


def scene_texture_source_report():
    """{"sampled": int, "sources": {source: count}, "unresolved": int, "truncated": bool,
    "message": str} — which source(s) are ACTUALLY resolving the scene's textures right now.

    texture_root_status() can only say a configured root exists on disk; existing is not the
    same as being used. The measured scene had a root that existed while P:/ quietly did the
    work, and nothing said so. This walks the scene's real a3obTexture values — the same
    attribute and enumeration paatex/materials.py's assign_pending_textures and
    apply_alpha_transparency_setting already read (cmds.ls(materials=True), the a3obTexture
    string on the material node) — through resolve_paa_path_with_source and reports what
    actually resolved each one, so a directory merely existing is never mistaken for evidence
    it is in use.

    A scene with no textured materials says so plainly rather than implying a verdict either
    way. A scene whose textures resolve from several different sources names all of them
    rather than collapsing to one.

    Silent read only: no cmds.warning, no scene writes. Meant to be called when the window
    opens or on an explicit refresh — never on a timer or on every selection event.

    Bounded like resolve.py's _WALK_DIR_LIMIT: samples at most _SCENE_MATERIAL_LIMIT materials
    rather than scanning every one, so a scene with a great many shading engines cannot hang
    the window on open.
    """
    from a3ob.mayabridge.paatex.resolve import resolve_paa_path_with_source

    materials = cmds.ls(materials=True) or []
    truncated = len(materials) > _SCENE_MATERIAL_LIMIT
    materials = materials[:_SCENE_MATERIAL_LIMIT]

    sources = {}
    unresolved = 0
    sampled = 0
    for shader in materials:
        if not cmds.attributeQuery("a3obTexture", node=shader, exists=True):
            continue
        texture = cmds.getAttr(shader + ".a3obTexture") or ""
        if not texture:
            continue
        sampled += 1
        resolved, source = resolve_paa_path_with_source(texture)
        if resolved is None:
            unresolved += 1
        else:
            sources[source] = sources.get(source, 0) + 1

    if sampled == 0:
        message = "No textured materials found in this scene — nothing to report."
    elif not sources:
        message = ("Sampled %d textured material(s); none resolved from any source "
                   "(configured root, P:/, or a filename search)." % sampled)
    elif len(sources) == 1:
        (only_source,) = sources
        message = "All resolved textures (%d of %d sampled) are coming from %s." % (
            sources[only_source], sampled,
            _SOURCE_LABELS.get(only_source, only_source or "unknown"))
    else:
        parts = "; ".join(
            "%s: %d" % (_SOURCE_LABELS.get(source, source or "unknown"), count)
            for source, count in sorted(sources.items(), key=lambda item: -item[1]))
        message = ("Resolved textures are coming from MULTIPLE sources (%d sampled) — %s. "
                   "A configured root existing on disk is not evidence it is the one in use."
                   % (sampled, parts))
    if unresolved:
        message += " %d texture(s) could not be resolved at all." % unresolved
    if truncated:
        message += " (sampled the first %d material(s) only)" % _SCENE_MATERIAL_LIMIT

    return {
        "sampled": sampled,
        "sources": sources,
        "unresolved": unresolved,
        "truncated": truncated,
        "message": message,
    }


def _section_label(text):
    label = qt_widgets.QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


def _maya_main_window():
    if not QT_AVAILABLE:
        return None
    pointer = omui.MQtUtil.mainWindow()
    if pointer is None:
        return None
    return wrapInstance(int(pointer), qt_widgets.QWidget)


def show_preferences():
    """Open the Preferences window. Not headlessly testable — see the module docstring.

    Must work whether or not the dock is open: it is reached from the MayaObjectBuilder menu,
    which is built independently of the dock (entry.show_plugin_ui builds the menu once; the
    dock can be closed and reopened many times within the same session).
    """
    if not QT_AVAILABLE:
        cmds.warning("MayaObjectBuilder requires PySide6; Preferences window could not be built.")
        return None

    from a3ob.mayabridge import paatex as _paatex

    dialog = qt_widgets.QDialog(_maya_main_window())
    dialog.setWindowTitle("MayaObjectBuilder Preferences")
    dialog.setMinimumWidth(420)
    layout = qt_widgets.QVBoxLayout(dialog)

    # --- Texture root --------------------------------------------------------------
    layout.addWidget(_section_label("Texture root"))
    root_row = qt_widgets.QHBoxLayout()
    root_field = qt_widgets.QLineEdit(_paatex.texture_root())
    root_field.setPlaceholderText("Folder with .paa (P-drive / mod)")
    root_browse = _icon_button(":/fileOpen.png", "...", "Select the .paa texture root folder")
    root_row.addWidget(root_field, 1)
    root_row.addWidget(root_browse)
    layout.addLayout(root_row)

    status_label = _hint(texture_root_status()["message"])
    layout.addWidget(status_label)

    def _refresh_status():
        status_label.setText(texture_root_status()["message"])

    def _apply_root(path):
        _paatex.set_texture_root(path)
        # Applies to materials already in the scene, not only to future imports — the same
        # call the retired panel's _on_texture_root_edited / _browse_texture_root made.
        count = _paatex.assign_pending_textures()
        _refresh_status()
        cmds.inViewMessage(assistMessage="Texture root set — textured %d material(s)" % count,
                           position="midCenter", fade=True)

    def _on_root_edited():
        _apply_root(root_field.text().strip())

    def _browse_root():
        current = _paatex.texture_root()
        kwargs = {"fileMode": 3, "caption": "Select the .paa texture root folder"}
        if current:
            kwargs["startingDirectory"] = current
        selected = cmds.fileDialog2(**kwargs)
        if not selected:
            return
        root_field.setText(selected[0])
        _apply_root(selected[0])

    root_field.editingFinished.connect(_on_root_edited)
    root_browse.clicked.connect(_browse_root)

    # --- Alpha -> transparency -------------------------------------------------------
    layout.addWidget(_section_label("Alpha → transparency"))
    alpha_check = qt_widgets.QCheckBox("Alpha → transparency (foliage / cut-outs)")
    alpha_check.setToolTip(
        "Off: imported materials stay opaque (solid armour). On: a .paa cut-out alpha "
        "becomes viewport transparency. A DayZ _ca alpha is often a data channel rather "
        "than a cut-out, so this stays off by default.")
    alpha_check.setChecked(_paatex.alpha_transparency_enabled())

    def _on_alpha_toggled(checked):
        _paatex.set_alpha_transparency(checked)
        # Applies to materials already in the scene, not only to future imports — the same
        # call the retired panel's _on_paa_alpha_toggled made.
        _paatex.apply_alpha_transparency_setting()

    alpha_check.toggled.connect(_on_alpha_toggled)
    layout.addWidget(alpha_check)

    # --- Active texture sources -------------------------------------------------------
    # Automatic, not a free-text checker: the window states which source is ACTUALLY
    # resolving the scene's textures without the user typing anything. This is the piece
    # texture_root_status() above cannot say — a configured root existing on disk is not
    # evidence it is the one in use (the measured scene's exact failure: root existed, P:/
    # quietly did the work). Computed on open and on explicit Refresh only — never on a
    # timer, and it never runs while typing.
    layout.addWidget(_section_label("Active texture sources"))
    sources_row = qt_widgets.QHBoxLayout()
    sources_label = _hint(scene_texture_source_report()["message"])
    sources_refresh = qt_widgets.QPushButton("Refresh")
    sources_refresh.setToolTip(
        "Re-scan the scene's textured materials and report which source (configured root, "
        "P:/, or a filename search) actually resolved each one.")
    sources_row.addWidget(sources_label, 1)
    sources_row.addWidget(sources_refresh)
    layout.addLayout(sources_row)

    def _refresh_sources():
        sources_label.setText(scene_texture_source_report()["message"])

    sources_refresh.clicked.connect(_refresh_sources)

    buttons = qt_widgets.QDialogButtonBox(qt_widgets.QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    return dialog


__all__ = [
    "texture_root_status",
    "resolution_source_label",
    "scene_texture_source_report",
    "show_preferences",
]
