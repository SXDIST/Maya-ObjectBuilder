"""The MayaObjectBuilder dock widget (accordion-panel Qt UI)."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class MayaObjectBuilderDock(qt_widgets.QWidget if QT_AVAILABLE else object):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MayaObjectBuilderQtDock")
        self.lod_toggle = None
        self._syncing_from_selection = False
        self.lod_type_combo = None
        self.lod_resolution = None
        self.lod_context = None
        self.memory_points_group = None
        self.auto_lod_preset = None
        self.auto_lod_first = None
        self.auto_lod_resolution = None
        self.auto_lod_geometry = None
        self.auto_lod_memory = None
        self.auto_lod_fire = None
        self.auto_lod_view = None
        self.auto_lod_geometry_type = None
        self.auto_lod_fire_quality = None
        self.model_cfg_import = None
        self.model_cfg_export = None
        self.mass_value_field = None
        self.mass_mode_combo = None
        self.flag_component_combo = None
        self.flag_value_field = None
        self.flag_name_field = None
        self.proxy_path_field = None
        self.proxy_index_field = None
        self.proxy_from_selection_check = None
        self.named_list = None
        self.named_name_combo = None
        self.named_value_combo = None
        self.named_items = {}
        self.material_list = None
        self.material_texture = None
        self.material_rvmat = None
        self.material_items = {}
        self.selection_list = None
        self.selection_details = None
        self.selection_mesh_context = None
        self._build_ui()
        self.refresh_lod_assignment()

    def _build_ui(self):
        outer = qt_widgets.QVBoxLayout(self)
        outer.setContentsMargins(UI_MARGIN, UI_MARGIN, UI_MARGIN, UI_MARGIN)
        outer.setSpacing(UI_SPACING)
        outer.addWidget(self._build_quick_actions())

        body = qt_widgets.QWidget()
        body_layout = qt_widgets.QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        panels = [
            ("LOD Properties", self._build_lod_properties_section(), False),
            ("Auto LOD", self._build_auto_lod_section(), True),
            ("Mass & Flags", self._build_mass_flags_section(), True),
            ("Named Properties", self._build_named_properties_tab(), True),
            ("Materials", self._build_materials_tab(), True),
            ("Selections", self._build_selections_tab(), True),
            ("Proxies", self._build_proxies_section(), True),
            ("Memory Points", self._build_memory_points_section(), True),
            ("Skeleton (model.cfg)", self._build_skeleton_section(), True),
            ("Validation", self._build_validation_tab(), True),
        ]
        self.memory_points_group = None
        for title, widget, collapsed in panels:
            section = _CollapsibleSection(title, collapsed=collapsed)
            section.body_layout.addWidget(widget)
            body_layout.addWidget(section)
            if title == "Memory Points":
                self.memory_points_group = section
        body_layout.addStretch()

        scroll = qt_widgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(qt_widgets.QScrollArea.NoFrame)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    def _build_quick_actions(self):
        group = qt_widgets.QGroupBox("Quick Actions")
        layout = qt_widgets.QGridLayout(group)
        layout.setContentsMargins(UI_MARGIN, UI_MARGIN, UI_MARGIN, UI_MARGIN)
        layout.setSpacing(UI_SPACING)
        actions = [
            ("Import P3D", import_p3d, "Open a P3D through Maya's native Arma P3D importer.", ":/fileOpen.png"),
            ("Export P3D", export_p3d, "Export the current scene through Maya's native Arma P3D exporter.", ":/fileSave.png"),
            ("Auto LOD", generate_auto_lods_from_ui, "Generate DayZ LODs from the selected mesh using the Auto LOD settings.", ":/polyReduce.png"),
            ("Validate", _validate_scene_no_flush, "Validate all Object Builder LODs in the scene.", ":/confirm.png"),
        ]
        for index, (label, callback, tooltip, icon) in enumerate(actions):
            button = _qt_button(label, callback, tooltip, icon)
            button.setMinimumHeight(30)
            layout.addWidget(button, index // 2, index % 2)
        return group

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
        self.auto_lod_preset = qt_widgets.QComboBox()
        self.auto_lod_preset.addItems(["QUADS", "TRIS", "CUSTOM"])
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
        auto_layout.addRow("Preset", self.auto_lod_preset)
        auto_layout.addRow("First LOD", self.auto_lod_first)
        auto_layout.addRow(self.auto_lod_resolution)
        auto_layout.addRow(self.auto_lod_geometry)
        auto_layout.addRow(self.auto_lod_memory)
        auto_layout.addRow(self.auto_lod_fire)
        auto_layout.addRow(self.auto_lod_view)
        auto_layout.addRow("Geometry", self.auto_lod_geometry_type)
        auto_layout.addRow("Fire quality", self.auto_lod_fire_quality)
        auto_layout.addRow(_qt_button("Generate Auto LOD", generate_auto_lods_from_ui, "Generate DayZ LODs from the selected mesh."))
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
        mem_buttons.addWidget(_qt_button("Add Memory Point", add_memory_point, "Create a new named locator under the selected Memory LOD."))
        mem_buttons.addWidget(_qt_button("Add Point to Selection", add_point_to_selection, "Add another locator to the same named selection as the selected memory point."))
        layout.addLayout(mem_buttons)
        return widget

    def _build_skeleton_section(self):
        widget = qt_widgets.QWidget()
        cfg_layout = qt_widgets.QFormLayout(widget)
        cfg_layout.setContentsMargins(0, 0, 0, 0)
        self.model_cfg_import = self._path_picker("Import path", "Select model.cfg", 1, "Config (*.cfg)")
        self.model_cfg_export = self._path_picker("Export path", "Export model.cfg", 0, "Config (*.cfg)")
        cfg_layout.addRow("Import", self.model_cfg_import)
        cfg_layout.addRow("Export", self.model_cfg_export)
        cfg_buttons = qt_widgets.QHBoxLayout()
        cfg_buttons.addWidget(_qt_button("Import CFG", import_model_cfg_from_ui))
        cfg_buttons.addWidget(_qt_button("Export CFG", export_model_cfg_from_ui))
        cfg_layout.addRow(cfg_buttons)
        return widget

    def _path_picker(self, label, caption, mode, file_filter):
        container = qt_widgets.QWidget()
        layout = qt_widgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        field = qt_widgets.QLineEdit()
        browse = _icon_button(":/fileOpen.png", "...", caption)
        clear = _icon_button(":/deleteActive.png", "X", f"Clear {label}")
        browse.clicked.connect(lambda: self._browse_qt_path(field, caption, mode, file_filter))
        clear.clicked.connect(field.clear)
        layout.addWidget(field, 1)
        layout.addWidget(browse)
        layout.addWidget(clear)
        container._line_edit = field
        return container

    def _browse_qt_path(self, field, caption, mode, file_filter):
        selected = cmds.fileDialog2(fileMode=mode, caption=caption, fileFilter=file_filter)
        if selected:
            field.setText(_normalize_dayz_path(selected[0]))

    def _build_mass_flags_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        mass_group = qt_widgets.QGroupBox("Mass")
        mass_layout = qt_widgets.QFormLayout(mass_group)
        self.mass_value_field = qt_widgets.QDoubleSpinBox()
        self.mass_value_field.setDecimals(3)
        self.mass_value_field.setValue(1.0)
        self.mass_value_field.setRange(-1000000.0, 1000000.0)
        self.mass_mode_combo = qt_widgets.QComboBox()
        self.mass_mode_combo.addItems(["All vertices", "Selected vertices"])
        mass_layout.addRow("Value", self.mass_value_field)
        mass_layout.addRow("Mode", self.mass_mode_combo)
        mass_buttons = qt_widgets.QHBoxLayout()
        mass_buttons.addWidget(_qt_button("Apply", apply_mass_from_ui))
        mass_buttons.addWidget(_qt_button("Clear", clear_mass_from_ui))
        mass_layout.addRow(mass_buttons)
        layout.addWidget(mass_group)

        flags_group = qt_widgets.QGroupBox("Flags")
        flags_layout = qt_widgets.QFormLayout(flags_group)
        self.flag_component_combo = qt_widgets.QComboBox()
        self.flag_component_combo.addItems(["Face", "Vertex"])
        self.flag_value_field = qt_widgets.QSpinBox()
        self.flag_value_field.setRange(-2147483648, 2147483647)
        self.flag_value_field.setValue(1)
        self.flag_name_field = qt_widgets.QLineEdit("a3ob_flag")
        flags_layout.addRow("Component", self.flag_component_combo)
        flags_layout.addRow("Value", self.flag_value_field)
        flags_layout.addRow("Set name", self.flag_name_field)
        flags_layout.addRow(_qt_button("Apply Flag", apply_flag_from_ui))
        layout.addWidget(flags_group)
        return widget

    def _build_proxies_section(self):
        widget = qt_widgets.QWidget()
        proxy_layout = qt_widgets.QFormLayout(widget)
        proxy_layout.setContentsMargins(0, 0, 0, 0)
        self.proxy_path_field = self._path_picker("Proxy path", "Select proxy P3D", 1, "Arma P3D (*.p3d)")
        self.proxy_index_field = qt_widgets.QSpinBox()
        self.proxy_index_field.setRange(0, 2147483647)
        self.proxy_index_field.setValue(1)
        self.proxy_from_selection_check = qt_widgets.QCheckBox("Create from selected components")
        self.proxy_from_selection_check.setChecked(True)
        proxy_layout.addRow("Path", self.proxy_path_field)
        proxy_layout.addRow("Index", self.proxy_index_field)
        proxy_layout.addRow(self.proxy_from_selection_check)
        proxy_layout.addRow(_qt_button("Create Proxy", create_proxy_from_ui))
        return widget

    def _build_named_properties_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Stored on the selected LOD, exported to P3D TAGGs."))

        form = qt_widgets.QFormLayout()
        layout.addLayout(form)

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

        named_buttons = qt_widgets.QHBoxLayout()
        named_buttons.addWidget(_qt_button("Add / Update", _commit_named_property_fields, "Save the current name/value pair on the active LOD."))
        named_buttons.addWidget(_qt_button("Remove", _remove_named_property, "Remove the selected property from the active LOD."))
        layout.addLayout(named_buttons)

        self.refresh_named_properties()
        return widget

    def _build_materials_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Pick a material, set its texture / rvmat paths. Edits save instantly."))

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

    def _build_validation_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(_hint("Validate before export. Scene = every LOD; Selection = selected only."))
        buttons = qt_widgets.QHBoxLayout()
        buttons.addWidget(_qt_button("Scene", _validate_scene_no_flush))
        buttons.addWidget(_qt_button("Selection", _validate_selection_no_flush))
        layout.addLayout(buttons)
        layout.addStretch()
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
            "preset": self.auto_lod_preset.currentText() if self.auto_lod_preset is not None else "QUADS",
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

    def model_cfg_import_path(self):
        field = _picker_field(self.model_cfg_import)
        return field.text().strip() if field is not None else ""

    def model_cfg_export_path(self):
        field = _picker_field(self.model_cfg_export)
        return field.text().strip() if field is not None else ""

    def mass_value(self):
        return self.mass_value_field.value() if self.mass_value_field is not None else 1.0

    def mass_mode(self):
        return self.mass_mode_combo.currentText() if self.mass_mode_combo is not None else "All vertices"

    def flag_component(self):
        return self.flag_component_combo.currentText() if self.flag_component_combo is not None else "Face"

    def flag_value(self):
        return self.flag_value_field.value() if self.flag_value_field is not None else 1

    def flag_name(self):
        return self.flag_name_field.text().strip() if self.flag_name_field is not None else "a3ob_flag"

    def proxy_path(self):
        field = _picker_field(self.proxy_path_field)
        return field.text().strip() if field is not None else ""

    def proxy_index(self):
        return self.proxy_index_field.value() if self.proxy_index_field is not None else 1

    def proxy_from_selection(self):
        return self.proxy_from_selection_check.isChecked() if self.proxy_from_selection_check is not None else True

    def selected_named_property_lod(self):
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
        selected_lod = _selected_lod_transform()
        prev_node = self.selected_selection_set_node()
        self.selection_list.blockSignals(True)
        self.selection_list.clear()

        if not selected_lod:
            # No DayZ LOD in the current selection — show nothing but a prompt.
            self.selection_list.blockSignals(False)
            if self.selection_mesh_context is not None:
                self.selection_mesh_context.setText("Select a DayZ LOD to see its selections.")
            self.set_selection_details("Select a row to see details.")
            return

        lod_label = _lod_name_from_transform(selected_lod)
        if self.selection_mesh_context is not None:
            self.selection_mesh_context.setText(f"Selections on {lod_label}")

        restore_row = -1
        for item in _selection_sets():
            if item["lod"] != lod_label:
                continue
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
            cmds.a3obCreateLOD(
                lodType=definition["type"],
                resolution=resolution,
                name=_lod_node_name(definition, resolution),
            )

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
