"""Modal dialogs for creating proxies and flags.

A leaf module: Qt and maya.cmds only. It must never import from a3ob.ui.actions — every
module there star-imports a3ob.ui.entry, and importing back into it would close the
actions/entry/dock cycle that entry._build_qt_dock's lazy import exists to break.
"""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403


def proxy_creation_mode():
    """"components" when mesh components are selected, otherwise "standalone".

    A silent read: it inspects the selection and writes nothing. The old panel offered this
    as a checkbox, which allowed asking for a mode the selection could not deliver."""
    for item in cmds.ls(selection=True, long=True) or []:
        if ".f[" in item or ".vtx[" in item:
            return "components"
    return "standalone"


_MODE_TEXT = {
    "components": "Will build the proxy from the selected components.",
    "standalone": "Nothing is selected — will create a standalone proxy placeholder.",
}


def proxy_dialog(dock):
    """Ask for a proxy path and index. Returns (path, index), or None if cancelled.

    The path picker is the dock's own _path_picker, so the recent-paths dropdown behaves
    exactly as it did in the retired Proxies panel."""
    dialog = qt_widgets.QDialog(dock)
    dialog.setWindowTitle("Create Proxy")
    layout = qt_widgets.QVBoxLayout(dialog)

    form_holder = qt_widgets.QWidget()
    form = qt_widgets.QFormLayout(form_holder)
    form.setContentsMargins(0, 0, 0, 0)
    path_field = dock._path_picker("Proxy path", "Select proxy P3D", 1,
                                   "Arma P3D (*.p3d)", recent_key="proxy")
    index_field = qt_widgets.QSpinBox()
    index_field.setRange(0, 2147483647)
    index_field.setValue(1)
    form.addRow("Path", path_field)
    form.addRow("Index", index_field)
    layout.addWidget(form_holder)

    mode_label = qt_widgets.QLabel(_MODE_TEXT[proxy_creation_mode()])
    mode_label.setWordWrap(True)
    layout.addWidget(mode_label)

    # The mode follows the viewport selection while the dialog is open, so the stated
    # behaviour never goes stale under the user. The job is explicitly killed in the
    # `finally` below when the dialog closes — that is what bounds its lifetime, not a
    # `parent=` flag: `scriptJob -parent` expects a Maya UI control PATH, not a Qt
    # `objectName()`, and this dialog is never given one (a fresh QDialog's objectName()
    # is "" unless set explicitly), so `parent=` would be silently inert here.
    job = cmds.scriptJob(event=["SelectionChanged",
                                lambda: mode_label.setText(_MODE_TEXT[proxy_creation_mode()])],
                         protected=False)

    buttons = qt_widgets.QDialogButtonBox(
        qt_widgets.QDialogButtonBox.Ok | qt_widgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    try:
        accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    finally:
        # `job` can be falsy (e.g. no Maya UI to attach to) — guard before querying
        # `exists`, which raises TypeError on anything but an int job id.
        if job and cmds.scriptJob(exists=job):
            cmds.scriptJob(kill=job, force=True)

    if not accepted:
        return None
    return path_field._line_edit.text().strip(), index_field.value()
