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
        layout.addWidget(_hint("Validate before export. Scene = every LOD; Selection = selected only."))
        buttons = qt_widgets.QHBoxLayout()
        buttons.addWidget(_qt_button("Scene", _validate_scene_no_flush, "Validate every Object Builder LOD in the scene.", ":/confirm.png"))
        buttons.addWidget(_qt_button("Selection", _validate_selection_no_flush, "Validate only the selected LODs.", ":/confirm.png"))
        layout.addLayout(buttons)
        layout.addStretch()
        return widget

