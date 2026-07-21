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

texture_root_status() and resolution_source_label() are the testable seams — see
tests/mayapy/preferences_texture_root.py. show_preferences() builds a real QDialog and is NOT
covered there: a QWidget under mayapy segfaults with no traceback unless a QApplication existed
before maya.standalone.initialize() ran.

No dock to borrow _path_picker (dock.py) from here: this window must open whether or not the
dock is up (it is reached from the menu, which exists independently of the dock), and
dock._path_picker is a bound method on the dock instance, not a free function. The texture-root
row is therefore built directly, deliberately without the dock's recent-paths dropdown — that
mechanism (dock._show_recent_paths_menu) is likewise a dock method, and duplicating it for a
window that holds exactly one path field was judged not worth it.
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

    # --- Check a texture path ---------------------------------------------------------
    layout.addWidget(_section_label("Check a texture path"))
    layout.addWidget(_hint(
        "Names which source would resolve a given P3D-relative texture path: the configured "
        "root, P:/, or a filename search — the same ambiguity the status line above warns "
        "about."))
    check_row = qt_widgets.QHBoxLayout()
    check_field = qt_widgets.QLineEdit()
    check_field.setPlaceholderText(r"e.g. mod\data\jacket_co.paa")
    check_button = qt_widgets.QPushButton("Check")
    check_row.addWidget(check_field, 1)
    check_row.addWidget(check_button)
    layout.addLayout(check_row)
    check_result = _hint("")

    def _on_check():
        check_result.setText(resolution_source_label(check_field.text().strip()))

    check_button.clicked.connect(_on_check)
    layout.addWidget(check_result)

    buttons = qt_widgets.QDialogButtonBox(qt_widgets.QDialogButtonBox.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    return dialog


__all__ = [
    "texture_root_status",
    "resolution_source_label",
    "show_preferences",
]
