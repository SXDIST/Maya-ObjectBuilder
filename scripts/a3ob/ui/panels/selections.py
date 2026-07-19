"""selections panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
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

        first_row = qt_widgets.QHBoxLayout()
        for label, callback, tip, icon in (
            ("Select", _select_set_members, "Select the live members of the highlighted set", ":/aselect.png"),
            ("Rename", _rename_selection_set, "Rename the highlighted Object Builder selection", ":/quickRename.png"),
            ("Create", _create_selection_set, "Create a new selection set from the current component selection", ":/create.png"),
            ("Find", find_components_from_ui, "Find closed mesh components and create Component## selection sets", ":/search.png"),
        ):
            first_row.addWidget(_qt_button(label, callback, tip, icon))
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

