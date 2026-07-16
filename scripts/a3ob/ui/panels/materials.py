"""materials panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class MaterialsPanelMixin:
    def _build_materials_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        head = qt_widgets.QHBoxLayout()
        head.addWidget(_hint("Pick a material, set its texture / rvmat paths. Edits save instantly."), 1)
        refresh = _icon_button(":/refresh.png", "↻", "Re-scan the current selection's materials")
        refresh.clicked.connect(lambda: self.refresh_material_metadata())
        head.addWidget(refresh)
        layout.addLayout(head)

        self.material_list = qt_widgets.QListWidget()
        self.material_list.currentItemChanged.connect(lambda *_: self.select_material_metadata())
        layout.addWidget(self.material_list, 1)

        form = qt_widgets.QFormLayout()
        self.material_texture = self._path_picker("Texture", "Select texture path", 1, "Texture (*.paa)")
        self.material_rvmat = self._path_picker("Material", "Select material path", 1, "Material (*.rvmat)")
        form.addRow("Texture", self.material_texture)
        form.addRow("Material", self.material_rvmat)
        layout.addLayout(form)

        texture_field = _picker_field(self.material_texture)
        rvmat_field = _picker_field(self.material_rvmat)
        if texture_field is not None:
            texture_field.textChanged.connect(lambda *_: self._on_material_path_edited())
        if rvmat_field is not None:
            rvmat_field.textChanged.connect(lambda *_: self._on_material_path_edited())

        self.refresh_material_metadata()
        return widget


    def material_texture_path(self):
        field = _picker_field(self.material_texture)
        return _normalize_dayz_path(field.text()) if field is not None else ""


    def material_rvmat_path(self):
        field = _picker_field(self.material_rvmat)
        return _normalize_dayz_path(field.text()) if field is not None else ""


    def selected_material_metadata_item(self):
        current = self.material_list.currentItem() if self.material_list is not None else None
        if current is None:
            return None
        item = self.material_items.get(current.text())
        if not item:
            return None
        if not _node_exists(item["material_node"]) and not _valid_nodes(item["shading_groups"]):
            self.refresh_material_metadata()
            return None
        item["shading_groups"] = _valid_nodes(item["shading_groups"])
        return item


    def select_material_metadata(self):
        item = self.selected_material_metadata_item()
        if not item:
            return
        texture = _picker_field(self.material_texture)
        rvmat = _picker_field(self.material_rvmat)
        if texture is not None:
            texture.blockSignals(True)
            try:
                texture.setText(item["texture"])
            finally:
                texture.blockSignals(False)
        if rvmat is not None:
            rvmat.blockSignals(True)
            try:
                rvmat.setText(item["material"])
            finally:
                rvmat.blockSignals(False)


    def _on_material_path_edited(self):
        if self.material_list is None:
            return
        current = self.material_list.currentItem()
        if current is None:
            return
        item = _persist_selected_material_metadata()
        if item is None:
            return
        new_label = _material_metadata_label(item)
        old_label = current.text()
        if new_label == old_label:
            return
        current.setText(new_label)
        if hasattr(self, "material_items"):
            self.material_items.pop(old_label, None)
            self.material_items[new_label] = item


    def refresh_material_metadata(self):
        if self.material_list is None:
            return
        current = self.material_list.currentItem()
        prev_label = current.text() if current else None
        self.material_list.clear()
        self.material_items = {}
        items = _material_nodes_for_selection()
        if not items:
            self.material_list.addItem("Select a mesh, LOD, or faces to edit its DayZ materials")
            return
        for item in items:
            label = _material_metadata_label(item)
            self.material_items[label] = item
            self.material_list.addItem(qt_widgets.QListWidgetItem(label))
        if prev_label and qt_core is not None:
            matches = self.material_list.findItems(prev_label, qt_core.Qt.MatchExactly)
            if matches:
                self.material_list.setCurrentItem(matches[0])
                return
        if self.material_list.count() > 0:
            self.material_list.setCurrentRow(0)

