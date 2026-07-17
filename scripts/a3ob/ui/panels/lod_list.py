"""LOD list panel — the dock's navigation hub: every LOD in the scene at a glance."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class LodListPanelMixin:
    def _build_lod_list_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        self.lod_list_context = _hint("No DayZ LODs in the scene yet.")
        layout.addWidget(self.lod_list_context)

        self.lod_list = qt_widgets.QListWidget()
        self.lod_list.currentItemChanged.connect(lambda *_: self._on_lod_list_selected())
        self.lod_list.itemDoubleClicked.connect(lambda *_: self._frame_selected_lod())
        layout.addWidget(self.lod_list, 1)

        row = qt_widgets.QHBoxLayout()
        row.addWidget(_qt_button("Frame", self._frame_selected_lod, "Select and frame the LOD in the viewport.", ":/eye.png"))
        row.addWidget(_qt_button("Isolate", self._toggle_isolate_lod, "Toggle viewport isolation of the selected LOD (non-destructive).", ":/ghostOff.png"))
        layout.addLayout(row)

        self.refresh_lod_list()
        return widget


    def _selected_lod_list_node(self):
        current = self.lod_list.currentItem() if getattr(self, "lod_list", None) is not None else None
        if current is None:
            return None
        node = current.data(qt_core.Qt.UserRole)
        return node if node and cmds.objExists(node) else None


    def _on_lod_list_selected(self):
        if getattr(self, "_syncing_lod_list", False):
            return
        node = self._selected_lod_list_node()
        if node:
            cmds.select(node, replace=True)  # SelectionChanged job refreshes the other panels


    def _frame_selected_lod(self):
        node = self._selected_lod_list_node()
        if not node:
            return
        cmds.select(node, replace=True)
        try:
            cmds.viewFit()
        except RuntimeError:
            pass


    def _toggle_isolate_lod(self):
        node = self._selected_lod_list_node()
        if not node:
            return
        panel = cmds.getPanel(withFocus=True)
        model_panels = cmds.getPanel(type="modelPanel") or []
        if panel not in model_panels:
            panel = model_panels[0] if model_panels else None
        if not panel:
            return
        cmds.select(node, replace=True)
        new_state = not cmds.isolateSelect(panel, query=True, state=True)
        cmds.isolateSelect(panel, state=new_state)
        if new_state:
            cmds.isolateSelect(panel, addSelected=True)


    def refresh_lod_list(self):
        if getattr(self, "lod_list", None) is None:
            return
        prev = self._selected_lod_list_node()
        active = _selected_lod_transform()
        rows = lod_overview()
        self._syncing_lod_list = True
        self.lod_list.blockSignals(True)
        self.lod_list.clear()
        restore_row = -1
        for row in rows:
            text = "{0}  ·  {1} tris".format(row["label"], row["tris"])
            if row["selections"]:
                text += "  ·  {0} sel".format(row["selections"])
            item = qt_widgets.QListWidgetItem(text)
            icon = _qt_icon(lod_type_icon(row["type"]))
            if icon is not None and not icon.isNull():
                item.setIcon(icon)
            item.setData(qt_core.Qt.UserRole, row["node"])
            item.setToolTip(row["node"])
            self.lod_list.addItem(item)
            target = prev or active
            if target is not None and row["node"] == target:
                restore_row = self.lod_list.count() - 1
        if restore_row >= 0:
            self.lod_list.setCurrentRow(restore_row)
        self.lod_list.blockSignals(False)
        self._syncing_lod_list = False

        if self.lod_list_context is not None:
            if not rows:
                self.lod_list_context.setText("No DayZ LODs in the scene yet.")
            elif active:
                self.lod_list_context.setText("Active: {0}".format(_lod_name_from_transform(active)))
            else:
                self.lod_list_context.setText("{0} LODs — click one to select it.".format(len(rows)))


__all__ = ["LodListPanelMixin"]
