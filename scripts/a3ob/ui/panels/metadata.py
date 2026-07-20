"""metadata panel of the MayaObjectBuilder dock."""

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class MetadataPanelMixin:
    def _build_flags_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Per-component flags on the active LOD, exported to P3D."))

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
        flags_layout.addRow(_qt_button("Apply Flag", apply_flag_from_ui, "Apply the flag value to the chosen component set.", ":/confirm.png"))
        layout.addWidget(flags_group)
        return widget


    def _build_proxies_section(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)
        layout.addWidget(_hint("Create a proxy placeholder (weapon, crew, light) from a P3D path + selection."))
        form_holder = qt_widgets.QWidget()
        proxy_layout = qt_widgets.QFormLayout(form_holder)
        proxy_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(form_holder)
        self.proxy_path_field = self._path_picker("Proxy path", "Select proxy P3D", 1, "Arma P3D (*.p3d)", recent_key="proxy")
        self.proxy_index_field = qt_widgets.QSpinBox()
        self.proxy_index_field.setRange(0, 2147483647)
        self.proxy_index_field.setValue(1)
        self.proxy_from_selection_check = qt_widgets.QCheckBox("Create from selected components")
        self.proxy_from_selection_check.setChecked(True)
        proxy_layout.addRow("Path", self.proxy_path_field)
        proxy_layout.addRow("Index", self.proxy_index_field)
        proxy_layout.addRow(self.proxy_from_selection_check)
        proxy_layout.addRow(_qt_button("Create Proxy", create_proxy_from_ui, "Create a proxy from the path and selected components.", ":/create.png"))
        return widget


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

