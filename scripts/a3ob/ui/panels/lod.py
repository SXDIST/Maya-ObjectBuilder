"""lod panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class LodPanelMixin:
    def _build_lod_properties_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        self.lod_toggle = qt_widgets.QCheckBox("DayZ LOD")
        self.lod_toggle.setToolTip("Mark/unmark the selected mesh as a DayZ LOD")
        self.lod_toggle.toggled.connect(self._on_lod_toggle_changed)
        layout.addWidget(self.lod_toggle)

        self.lod_context = qt_widgets.QLabel()
        self.lod_context.setWordWrap(True)
        layout.addWidget(self.lod_context)

        form = qt_widgets.QFormLayout()
        self.lod_type_combo = qt_widgets.QComboBox()
        for definition in LOD_DEFINITIONS:
            icon = _qt_icon(lod_type_icon(definition["type"]))
            if icon is not None and not icon.isNull():
                self.lod_type_combo.addItem(icon, definition["label"], definition["type"])
            else:
                self.lod_type_combo.addItem(definition["label"], definition["type"])
        self.lod_type_combo.currentIndexChanged.connect(self._on_lod_controls_changed)
        form.addRow("LOD type", self.lod_type_combo)

        self.lod_resolution = qt_widgets.QSpinBox()
        self.lod_resolution.setMinimum(0)
        self.lod_resolution.setMaximum(1000000)
        self.lod_resolution.setValue(1)
        self.lod_resolution.valueChanged.connect(self._on_lod_controls_changed)
        form.addRow("Resolution", self.lod_resolution)
        layout.addLayout(form)
        return widget


    def _build_auto_lod_section(self):
        widget = qt_widgets.QWidget()
        auto_layout = qt_widgets.QFormLayout(widget)
        auto_layout.setContentsMargins(0, 0, 0, 0)
        self.auto_lod_output = qt_widgets.QComboBox()
        self.auto_lod_output.addItems(["Quads", "Triangles"])
        self.auto_lod_output.setToolTip("Quads keep quad-dominant LODs; Triangles fully triangulate.")
        self.auto_lod_reduction = qt_widgets.QComboBox()
        self.auto_lod_reduction.addItems(["Aggressive", "Balanced", "Light"])
        self.auto_lod_reduction.setToolTip("Per-step strength: Aggressive halves each LOD, Light barely reduces.")
        self.auto_lod_first = qt_widgets.QComboBox()
        self.auto_lod_first.addItems(["LOD1", "LOD0"])
        self.auto_lod_resolution = qt_widgets.QCheckBox("Resolution LODs")
        self.auto_lod_resolution.setChecked(True)
        self.auto_lod_geometry = qt_widgets.QCheckBox("Geometry LOD")
        self.auto_lod_geometry.setChecked(True)
        self.auto_lod_memory = qt_widgets.QCheckBox("Memory LOD")
        self.auto_lod_fire = qt_widgets.QCheckBox("Fire Geometry LOD")
        self.auto_lod_view = qt_widgets.QCheckBox("View Geometry LOD")
        self.auto_lod_geometry_type = qt_widgets.QComboBox()
        self.auto_lod_geometry_type.addItems(["BOX", "NONE"])
        self.auto_lod_fire_quality = qt_widgets.QSpinBox()
        self.auto_lod_fire_quality.setRange(1, 10)
        self.auto_lod_fire_quality.setValue(2)
        auto_layout.addRow("Output", self.auto_lod_output)
        auto_layout.addRow("Reduction", self.auto_lod_reduction)
        auto_layout.addRow("First LOD", self.auto_lod_first)
        auto_layout.addRow(self.auto_lod_resolution)
        auto_layout.addRow(self.auto_lod_geometry)
        auto_layout.addRow(self.auto_lod_memory)
        auto_layout.addRow(self.auto_lod_fire)
        auto_layout.addRow(self.auto_lod_view)
        auto_layout.addRow("Geometry", self.auto_lod_geometry_type)
        auto_layout.addRow("Fire quality", self.auto_lod_fire_quality)
        auto_layout.addRow(_qt_button("Generate Auto LOD", generate_auto_lods_from_ui, "Generate DayZ LODs from the selected mesh.", ":/polyReduce.png"))
        return widget


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


    def selected_lod_definition(self):
        index = self.lod_type_combo.currentIndex() if self.lod_type_combo is not None else 0
        lod_type = self.lod_type_combo.itemData(index) if self.lod_type_combo is not None else LOD_DEFINITIONS[0]["type"]
        for definition in LOD_DEFINITIONS:
            if definition["type"] == lod_type:
                return definition
        return LOD_DEFINITIONS[0]


    def auto_lod_settings(self):
        return {
            "output": (self.auto_lod_output.currentText() if self.auto_lod_output is not None else "Quads").lower(),
            "reduction": (self.auto_lod_reduction.currentText() if self.auto_lod_reduction is not None else "Aggressive").lower(),
            "first_lod": self.auto_lod_first.currentText() if self.auto_lod_first is not None else "LOD1",
            "resolution": self.auto_lod_resolution.isChecked() if self.auto_lod_resolution is not None else True,
            "geometry": self.auto_lod_geometry.isChecked() if self.auto_lod_geometry is not None else True,
            "memory": self.auto_lod_memory.isChecked() if self.auto_lod_memory is not None else False,
            "fire_geometry": self.auto_lod_fire.isChecked() if self.auto_lod_fire is not None else False,
            "view_geometry": self.auto_lod_view.isChecked() if self.auto_lod_view is not None else False,
            "geometry_type": self.auto_lod_geometry_type.currentText() if self.auto_lod_geometry_type is not None else "BOX",
            "fire_quality": self.auto_lod_fire_quality.value() if self.auto_lod_fire_quality is not None else 2,
        }


    def lod_resolution_value(self):
        return self.lod_resolution.value() if self.lod_resolution is not None else 1


    def _on_lod_controls_changed(self, *_):
        definition = self.selected_lod_definition()
        selected_lod = _selected_lod_transform()
        is_lod = bool(selected_lod)
        if self.lod_type_combo is not None:
            self.lod_type_combo.setEnabled(is_lod)
        if self.lod_resolution is not None:
            enabled = is_lod and definition["has_resolution"]
            self.lod_resolution.setEnabled(enabled)
            if not definition["has_resolution"]:
                self.lod_resolution.blockSignals(True)
                self.lod_resolution.setValue(definition["default_resolution"])
                self.lod_resolution.blockSignals(False)
        target = selected_lod or "No LOD selected."
        if self.lod_context is not None:
            self.lod_context.setText(f"Target: {target}")
        if not self._syncing_from_selection and is_lod:
            load_plugin()
            resolution = _lod_resolution_value(definition)
            # Re-stamp the active LOD's type/resolution as the user edits the combos. The
            # node's NAME is deliberately left alone — see _mark_selection_as_lod.
            _mark_selection_as_lod(definition, resolution)


    def _on_lod_toggle_changed(self, checked):
        if checked:
            assign_lod_to_selection()
        else:
            _remove_lod_from_selection()


    def _update_memory_points_visibility(self):
        if self.memory_points_group is None:
            return
        selected_lod = _selected_lod_transform()
        if selected_lod:
            lod_type = _safe_get_attr(selected_lod, "a3obLodType", -1)
            self.memory_points_group.setVisible(lod_type == MEMORY_LOD_TYPE)
        else:
            self.memory_points_group.setVisible(False)


    def refresh_lod_assignment(self, *_):
        selected_lod = _selected_lod_transform()
        if self.lod_toggle is not None:
            self.lod_toggle.blockSignals(True)
            self.lod_toggle.setChecked(bool(selected_lod))
            self.lod_toggle.setEnabled(bool(selected_lod or cmds.ls(selection=True)))
            self.lod_toggle.blockSignals(False)
        self._syncing_from_selection = True
        try:
            if selected_lod and self.lod_type_combo is not None:
                lod_type = _safe_get_attr(selected_lod, "a3obLodType", 0)
                resolution = _safe_get_attr(selected_lod, "a3obResolution", 0)
                for i in range(self.lod_type_combo.count()):
                    if self.lod_type_combo.itemData(i) == lod_type:
                        self.lod_type_combo.blockSignals(True)
                        self.lod_type_combo.setCurrentIndex(i)
                        self.lod_type_combo.blockSignals(False)
                        break
                if self.lod_resolution is not None:
                    self.lod_resolution.blockSignals(True)
                    self.lod_resolution.setValue(resolution)
                    self.lod_resolution.blockSignals(False)
            self._on_lod_controls_changed()
            self._update_memory_points_visibility()
            self.refresh_named_properties()
        finally:
            self._syncing_from_selection = False


__all__ = ["MayaObjectBuilderDock"]

