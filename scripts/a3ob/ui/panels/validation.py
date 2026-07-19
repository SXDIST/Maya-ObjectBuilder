"""validation panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class ValidationPanelMixin:
    def _build_validation_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)
        layout.addWidget(_hint("Validate before export. Scene = every LOD; Selection = selected only."))

        buttons = qt_widgets.QHBoxLayout()
        buttons.addWidget(_qt_button("Scene", lambda: self.run_validation(False), "Validate every Object Builder LOD in the scene.", ":/confirm.png"))
        buttons.addWidget(_qt_button("Selection", lambda: self.run_validation(True), "Validate only the selected LODs.", ":/confirm.png"))
        layout.addLayout(buttons)

        layout.addWidget(_hint("Skin weights: finds vertices whose weights disagree with their "
                               "neighbours — weight-transfer artefacts, invisible in bind pose. "
                               "Fix the selection with Skin > Smooth Skin Weights."))
        layout.addWidget(_qt_button("Select Skin Outliers", lambda: self.run_skin_weights(),
                                    "Select skin-weight outlier vertices, then fix them with "
                                    "Maya's Skin > Smooth Skin Weights.", ":/aselect.png"))

        self.validation_summary = _hint("Not validated yet.")
        layout.addWidget(self.validation_summary)

        self.validation_list = qt_widgets.QListWidget()
        self.validation_list.currentItemChanged.connect(lambda *_: self._select_validation_node())
        layout.addWidget(self.validation_list, 1)
        return widget


    def run_validation(self, selection_only):
        rows = _run_validation(selection_only)
        self._populate_validation(rows)


    def run_skin_weights(self):
        count = _run_skin_weights()
        if getattr(self, "validation_summary", None) is None:
            return
        if count == 0:
            self.validation_summary.setText("No skin weight outliers found ✓")
        else:
            self.validation_summary.setText(
                "Selected {0} outlier vertex(es) — fix with Skin > Smooth Skin Weights.".format(count))


    def _populate_validation(self, rows):
        if getattr(self, "validation_list", None) is None:
            return
        self.validation_list.blockSignals(True)
        self.validation_list.clear()
        errors = warnings = 0
        for row in rows or []:
            parts = row.split("|", 2)
            if len(parts) != 3:
                continue
            severity, node, message = parts
            if severity == "error":
                errors += 1
            else:
                warnings += 1
            text = message + ("  ·  " + node if node else "")
            item = qt_widgets.QListWidgetItem(text)
            icon = _qt_icon(":/error.png" if severity == "error" else ":/caution.png")
            if icon is not None and not icon.isNull():
                item.setIcon(icon)
            item.setData(qt_core.Qt.UserRole, node)
            self.validation_list.addItem(item)
        self.validation_list.blockSignals(False)
        if not rows:
            self.validation_summary.setText("No issues found ✓")
        else:
            self.validation_summary.setText("{0} error(s), {1} warning(s) — click a row to select it.".format(errors, warnings))


    def _select_validation_node(self):
        current = self.validation_list.currentItem() if getattr(self, "validation_list", None) is not None else None
        node = current.data(qt_core.Qt.UserRole) if current is not None else None
        if node and cmds.objExists(node):
            cmds.select(node, replace=True)
