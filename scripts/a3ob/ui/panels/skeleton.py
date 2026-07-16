"""skeleton panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class SkeletonPanelMixin:
    def _build_skeleton_section(self):
        widget = qt_widgets.QWidget()
        cfg_layout = qt_widgets.QFormLayout(widget)
        cfg_layout.setContentsMargins(0, 0, 0, 0)
        self.model_cfg_import = self._path_picker("Import path", "Select model.cfg", 1, "Config (*.cfg)")
        self.model_cfg_export = self._path_picker("Export path", "Export model.cfg", 0, "Config (*.cfg)")
        cfg_layout.addRow("Import", self.model_cfg_import)
        cfg_layout.addRow("Export", self.model_cfg_export)
        cfg_buttons = qt_widgets.QHBoxLayout()
        cfg_buttons.addWidget(_qt_button("Import CFG", import_model_cfg_from_ui))
        cfg_buttons.addWidget(_qt_button("Export CFG", export_model_cfg_from_ui))
        cfg_layout.addRow(cfg_buttons)
        return widget


    def model_cfg_import_path(self):
        field = _picker_field(self.model_cfg_import)
        return field.text().strip() if field is not None else ""


    def model_cfg_export_path(self):
        field = _picker_field(self.model_cfg_export)
        return field.text().strip() if field is not None else ""

