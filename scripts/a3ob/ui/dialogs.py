"""Modal dialogs for creating proxies and flag sets.

A leaf module: Qt and Maya's own APIs only. It must never import from a3ob.ui.actions — every
module there star-imports a3ob.ui.entry, and importing back into it would close the
actions/entry/dock cycle that entry._build_qt_dock's lazy import exists to break.

flag_dialog deliberately has no scriptJob following the live selection: QDialog.exec() is
application-modal (Qt's default, and nothing here calls setWindowModality), so the viewport is
unclickable and SelectionChanged cannot fire from user action while the dialog is open. An
earlier version wired one up anyway; it was dead code by construction and was removed.
"""

import maya.api.OpenMaya as om

from a3ob.ui._qt import *  # noqa: F401,F403


def proxy_creation_mode():
    """"components" when the selection would build a proxy selection set, else "standalone".

    A silent read: it inspects the selection and writes nothing.

    The predicate mirrors ``create_proxy_selection_set`` in
    ``mayabridge/commands/helpers/sets.py`` exactly — a mesh DAG node carrying a non-null
    component — because this function decides the ``fromSelection`` flag that command path
    receives. It is deliberately NOT a scan for ``.f[``/``.vtx[`` markers in the selection
    strings: the command accepts ANY mesh component, so edges (``.e[``) and UVs (``.map[``)
    build a real set, and a marker list that omitted them classified those selections as
    "standalone", passed fromSelection=False and silently created nothing.

    Duplicated rather than imported: this is a ui leaf and the helper is a private name behind
    a star-importing mayabridge module. Measured against the command for faces, vertices,
    edges, UVs, whole transforms, bare mesh shapes, an empty selection and a mixed selection —
    the two agree on all eight."""
    sel = om.MGlobal.getActiveSelectionList()
    for i in range(sel.length()):
        try:
            dag_path, component = sel.getComponent(i)
        except Exception:
            continue
        if not dag_path.isValid():
            continue
        if dag_path.node().hasFn(om.MFn.kMesh) and not component.isNull():
            return "components"
    return "standalone"


_MODE_TEXT = {
    "components": "Will build the proxy from the selected components.",
    "standalone": "No components are selected — will create a standalone proxy placeholder.",
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

    # Stated once, at open time, and it cannot go stale: exec() below is application-modal
    # (Qt's default, and nothing here calls setWindowModality), so the viewport is
    # unclickable while the dialog is up and the selection cannot change under the label.
    # create_proxy_from_ui re-reads proxy_creation_mode() when it actually creates, so the
    # flag handed to a3obProxy is the one this label described.
    mode_label = qt_widgets.QLabel(_MODE_TEXT[proxy_creation_mode()])
    mode_label.setWordWrap(True)
    layout.addWidget(mode_label)

    buttons = qt_widgets.QDialogButtonBox(
        qt_widgets.QDialogButtonBox.Ok | qt_widgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()

    if not accepted:
        return None
    return path_field._line_edit.text().strip(), index_field.value()


def flag_dialog(dock):
    """Ask for a flag's component type, value and set name.

    Returns (component, value, name) with component already lowercased for a3obSetFlag, or
    None if cancelled. The command itself rejects a zero value and any component outside
    vertex/face, so this dialog does not duplicate that check — it only refuses an empty
    name, which the command would otherwise turn into the placeholder "a3ob_flag#"."""
    dialog = qt_widgets.QDialog(dock)
    dialog.setWindowTitle("Create Flag Set")
    layout = qt_widgets.QVBoxLayout(dialog)

    form_holder = qt_widgets.QWidget()
    form = qt_widgets.QFormLayout(form_holder)
    form.setContentsMargins(0, 0, 0, 0)
    component_combo = qt_widgets.QComboBox()
    component_combo.addItems(["Face", "Vertex"])
    value_field = qt_widgets.QSpinBox()
    value_field.setRange(-2147483648, 2147483647)
    value_field.setValue(1)
    name_field = qt_widgets.QLineEdit("a3ob_flag")
    form.addRow("Component", component_combo)
    form.addRow("Value", value_field)
    form.addRow("Set name", name_field)
    layout.addWidget(form_holder)

    hint = qt_widgets.QLabel("Select mesh vertices or faces before creating a flag set.")
    hint.setWordWrap(True)
    layout.addWidget(hint)

    buttons = qt_widgets.QDialogButtonBox(
        qt_widgets.QDialogButtonBox.Ok | qt_widgets.QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    accepted = dialog.exec_() if hasattr(dialog, "exec_") else dialog.exec()
    if not accepted:
        return None
    return (component_combo.currentText().lower(), value_field.value(),
            name_field.text().strip())
