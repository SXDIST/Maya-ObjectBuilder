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
        self.lod_list.setContextMenuPolicy(qt_core.Qt.CustomContextMenu)
        self.lod_list.customContextMenuRequested.connect(self._show_lod_context_menu)
        layout.addWidget(self.lod_list, 1)

        row = qt_widgets.QHBoxLayout()
        add_button = qt_widgets.QPushButton("Add LOD")
        _add_icon = _qt_icon(":/create.png")
        if _add_icon is not None and not _add_icon.isNull():
            add_button.setIcon(_add_icon)
        add_button.setToolTip("Add a new empty LOD of a chosen type.")
        add_button.clicked.connect(lambda: self._show_add_lod_menu(add_button))
        row.addWidget(add_button)
        row.addWidget(_qt_button("Frame", self._frame_selected_lod, "Select and frame the LOD in the viewport.", ":/eye.png"))
        row.addWidget(_qt_button("Isolate", self._toggle_isolate_lod, "Toggle viewport isolation of the selected LOD (non-destructive).", ":/ghostOff.png"))
        layout.addLayout(row)

        self.refresh_lod_list()
        return widget


    # Common LOD types offered by the Add menu (label comes from LOD_DEFINITIONS).
    _ADD_LOD_TYPES = (0, 6, 7, 14, 15, 4, 9, 11, 10, 12, 13)

    def _show_add_lod_menu(self, anchor):
        menu = qt_widgets.QMenu(self)
        labels = {d["type"]: d["label"] for d in LOD_DEFINITIONS}
        for lod_type in self._ADD_LOD_TYPES:
            label = labels.get(lod_type, "LOD %d" % lod_type)
            icon = _qt_icon(lod_type_icon(lod_type))
            action = menu.addAction(label)
            if icon is not None and not icon.isNull():
                action.setIcon(icon)
            action.triggered.connect(lambda checked=False, t=lod_type: create_lod_type(t))
        menu.popup(anchor.mapToGlobal(anchor.rect().bottomLeft()))


    def _show_lod_context_menu(self, pos):
        item = self.lod_list.itemAt(pos)
        if item is None:
            return
        node = item.data(qt_core.Qt.UserRole)
        if not node or not cmds.objExists(node):
            return
        menu = qt_widgets.QMenu(self)
        menu.addAction("Frame").triggered.connect(lambda *_: self._frame_selected_lod())
        menu.addAction("Isolate").triggered.connect(lambda *_: self._toggle_isolate_lod())
        menu.addSeparator()
        menu.addAction("Rename…").triggered.connect(lambda *_: self._rename_lod(node))
        menu.addAction("Duplicate").triggered.connect(lambda *_: self._duplicate_lod(node))
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(lambda *_: self._delete_lod(node))
        menu.popup(self.lod_list.viewport().mapToGlobal(pos))


    def _rename_lod(self, node):
        leaf = node.split("|")[-1].split(":")[-1]
        result = cmds.promptDialog(title="Rename LOD", message="New name:", text=leaf,
                                   button=["OK", "Cancel"], defaultButton="OK", cancelButton="Cancel", dismissString="Cancel")
        if result != "OK":
            return
        new_name = cmds.promptDialog(query=True, text=True).strip()
        if new_name and cmds.objExists(node):
            cmds.rename(node, new_name)
            self.refresh_lod_list()


    def _duplicate_lod(self, node):
        if not cmds.objExists(node):
            return
        duplicated = cmds.duplicate(node, returnRootsOnly=True)
        if duplicated:
            cmds.select(duplicated[0], replace=True)
        self.refresh_lod_list()


    def _delete_lod(self, node):
        if cmds.objExists(node):
            cmds.delete(node)
        self.refresh_lod_list()


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
