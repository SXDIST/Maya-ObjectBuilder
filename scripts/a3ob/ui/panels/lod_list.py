"""LOD list panel — the dock's navigation hub: every LOD in the scene at a glance."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


def _lod_definition_for_type(lod_type):
    for definition in LOD_DEFINITIONS:
        if definition["type"] == lod_type:
            return definition
    return LOD_DEFINITIONS[0]


class LodListPanelMixin:
    def _build_lod_list_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        self.lod_list_context = _hint("No DayZ LODs in the scene yet.")
        layout.addWidget(self.lod_list_context)

        # Track-record fields for the rebuild-only-on-change optimisation: rebuilding a
        # QComboBox + QSpinBox per row on every refresh is wasteful when the set of LOD
        # nodes has not moved (e.g. a plain selection change) — see refresh_lod_list.
        self._lod_row_editors = {}   # node -> {"item", "combo", "spin"}
        self._lod_row_order = ()     # node tuple as of the last full rebuild

        self.lod_list = qt_widgets.QTreeWidget()
        self.lod_list.setColumnCount(4)
        self.lod_list.setHeaderLabels(["LOD", "Type", "Res", "Stats"])
        self.lod_list.setRootIsDecorated(False)
        self.lod_list.setUniformRowHeights(True)
        self.lod_list.setSelectionMode(qt_widgets.QAbstractItemView.SingleSelection)
        self.lod_list.setSelectionBehavior(qt_widgets.QAbstractItemView.SelectRows)
        header = self.lod_list.header()
        header.setSectionResizeMode(0, qt_widgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, qt_widgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, qt_widgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, qt_widgets.QHeaderView.ResizeToContents)
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
        node = item.data(0, qt_core.Qt.UserRole)
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
        node = current.data(0, qt_core.Qt.UserRole)
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
        node_order = tuple(row["node"] for row in rows)

        # Rebuilding constructs a QComboBox + QSpinBox per row, and this runs on every
        # SelectionChanged (debounced). Only rebuild when the SET of LOD nodes actually
        # moved (a LOD created/deleted/retyped-into-a-new-sort-slot); otherwise update the
        # existing editors in place with signals blocked, so plain selection traffic never
        # pays for new widgets — see dock_refresh_cost.py.
        if node_order != self._lod_row_order:
            self._rebuild_lod_tree(rows, node_order, active, prev)
        else:
            self._update_lod_tree_rows(rows)
            self._restore_lod_tree_selection(active, prev)

        if self.lod_list_context is not None:
            if not rows:
                self.lod_list_context.setText("No DayZ LODs in the scene yet.")
            elif active:
                self.lod_list_context.setText("Active: {0}".format(_lod_name_from_transform(active)))
            else:
                self.lod_list_context.setText("{0} LODs — click one to select it.".format(len(rows)))


    def _build_row_editors(self, node):
        combo = qt_widgets.QComboBox()
        for definition in LOD_DEFINITIONS:
            icon = _qt_icon(lod_type_icon(definition["type"]))
            if icon is not None and not icon.isNull():
                combo.addItem(icon, definition["label"], definition["type"])
            else:
                combo.addItem(definition["label"], definition["type"])
        spin = qt_widgets.QSpinBox()
        spin.setMinimum(0)
        spin.setMaximum(1000000)
        # The editor writes to the node of ITS OWN ROW, captured here — never to
        # _selected_lod_transform(). The old panel edited the selection, which is wrong the
        # moment the row being edited is not the row selected.
        combo.currentIndexChanged.connect(
            lambda _index, n=node, c=combo: self._on_row_type_changed(n, c))
        spin.valueChanged.connect(
            lambda value, n=node: self._on_row_resolution_changed(n, value))
        return combo, spin


    def _apply_row_values(self, item, combo, spin, row):
        definition = _lod_definition_for_type(row["type"])
        item.setText(0, row["label"])
        icon = _qt_icon(lod_type_icon(row["type"]))
        if icon is not None and not icon.isNull():
            item.setIcon(0, icon)
        item.setToolTip(0, row["node"])

        combo.blockSignals(True)
        index = combo.findData(row["type"])
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

        # has_resolution == False means the type carries a fixed resolution; show it, do
        # not let it be edited. Disabled, not hidden: the value is still information.
        spin.blockSignals(True)
        spin.setValue(row["resolution"])
        spin.setEnabled(bool(definition["has_resolution"]))
        spin.blockSignals(False)

        stats = "{0} tris".format(row["tris"])
        if row["selections"]:
            stats += "  ·  {0} sel".format(row["selections"])
        item.setText(3, stats)


    def _rebuild_lod_tree(self, rows, node_order, active, prev):
        self._syncing_lod_list = True
        self.lod_list.blockSignals(True)
        self.lod_list.clear()
        self._lod_row_editors = {}
        target = _lod_list_target(active, prev)
        restore_item = None
        for row in rows:
            item = qt_widgets.QTreeWidgetItem()
            item.setData(0, qt_core.Qt.UserRole, row["node"])
            self.lod_list.addTopLevelItem(item)
            combo, spin = self._build_row_editors(row["node"])
            self.lod_list.setItemWidget(item, 1, combo)
            self.lod_list.setItemWidget(item, 2, spin)
            self._lod_row_editors[row["node"]] = {"item": item, "combo": combo, "spin": spin}
            self._apply_row_values(item, combo, spin, row)
            if target is not None and row["node"] == target:
                restore_item = item
        self._lod_row_order = node_order
        if restore_item is not None:
            self.lod_list.setCurrentItem(restore_item)
        self.lod_list.blockSignals(False)
        self._syncing_lod_list = False


    def _update_lod_tree_rows(self, rows):
        self._syncing_lod_list = True
        for row in rows:
            entry = self._lod_row_editors.get(row["node"])
            if entry is None:
                continue
            self._apply_row_values(entry["item"], entry["combo"], entry["spin"], row)
        self._syncing_lod_list = False


    def _restore_lod_tree_selection(self, active, prev):
        target = _lod_list_target(active, prev)
        if target is None:
            return
        entry = self._lod_row_editors.get(target)
        if entry is None:
            return
        self.lod_list.blockSignals(True)
        self._syncing_lod_list = True
        self.lod_list.setCurrentItem(entry["item"])
        self.lod_list.blockSignals(False)
        self._syncing_lod_list = False


    def _on_row_type_changed(self, node, combo):
        if not cmds.objExists(node):
            return
        lod_type = combo.itemData(combo.currentIndex())
        definition = _lod_definition_for_type(lod_type)
        entry = self._lod_row_editors.get(node)
        spin = entry["spin"] if entry else None
        if spin is not None:
            spin.blockSignals(True)
            spin.setEnabled(bool(definition["has_resolution"]))
            if not definition["has_resolution"]:
                spin.setValue(definition["default_resolution"])
            spin.blockSignals(False)
        resolution = spin.value() if spin is not None else definition["default_resolution"]
        self._write_row_lod(node, definition, resolution, entry)


    def _on_row_resolution_changed(self, node, value):
        if not cmds.objExists(node):
            return
        entry = self._lod_row_editors.get(node)
        combo = entry["combo"] if entry else None
        lod_type = combo.itemData(combo.currentIndex()) if combo is not None else LOD_DEFINITIONS[0]["type"]
        definition = _lod_definition_for_type(lod_type)
        self._write_row_lod(node, definition, value, entry)


    def _write_row_lod(self, node, definition, resolution, entry):
        load_plugin()
        with _undo_chunk("Set LOD"):
            # Both type and resolution edits write through cmds.a3obCreateLOD the way
            # _mark_selection_as_lod does — but _mark_node_as_lod passes the node
            # EXPLICITLY rather than relying on the current selection, so the node's own
            # name is left alone regardless of what else is selected.
            _mark_node_as_lod(node, definition, resolution)
        if entry is not None and cmds.objExists(node):
            item = entry["item"]
            item.setText(0, _lod_name_from_transform(node))
            icon = _qt_icon(lod_type_icon(definition["type"]))
            if icon is not None and not icon.isNull():
                item.setIcon(0, icon)
        # Signals are blocked while _apply_row_values drives the editors from scene state
        # (rebuild/update-in-place), so this method is only ever reached from a genuine
        # user edit — safe to always resync the rest of the dock (LOD Properties etc.).
        _refresh_context_ui()


    def lod_row_nodes(self):
        """Every row's node, in display order. Read-only; used by tests and by the
        detail area to find the row a node belongs to."""
        if getattr(self, "lod_list", None) is None:
            return []
        return [self.lod_list.topLevelItem(i).data(0, qt_core.Qt.UserRole)
                for i in range(self.lod_list.topLevelItemCount())]


    def _resolve_lod_row_node(self, node):
        """Normalize ``node`` to the full DAG path rows are keyed by.

        ``lod_overview()`` (via ``_lod_transforms()``) keys every row by its long path, but
        a caller may only have the short name on hand (``cmds.polyCube`` hands one back) —
        without this, ``set_row_type``/``set_row_resolution`` would silently find no row
        and write nothing."""
        if not node or not cmds.objExists(node):
            return node
        long_names = cmds.ls(node, long=True) or [node]
        return long_names[0]


    def set_row_type(self, node, lod_type):
        """Set a row's LOD type as if its combo had been changed."""
        node = self._resolve_lod_row_node(node)
        entry = self._lod_row_editors.get(node)
        if entry is None:
            return
        combo = entry["combo"]
        index = combo.findData(lod_type)
        if index < 0:
            return
        if combo.currentIndex() == index:
            # Same index would not fire currentIndexChanged; drive the write directly so
            # this still goes through the real write path.
            self._on_row_type_changed(node, combo)
        else:
            combo.setCurrentIndex(index)


    def set_row_resolution(self, node, resolution):
        """Set a row's resolution as if its spin box had been changed."""
        node = self._resolve_lod_row_node(node)
        entry = self._lod_row_editors.get(node)
        if entry is None:
            return
        spin = entry["spin"]
        if spin.value() == resolution:
            self._on_row_resolution_changed(node, resolution)
        else:
            spin.setValue(resolution)


__all__ = ["LodListPanelMixin"]
