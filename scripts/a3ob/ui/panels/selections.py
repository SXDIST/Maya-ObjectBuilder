"""selections panel of the MayaObjectBuilder dock."""

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class SelectionsPanelMixin:
    def _build_selections_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        # Context line: which LOD's selections are shown (or a prompt when none is active).
        self.selection_mesh_context = _hint("Select a DayZ LOD to see its selections.")
        layout.addWidget(self.selection_mesh_context)

        self.selection_list = qt_widgets.QListWidget()
        self.selection_list.currentItemChanged.connect(lambda *_: _update_selection_details())
        self.selection_list.itemDoubleClicked.connect(lambda *_: _select_set_members())
        layout.addWidget(self.selection_list, 1)

        self.selection_details = qt_widgets.QLabel("Select a row to see details.")
        self.selection_details.setWordWrap(True)
        layout.addWidget(self.selection_details)

        # Page 0 is empty: an ordinary Selection row has nothing to edit, and the summary
        # label above already says everything about it. Pages 1 and 2 are the flag and proxy
        # editors — the capability the retired create-only panels never had.
        self.selection_editor_stack = qt_widgets.QStackedWidget()
        self.selection_editor_stack.addWidget(qt_widgets.QWidget())
        self.selection_editor_stack.addWidget(self._build_flag_editor_page())
        layout.addWidget(self.selection_editor_stack)

        first_row = qt_widgets.QHBoxLayout()
        for label, callback, tip, icon in (
            ("Select", _select_set_members, "Select the live members of the highlighted set", ":/aselect.png"),
            ("Rename", _rename_selection_set, "Rename the highlighted Object Builder selection", ":/quickRename.png"),
        ):
            first_row.addWidget(_qt_button(label, callback, tip, icon))

        create_button = qt_widgets.QToolButton()
        create_button.setText("Create")
        create_button.setToolTip("Create a selection, proxy or flag set")
        create_icon = _qt_icon(":/create.png")
        if create_icon is not None and not create_icon.isNull():
            create_button.setIcon(create_icon)
        create_button.setPopupMode(qt_widgets.QToolButton.InstantPopup)
        create_menu = qt_widgets.QMenu(create_button)
        create_menu.addAction("Selection from components", _create_selection_set)
        create_menu.addAction("Proxy...", create_proxy_from_ui)
        create_menu.addAction("Flag...", apply_flag_from_ui)
        create_button.setMenu(create_menu)
        # Not a lifetime crutch: QMenu(create_button) already parents the menu to the button,
        # so Qt owns it and it survives this method either way. The handle is kept for the
        # same reason the dock keeps selection_list and selection_details — so the menu can be
        # reached later without digging through the widget tree.
        self.selection_create_menu = create_menu
        first_row.addWidget(create_button)

        first_row.addWidget(_qt_button("Find", find_components_from_ui,
                                       "Find closed mesh components and create Component## selection sets",
                                       ":/search.png"))
        layout.addLayout(first_row)

        second_row = qt_widgets.QHBoxLayout()
        for label, callback, tip, icon in (
            ("Add", _add_to_selection_set, "Add selected components to the highlighted set", ":/setEdit.png"),
            ("Remove", _remove_from_selection_set, "Remove selected components from the highlighted set", ":/removeRenderable.png"),
            ("Delete", _delete_selection_set, "Delete the highlighted Object Builder set", ":/delete.png"),
            ("Clear All", _clear_all_object_builder_sets, "Delete every Object Builder selection set in the scene", ":/clearAll.png"),
        ):
            second_row.addWidget(_qt_button(label, callback, tip, icon))
        layout.addLayout(second_row)

        self.refresh_selection_manager(True)
        return widget


    def _build_flag_editor_page(self):
        page = qt_widgets.QWidget()
        form = qt_widgets.QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        self.flag_edit_component_combo = qt_widgets.QComboBox()
        self.flag_edit_component_combo.addItems(["Face", "Vertex"])
        self.flag_edit_value_field = qt_widgets.QSpinBox()
        self.flag_edit_value_field.setRange(-2147483648, 2147483647)
        form.addRow("Component", self.flag_edit_component_combo)
        form.addRow("Value", self.flag_edit_value_field)
        form.addRow(_qt_button("Apply", apply_flag_edit_from_ui,
                               "Write the component type and value onto the highlighted flag set",
                               ":/confirm.png"))
        return page


    def flag_edit_values(self):
        if self.flag_edit_component_combo is None or self.flag_edit_value_field is None:
            return "face", 0
        return (self.flag_edit_component_combo.currentText().lower(),
                self.flag_edit_value_field.value())


    def show_selection_editor(self, fields):
        """Switch the details area to the page matching the highlighted row's kind.

        Values are loaded with signals blocked: the editors are plain inputs with no
        change handler today, but a future one must not fire on a programmatic load and
        write back the value the user is only looking at."""
        if self.selection_editor_stack is None:
            return
        kind = fields.get("kind", "")
        if kind in ("Vertex Flag", "Face Flag"):
            self.flag_edit_component_combo.blockSignals(True)
            self.flag_edit_value_field.blockSignals(True)
            index = 1 if fields.get("flag_component") == "vertex" else 0
            self.flag_edit_component_combo.setCurrentIndex(index)
            self.flag_edit_value_field.setValue(int(fields.get("flag_value", 0)))
            self.flag_edit_component_combo.blockSignals(False)
            self.flag_edit_value_field.blockSignals(False)
            self.selection_editor_stack.setCurrentIndex(1)
            return
        self.selection_editor_stack.setCurrentIndex(0)


    def selected_selection_set_node(self):
        current = self.selection_list.currentItem() if self.selection_list is not None else None
        if current is None:
            return None
        item = current.data(qt_core.Qt.UserRole)
        set_node = item["node"] if item else None
        return set_node if _node_exists(set_node) else None


    def set_selection_details(self, message):
        if self.selection_details is not None:
            self.selection_details.setText(message)


    def refresh_selection_manager(self, rebuild_lods=True):
        if self.selection_list is None:
            return
        # The owner is the selected LOD, or the plain mesh when it has not been marked as
        # one yet. Requiring a LOD meant a selection made while modelling — before anyone
        # thinks about LOD metadata — existed in the scene but showed up in no panel.
        owner = _selected_selection_owner()
        prev_node = self.selected_selection_set_node()
        self.selection_list.blockSignals(True)
        self.selection_list.clear()

        if not owner:
            self.selection_list.blockSignals(False)
            if self.selection_mesh_context is not None:
                self.selection_mesh_context.setText("Select a mesh or LOD to see its selections.")
            self.set_selection_details("Select a row to see details.")
            return

        if self.selection_mesh_context is not None:
            if _is_lod_transform(owner):
                where = _lod_name_from_transform(owner)
            else:
                where = "%s (not a LOD yet)" % owner.split("|")[-1]
            self.selection_mesh_context.setText(f"Selections on {where}")

        restore_row = -1
        for item in selection_sets_for_owner(owner):
            list_item = qt_widgets.QListWidgetItem(item["name"])
            icon = _qt_icon(_SELECTION_KIND_ICONS.get(item["kind"], ""))
            if icon is not None and not icon.isNull():
                list_item.setIcon(icon)
            list_item.setToolTip(f"{item['kind']}  ·  Maya set: {item['node']}")
            list_item.setData(qt_core.Qt.UserRole, item)
            self.selection_list.addItem(list_item)
            if prev_node is not None and item["node"] == prev_node:
                restore_row = self.selection_list.count() - 1
        self.selection_list.blockSignals(False)
        if restore_row >= 0:
            self.selection_list.setCurrentRow(restore_row)
        else:
            self.set_selection_details("Select a row to see details.")
        _update_selection_details()

