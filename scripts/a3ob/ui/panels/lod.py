"""lod panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class LodPanelMixin:
    def _build_memory_points_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)
        layout.addWidget(_hint(
            "Add Memory Point — new named locator. Add Point to Selection — "
            "adds a second point to the selected one (auto-groups them)."
        ))
        mem_buttons = qt_widgets.QHBoxLayout()
        mem_buttons.addWidget(_qt_button("Add Memory Point", add_memory_point, "Create a new named locator under the selected Memory LOD.", ":/locator.png"))
        mem_buttons.addWidget(_qt_button("Add Point to Selection", add_point_to_selection, "Add another locator to the same named selection as the selected memory point.", ":/locator.png"))
        layout.addLayout(mem_buttons)
        return widget


    def _update_memory_points_visibility(self):
        """Silent query, called from refresh_lod_list() as part of the LODs refresh —
        the panel this used to belong to (LOD Properties) is gone, but Memory Points
        still needs to know whether the selected LOD is a Memory LOD."""
        if self.memory_points_group is None:
            return
        selected_lod = _selected_lod_transform()
        if selected_lod:
            lod_type = _safe_get_attr(selected_lod, "a3obLodType", -1)
            self.memory_points_group.setVisible(lod_type == MEMORY_LOD_TYPE)
        else:
            self.memory_points_group.setVisible(False)


__all__ = ["MayaObjectBuilderDock"]

