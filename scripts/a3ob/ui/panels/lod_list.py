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


# Sentinel for _mass_collapse_node: distinct from any real node path (including None),
# so the very first sync after dock construction always recomputes the collapse state.
_MASS_COLLAPSE_UNSET = object()


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
        row.addWidget(_qt_button("Mark Selection as LOD", self._mark_selection_as_lod_clicked,
                                  "Mark the current Maya selection as a DayZ LOD (Resolution type). "
                                  "Right-click a row for Unmark.", ":/confirm.png"))
        row.addWidget(_qt_button("Frame", self._frame_selected_lod, "Select and frame the LOD in the viewport.", ":/eye.png"))
        row.addWidget(_qt_button("Isolate", self._toggle_isolate_lod, "Toggle viewport isolation of the selected LOD (non-destructive).", ":/ghostOff.png"))
        layout.addLayout(row)

        # Named properties are per-LOD data (a3obProperties, exported as that LOD's TAGGs),
        # so the detail area lives directly under the tree it describes rather than in a
        # panel of its own — see selected_named_property_lod() for how it follows the row.
        layout.addWidget(self._build_named_properties_detail())

        # Mass (a3obMassValues) is likewise per-LOD data, exported to a mass TAGG
        # wherever it exists — see _build_mass_detail() for why it is never hidden.
        layout.addWidget(self._build_mass_detail())

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
        menu.addAction("Unmark").triggered.connect(lambda *_: self._unmark_lod(node))
        menu.addSeparator()
        menu.addAction("Delete").triggered.connect(lambda *_: self._delete_lod(node))
        menu.popup(self.lod_list.viewport().mapToGlobal(pos))


    def _mark_selection_as_lod_clicked(self):
        """Button in the LOD list's row — replaces the old LOD Properties 'DayZ LOD'
        checkbox. assign_lod_to_selection() keeps acting on the Maya selection, not on
        this dock instance, so refresh this instance explicitly afterwards too (mirrors
        _rename_lod/_duplicate_lod/_delete_lod below, which do the same for their edits)."""
        assign_lod_to_selection()
        self.refresh_lod_list()


    def _unmark_lod(self, node):
        """Row context-menu 'Unmark' — replaces the old checkbox's unchecked state.

        _remove_lod_from_selection() acts on the Maya selection, so select the row's own
        node first; this mirrors _mark_node_as_lod's save/select/restore pattern except a
        removal has nothing useful to restore selection to afterward."""
        if not node or not cmds.objExists(node):
            return
        cmds.select(node, replace=True)
        _remove_lod_from_selection()
        self.refresh_lod_list()


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

        # The detail area follows the row the tree ends up highlighting above, whichever
        # of the rebuild/update-in-place paths just ran.
        self.refresh_named_properties()
        self.refresh_mass_summary()
        self._sync_mass_collapse_state()
        # Memory Points visibility used to be refreshed by the LOD Properties panel's own
        # refresh_lod_assignment() (retired with that panel); it follows the selected LOD
        # too, so it belongs in the same SelectionChanged-driven pass.
        self._update_memory_points_visibility()


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


    # ---- named properties detail area (moved from panels/named_properties.py) ------

    def _build_named_properties_detail(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Named properties on the selected LOD, exported to P3D TAGGs."))

        self.named_list = qt_widgets.QListWidget()
        self.named_list.currentItemChanged.connect(lambda *_: self.select_named_property())
        layout.addWidget(self.named_list, 1)

        edit_form = qt_widgets.QFormLayout()
        self.named_name_combo = qt_widgets.QComboBox()
        self.named_name_combo.setEditable(True)
        self.named_name_combo.addItems(sorted(KNOWN_NAMED_PROPS.keys()))
        self.named_name_combo.currentTextChanged.connect(self._update_named_value_combo)
        self.named_value_combo = qt_widgets.QComboBox()
        self.named_value_combo.setEditable(True)
        edit_form.addRow("Name", self.named_name_combo)
        edit_form.addRow("Value", self.named_value_combo)
        layout.addLayout(edit_form)

        self.named_batch_check = qt_widgets.QCheckBox("Apply to all selected LODs")
        self.named_batch_check.setToolTip("Add/Update writes the property to every selected LOD, not just the active one.")
        layout.addWidget(self.named_batch_check)

        named_buttons = qt_widgets.QHBoxLayout()
        named_buttons.addWidget(_qt_button("Add / Update", self._commit_named_property_from_fields, "Save the current name/value pair on the active LOD.", ":/confirm.png"))
        named_buttons.addWidget(_qt_button("Remove", _remove_named_property, "Remove the selected property from the active LOD.", ":/delete.png"))
        layout.addLayout(named_buttons)

        return widget


    def named_batch_enabled(self):
        return self.named_batch_check.isChecked() if getattr(self, "named_batch_check", None) is not None else False


    def selected_named_property_lod(self):
        """The LOD the detail area is currently showing.

        The tree's own current row wins — the detail area follows what the user is
        looking at in the list — and only falls back to the scene selection when no row
        is current (e.g. right after the dock is built, before anything is picked)."""
        node = self._selected_lod_list_node()
        if node:
            return node
        try:
            sel = cmds.ls(selection=True, long=True, transforms=True)
            return sel[0] if sel else None
        except RuntimeError:
            return None


    def named_property_name(self):
        return self.named_name_combo.currentText().strip() if self.named_name_combo is not None else ""


    def named_property_value(self):
        return self.named_value_combo.currentText().strip() if self.named_value_combo is not None else ""


    def set_named_property_fields(self, name, value):
        if self.named_name_combo is not None:
            self.named_name_combo.blockSignals(True)
            self.named_name_combo.setCurrentText(name)
            self.named_name_combo.blockSignals(False)
        if self.named_value_combo is not None:
            self.named_value_combo.blockSignals(True)
            self.named_value_combo.setCurrentText(value)
            self.named_value_combo.blockSignals(False)


    def clear_named_property_fields(self):
        self.set_named_property_fields("", "")


    def _update_named_value_combo(self):
        if self.named_name_combo is None or self.named_value_combo is None:
            return
        name = self.named_name_combo.currentText().strip()
        self.named_value_combo.blockSignals(True)
        self.named_value_combo.clear()
        values = KNOWN_NAMED_PROPS.get(name, [])
        if values:
            self.named_value_combo.addItems(values)
        self.named_value_combo.blockSignals(False)
        description = NAMED_PROP_DESCRIPTIONS.get(name.lower(), "")
        self.named_name_combo.setToolTip(description or "DayZ named property stored on the active LOD.")


    def refresh_named_properties(self):
        if self.named_list is None:
            return
        self.named_list.clear()
        self.named_items = {}
        lod = self.selected_named_property_lod()
        if not lod:
            self.clear_named_property_fields()
            return
        raw = _safe_get_attr(lod, "a3obProperties", "") or ""
        for name, value in _split_named_properties(raw):
            label = f"{name} = {value}"
            self.named_items[label] = (name, value)
            self.named_list.addItem(label)


    def select_named_property(self):
        current = self.named_list.currentItem() if self.named_list is not None else None
        if current is None:
            return
        name, value = self.named_items.get(current.text(), ("", ""))
        self.set_named_property_fields(name, value)


    def _commit_named_property_from_fields(self, *_args):
        self.apply_named_property(self.named_property_name(), self.named_property_value())


    def apply_named_property(self, name, value):
        """Programmatic path for writing a name/value pair — the Add/Update button and
        tests both call this, so a passing test proves what the button actually does."""
        batch = self.named_batch_enabled()
        return _set_named_property_value(name, value, batch=batch)


    # ---- mass detail area (moved from panels/metadata.py) -----------------------------

    def _build_mass_detail(self):
        """Per-vertex mass on the selected LOD (a3obMassValues), exported to a P3D mass
        TAGG wherever it exists — export does NOT restrict it by LOD type. The section is
        therefore always present; only its starting expanded/collapsed state depends on
        the row's type (see _sync_mass_collapse_state) — never its existence or whether
        Apply/Clear/etc. actually work."""
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        header = qt_widgets.QHBoxLayout()
        self.mass_toggle_button = qt_widgets.QPushButton("Mass")
        self.mass_toggle_button.setFlat(True)
        self.mass_toggle_button.setCheckable(True)
        self.mass_toggle_button.setCursor(qt_core.Qt.PointingHandCursor)
        self.mass_toggle_button.setToolTip("Per-vertex mass on the selected LOD, exported to P3D.")
        button_font = self.mass_toggle_button.font()
        button_font.setBold(True)
        self.mass_toggle_button.setFont(button_font)
        self.mass_toggle_button.toggled.connect(self._on_mass_toggle)
        header.addWidget(self.mass_toggle_button)
        layout.addLayout(header)

        self.mass_body = qt_widgets.QWidget()
        mass_layout = qt_widgets.QFormLayout(self.mass_body)
        mass_layout.setContentsMargins(12, 0, 0, 0)
        self.mass_value_field = qt_widgets.QDoubleSpinBox()
        self.mass_value_field.setDecimals(3)
        self.mass_value_field.setValue(1.0)
        self.mass_value_field.setRange(-1000000.0, 1000000.0)
        self.mass_mode_combo = qt_widgets.QComboBox()
        self.mass_mode_combo.addItems(["All vertices", "Selected vertices"])
        self.mass_total_label = qt_widgets.QLabel("Total: —")
        mass_layout.addRow("Value", self.mass_value_field)
        mass_layout.addRow("Mode", self.mass_mode_combo)
        mass_layout.addRow("Current", self.mass_total_label)
        mass_buttons = qt_widgets.QHBoxLayout()
        mass_buttons.addWidget(_qt_button("Apply", apply_mass_from_ui, "Set the mass value on the LOD's vertices.", ":/confirm.png"))
        mass_buttons.addWidget(_qt_button("Clear", clear_mass_from_ui, "Remove all mass data from the LOD.", ":/delete.png"))
        mass_layout.addRow(mass_buttons)

        self.mass_density_field = qt_widgets.QDoubleSpinBox()
        self.mass_density_field.setDecimals(1)
        self.mass_density_field.setRange(0.1, 1000000.0)
        self.mass_density_field.setValue(1000.0)
        self.mass_density_field.setToolTip("Density (kg/m3) for 'From volume' — water ~ 1000, wood ~ 700, steel ~ 7850.")
        mass_layout.addRow("Density", self.mass_density_field)
        mass_tools = qt_widgets.QHBoxLayout()
        mass_tools.addWidget(_qt_button("Distribute evenly", distribute_mass_evenly, "Spread the current total mass evenly across all vertices.", ":/confirm.png"))
        mass_tools.addWidget(_qt_button("From volume", mass_from_volume_from_ui, "Set total mass = bounding-box volume x density, spread evenly.", ":/polyCube.png"))
        mass_layout.addRow(mass_tools)
        layout.addWidget(self.mass_body)

        self._set_mass_collapsed(True)
        self.refresh_mass_summary()
        return widget


    def _on_mass_toggle(self, checked):
        """User clicked the Mass header — a manual override of the collapse-by-relevance
        default, good for the session but not persisted (the next refresh recomputes it
        from the row's LOD type, same as the row editors themselves do)."""
        self._mass_collapsed = not checked
        if self.mass_body is not None:
            self.mass_body.setVisible(checked)
        self.mass_toggle_button.setText("Mass ▾" if checked else "Mass ▸")


    def _set_mass_collapsed(self, collapsed):
        collapsed = bool(collapsed)
        self._mass_collapsed = collapsed
        if getattr(self, "mass_body", None) is not None:
            self.mass_body.setVisible(not collapsed)
        if getattr(self, "mass_toggle_button", None) is not None:
            self.mass_toggle_button.blockSignals(True)
            self.mass_toggle_button.setChecked(not collapsed)
            self.mass_toggle_button.setText("Mass ▸" if collapsed else "Mass ▾")
            self.mass_toggle_button.blockSignals(False)


    def _sync_mass_collapse_state(self):
        """Collapse the Mass group when the selected row's LOD type makes mass unusual.

        Collapsed, never hidden and never disabled: export writes a mass TAGG wherever
        a3obMassValues exists, with no restriction by a3obLodType, so the UI must not be
        narrower than the format — this only decides prominence, never availability.

        Recomputed only when the SELECTED NODE changes, not on every refresh_lod_list()
        call — mirroring the _lod_row_order-vs-node_order rebuild-only-on-change pattern
        above. Two of the Mass section's own buttons (distribute_mass_evenly,
        mass_from_volume_from_ui) end with _refresh_context_ui(), which runs this on the
        same node the user just edited; recomputing unconditionally there re-collapsed a
        section the user had just expanded by hand, before they could even see the
        result. A manual toggle during a visit to one LOD now sticks until the selection
        actually moves to a different node — switching away and back still re-applies
        the type-based default, so this is not a sticky-forever override."""
        if getattr(self, "mass_body", None) is None:
            return
        node = self.selected_named_property_lod()
        if node == getattr(self, "_mass_collapse_node", _MASS_COLLAPSE_UNSET):
            return
        self._mass_collapse_node = node
        lod_type = None
        if node and cmds.objExists(node) and cmds.attributeQuery("a3obLodType", node=node, exists=True):
            lod_type = cmds.getAttr(node + ".a3obLodType")
        self._set_mass_collapsed(lod_type not in GEOMETRY_FAMILY_LOD_TYPES)


    def refresh_mass_summary(self):
        """The running total/vertex-count line under the mass controls. Follows the
        detail area's row (selected_named_property_lod), not the raw scene selection —
        matching what selected_named_property_lod already does for named properties."""
        if getattr(self, "mass_total_label", None) is None:
            return
        node = self.selected_named_property_lod()
        raw = _safe_get_attr(node, "a3obMassValues", "") if node else ""
        values = []
        for token in (raw or "").split(";"):
            token = token.strip()
            if not token:
                continue
            try:
                values.append(float(token))
            except ValueError:
                pass
        if node is None:
            self.mass_total_label.setText("Total: — (no LOD)")
        elif not values:
            self.mass_total_label.setText("Total: — (no mass set)")
        else:
            self.mass_total_label.setText("Total: {0:.3f}  ({1} verts)".format(sum(values), len(values)))


    def mass_value(self):
        return self.mass_value_field.value() if self.mass_value_field is not None else 1.0


    def mass_mode(self):
        return self.mass_mode_combo.currentText() if self.mass_mode_combo is not None else "All vertices"


    def mass_section_is_present(self):
        """Mass must be present for EVERY LOD type — collapsed only changes prominence,
        never availability. True once the detail area has built the group at all."""
        return getattr(self, "mass_body", None) is not None


    def mass_section_is_collapsed(self):
        return bool(getattr(self, "_mass_collapsed", True))


    def apply_mass(self, value):
        """Programmatic path for setting + applying mass on THIS dock instance.

        Mirrors apply_mass_from_ui() but writes through self directly rather than
        through _active_qt_dock() — the free function only finds the one dock that
        was built via _build_qt_dock()/open_dock(), which a test-constructed dock
        never registers as. Both paths end at the same a3obSetMass command."""
        if getattr(self, "mass_value_field", None) is not None:
            self.mass_value_field.setValue(value)
        load_plugin()
        with _undo_chunk("Set Mass"):
            cmds.a3obSetMass(value=value, selectedComponents=(self.mass_mode() == "Selected vertices"))


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
