"""The MayaObjectBuilder dock widget — assembles the panel mixins."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene_ops import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.recent import recent_paths, remember_path

from a3ob.ui.panels.lod_list import LodListPanelMixin
from a3ob.ui.panels.lod import LodPanelMixin
from a3ob.ui.panels.metadata import MetadataPanelMixin
from a3ob.ui.panels.named_properties import NamedPropertiesPanelMixin
from a3ob.ui.panels.materials import MaterialsPanelMixin
from a3ob.ui.panels.selections import SelectionsPanelMixin
from a3ob.ui.panels.validation import ValidationPanelMixin


class MayaObjectBuilderDock(LodListPanelMixin, LodPanelMixin, MetadataPanelMixin, NamedPropertiesPanelMixin, MaterialsPanelMixin, SelectionsPanelMixin, ValidationPanelMixin, qt_widgets.QWidget if QT_AVAILABLE else object):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MayaObjectBuilderQtDock")
        self.lod_list = None
        self.lod_list_context = None
        self._syncing_lod_list = False
        self.lod_toggle = None
        self._syncing_from_selection = False
        self.lod_type_combo = None
        self.lod_resolution = None
        self.lod_context = None
        self.memory_points_group = None
        self.auto_lod_output = None
        self.auto_lod_reduction = None
        self.auto_lod_first = None
        self.auto_lod_resolution = None
        self.auto_lod_geometry = None
        self.auto_lod_memory = None
        self.auto_lod_fire = None
        self.auto_lod_view = None
        self.auto_lod_geometry_type = None
        self.auto_lod_fire_quality = None
        self.mass_value_field = None
        self.mass_mode_combo = None
        self.mass_total_label = None
        self.mass_density_field = None
        self.validation_list = None
        self.validation_summary = None
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
        self._live_sections = {}   # panel title -> _CollapsibleSection (for auto-refresh)
        self._poll_snaps = {}      # panel title -> last scene snapshot
        self._build_ui()
        self.refresh_lod_assignment()
        # Diff-based auto-refresh: keeps open live panels current after scene changes
        # (e.g. reassigning a material) that don't fire a SelectionChanged event.
        self._poll_timer = qt_core.QTimer(self)
        self._poll_timer.setInterval(500)
        self._poll_timer.timeout.connect(self._poll_live_panels)
        self._poll_timer.start()


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
            ("LODs", self._build_lod_list_section(), False, self.refresh_lod_list),
            ("LOD Properties", self._build_lod_properties_section(), False, None),
            ("Auto LOD", self._build_auto_lod_section(), True, None),
            ("Mass & Flags", self._build_mass_flags_section(), True, None),
            ("Named Properties", self._build_named_properties_tab(), True, self.refresh_named_properties),
            ("Materials", self._build_materials_tab(), True, self.refresh_material_metadata),
            ("Selections", self._build_selections_tab(), True, lambda: self.refresh_selection_manager()),
            ("Proxies", self._build_proxies_section(), True, None),
            ("Memory Points", self._build_memory_points_section(), True, None),
            ("Validation", self._build_validation_tab(), True, None),
        ]
        self.memory_points_group = None
        for title, widget, collapsed, on_expand in panels:
            section = _CollapsibleSection(title, collapsed=collapsed, on_expand=on_expand)
            section.body_layout.addWidget(widget)
            body_layout.addWidget(section)
            if title == "Memory Points":
                self.memory_points_group = section
            if on_expand is not None:
                self._live_sections[title] = section
        body_layout.addStretch()

        scroll = qt_widgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(qt_widgets.QScrollArea.NoFrame)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

    # ---- diff-based auto-refresh of open live panels -------------------------------

    def _poll_live_panels(self):
        """Cheap timer tick: refresh an open live panel only when its scene snapshot changed."""
        # Bail out if the C++ widget is gone (dock deleted / Maya shutting down) — polling a
        # dead object or a torn-down scene is what produced the exit-time crash.
        if qt_is_valid is not None and not qt_is_valid(self):
            return
        try:
            self._poll_panel("LODs", self._lods_snapshot, self.refresh_lod_list)
            self._poll_panel("Materials", self._materials_snapshot, self.refresh_material_metadata,
                             defer=self._material_fields_focused())
            self._poll_panel("Selections", self._selections_snapshot, self.refresh_selection_manager)
            self._poll_panel("Named Properties", self._named_snapshot, self.refresh_named_properties,
                             defer=self._named_fields_focused())
        except Exception:
            pass  # transient scene state during undo/scene-open/teardown — retry next tick

    def _poll_panel(self, title, snapshot_fn, refresh_fn, defer=False):
        section = self._live_sections.get(title)
        if section is None or not section.is_expanded():
            return
        snap = snapshot_fn()
        if snap == self._poll_snaps.get(title):
            return
        if defer:
            return  # user is editing a field; leave the snapshot stale and retry next tick
        self._poll_snaps[title] = snap
        refresh_fn()

    def _material_fields_focused(self):
        for field in (_picker_field(self.material_texture), _picker_field(self.material_rvmat)):
            if field is not None and field.hasFocus():
                return True
        return False

    def _named_fields_focused(self):
        for combo in (self.named_name_combo, self.named_value_combo):
            if combo is None:
                continue
            if combo.hasFocus() or (combo.lineEdit() is not None and combo.lineEdit().hasFocus()):
                return True
        return False

    def _lods_snapshot(self):
        lod = _selected_lod_transform()
        active = _lod_name_from_transform(lod) if lod else None
        return (active, tuple((r["node"], r["tris"], r["selections"]) for r in lod_overview()))

    def _materials_snapshot(self):
        return tuple((i["shading_groups"][0], i["material_node"], i["texture"], i["material"])
                     for i in _material_nodes_for_selection())

    def _selections_snapshot(self):
        lod = _selected_lod_transform()
        label = _lod_name_from_transform(lod) if lod else None
        rows = []
        for node in cmds.ls(type="objectSet") or []:
            if not _attr_exists(node, "a3obSelectionName"):
                continue
            rows.append((node,
                         _safe_get_attr(node, "a3obSelectionName", "") or "",
                         bool(_safe_get_attr(node, "a3obIsProxySelection", False)),
                         _safe_get_attr(node, "a3obFlagComponent", "") or "",
                         _set_member_count(node)))
        return (label, tuple(sorted(rows)))

    def _named_snapshot(self):
        lod = self.selected_named_property_lod()
        return _safe_get_attr(lod, "a3obProperties", "") if lod else ""

    def showEvent(self, event):
        # Only poll while the dock is actually on screen; also restarts after a hide.
        if getattr(self, "_poll_timer", None) is not None and not self._poll_timer.isActive():
            self._poll_timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        # Stop polling when the dock is hidden (tab switched, closed, Maya exiting) so a
        # stray tick never touches a torn-down scene.
        if getattr(self, "_poll_timer", None) is not None:
            self._poll_timer.stop()
        super().hideEvent(event)

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


    def _path_picker(self, label, caption, mode, file_filter, recent_key=None):
        container = qt_widgets.QWidget()
        layout = qt_widgets.QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        if recent_key:
            # Editable combo seeded with recently-used paths (see a3ob.ui.recent).
            combo = qt_widgets.QComboBox()
            combo.setEditable(True)
            combo.setInsertPolicy(qt_widgets.QComboBox.NoInsert)
            combo.addItem("")
            for path in recent_paths(recent_key):
                combo.addItem(path)
            combo.setCurrentIndex(0)
            input_widget = combo
            field = combo.lineEdit()
            field.setText("")
        else:
            field = qt_widgets.QLineEdit()
            input_widget = field
        browse = _icon_button(":/fileOpen.png", "...", caption)
        clear = _icon_button(":/deleteActive.png", "X", f"Clear {label}")
        browse.clicked.connect(lambda: self._browse_qt_path(field, caption, mode, file_filter, recent_key))
        clear.clicked.connect(field.clear)
        layout.addWidget(input_widget, 1)
        layout.addWidget(browse)
        layout.addWidget(clear)
        container._line_edit = field
        container._recent_key = recent_key
        return container


    def _browse_qt_path(self, field, caption, mode, file_filter, recent_key=None):
        selected = cmds.fileDialog2(fileMode=mode, caption=caption, fileFilter=file_filter)
        if selected:
            path = _normalize_dayz_path(selected[0])
            field.setText(path)
            if recent_key:
                remember_path(recent_key, path)


__all__ = ["MayaObjectBuilderDock"]
