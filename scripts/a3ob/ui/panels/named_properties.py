"""named_properties panel of the MayaObjectBuilder dock."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403


class NamedPropertiesPanelMixin:
    def _build_named_properties_tab(self):
        widget = qt_widgets.QWidget()
        layout = qt_widgets.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(UI_SPACING)

        layout.addWidget(_hint("Stored on the selected LOD, exported to P3D TAGGs."))

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
        named_buttons.addWidget(_qt_button("Add / Update", _commit_named_property_fields, "Save the current name/value pair on the active LOD.", ":/confirm.png"))
        named_buttons.addWidget(_qt_button("Remove", _remove_named_property, "Remove the selected property from the active LOD.", ":/delete.png"))
        layout.addLayout(named_buttons)

        self.refresh_named_properties()
        return widget


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

