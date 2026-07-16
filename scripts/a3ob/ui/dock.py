"""The MayaObjectBuilder dock widget — assembles the panel mixins."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403

from a3ob.ui.panels.lod import LodPanelMixin
from a3ob.ui.panels.metadata import MetadataPanelMixin
from a3ob.ui.panels.named_properties import NamedPropertiesPanelMixin
from a3ob.ui.panels.materials import MaterialsPanelMixin
from a3ob.ui.panels.selections import SelectionsPanelMixin
from a3ob.ui.panels.skeleton import SkeletonPanelMixin
from a3ob.ui.panels.validation import ValidationPanelMixin


class MayaObjectBuilderDock(LodPanelMixin, MetadataPanelMixin, NamedPropertiesPanelMixin, MaterialsPanelMixin, SelectionsPanelMixin, SkeletonPanelMixin, ValidationPanelMixin, qt_widgets.QWidget if QT_AVAILABLE else object):
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

        # on_expand re-queries the scene when a panel is opened, so live-scene panels
        # (materials, selections, named properties) stay fresh even after changes that
        # do not fire a SelectionChanged event (e.g. reassigning a material).
        panels = [
            ("LOD Properties", self._build_lod_properties_section(), False, None),
            ("Auto LOD", self._build_auto_lod_section(), True, None),
            ("Mass & Flags", self._build_mass_flags_section(), True, None),
            ("Named Properties", self._build_named_properties_tab(), True, self.refresh_named_properties),
            ("Materials", self._build_materials_tab(), True, self.refresh_material_metadata),
            ("Selections", self._build_selections_tab(), True, lambda: self.refresh_selection_manager()),
            ("Proxies", self._build_proxies_section(), True, None),
            ("Memory Points", self._build_memory_points_section(), True, None),
            ("Skeleton (model.cfg)", self._build_skeleton_section(), True, None),
            ("Validation", self._build_validation_tab(), True, None),
        ]
        self.memory_points_group = None
        for title, widget, collapsed, on_expand in panels:
            section = _CollapsibleSection(title, collapsed=collapsed, on_expand=on_expand)
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


__all__ = ["MayaObjectBuilderDock"]
