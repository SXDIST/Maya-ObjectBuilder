"""The MayaObjectBuilder dock widget — assembles the panel mixins."""

import maya.cmds as cmds

from a3ob.ui._qt import *  # noqa: F401,F403
from a3ob.ui.constants import *  # noqa: F401,F403
from a3ob.ui.widgets import *  # noqa: F401,F403
from a3ob.ui.scene import *  # noqa: F401,F403
from a3ob.ui.actions import *  # noqa: F401,F403
from a3ob.ui.entry import *  # noqa: F401,F403
from a3ob.ui.recent import recent_paths, remember_path
from a3ob.ui.watch import SceneWatcher, ALL_PANELS

from a3ob.ui.panels.lod_list import LodListPanelMixin
from a3ob.ui.panels.lod import LodPanelMixin
from a3ob.ui.panels.metadata import MetadataPanelMixin
from a3ob.ui.panels.materials import MaterialsPanelMixin
from a3ob.ui.panels.selections import SelectionsPanelMixin
from a3ob.ui.panels.validation import ValidationPanelMixin
from a3ob.ui.panels.skinning import SkinningPanelMixin


# Panels that have already warned this session. Reset to an empty set when the plugin
# reloads (module re-import). Stored at module level so _warn_panel_once is testable
# without a full dock instance.
_dock_warned_panels: set = set()


def _warn_panel_once(title: str, exc: Exception) -> None:
    """Warn once per panel per session when a dock refresh raises.

    Panels rebuild on every SelectionChanged, so a recurring error would flood the Script
    Editor. After the first warning per panel, further failures are silently ignored until
    the plugin is reloaded (which re-imports this module and clears the set)."""
    if title in _dock_warned_panels:
        return
    _dock_warned_panels.add(title)
    cmds.warning(
        "MayaObjectBuilder dock panel '%s' raised %s: %s "
        "(further errors for this panel are suppressed until the plugin is reloaded)"
        % (title, type(exc).__name__, exc)
    )


class MayaObjectBuilderDock(LodListPanelMixin, LodPanelMixin, MetadataPanelMixin, MaterialsPanelMixin, SelectionsPanelMixin, ValidationPanelMixin, SkinningPanelMixin, qt_widgets.QWidget if QT_AVAILABLE else object):
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
        self.named_batch_check = None
        self.named_name_combo = None
        self.named_value_combo = None
        self.named_items = {}
        self.material_list = None
        self.texture_root_field = None
        self.paa_alpha_check = None
        self.material_texture = None
        self.material_rvmat = None
        self.material_items = {}
        self.selection_list = None
        self.selection_details = None
        self.selection_mesh_context = None
        self._live_sections = {}   # panel title -> _CollapsibleSection (for auto-refresh)
        self._poll_snaps = {}      # panel title -> last scene snapshot
        self._poll_lod = None      # selected LOD, resolved once per refresh
        self._watched_lod = None   # LOD the per-node callbacks are currently pointed at
        self._build_ui()
        self.refresh_lod_assignment()
        # Event-driven, not polled: Maya callbacks mark panels dirty and this timer only
        # debounces the burst (a single scene edit can fire many callbacks). While nothing
        # changes it never runs, so an idle dock costs nothing.
        self._dirty_panels = set()
        self._refresh_timer = qt_core.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(120)
        self._refresh_timer.timeout.connect(self._refresh_dirty_panels)
        self._watcher = SceneWatcher(self._on_scene_changed)
        self._watcher.start()


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
        # (materials, selections) stay fresh even after changes that do not fire a
        # SelectionChanged event (e.g. reassigning a material).
        panels = [
            ("LODs", self._build_lod_list_section(), False, self.refresh_lod_list),
            ("LOD Properties", self._build_lod_properties_section(), False, None),
            ("Mass & Flags", self._build_mass_flags_section(), True, None),
            ("Materials", self._build_materials_tab(), True, self.refresh_material_metadata),
            ("Selections", self._build_selections_tab(), True, lambda: self.refresh_selection_manager()),
            ("Proxies", self._build_proxies_section(), True, None),
            ("Memory Points", self._build_memory_points_section(), True, None),
            ("Skinning", self._build_skinning_tab(), True, None),
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

    # ---- event-driven refresh of open live panels ----------------------------------

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

    def _lods_snapshot(self):
        lod = self._poll_lod
        active = _lod_name_from_transform(lod) if lod else None
        # Geometry fingerprint instead of lod_overview(): the latter re-triangulates every
        # LOD mesh (19 ms) merely to decide whether anything changed. See lod_geometry_key().
        return (active, lod_geometry_key())

    def _materials_snapshot(self):
        return tuple((i["shading_groups"][0], i["material_node"], i["texture"], i["material"])
                     for i in _material_nodes_for_selection())

    def _selections_snapshot(self):
        lod = self._poll_lod
        label = _lod_name_from_transform(lod) if lod else None
        rows = []
        # Maya's own attribute filter, not "list every objectSet then probe each one".
        for node in cmds.ls("*.a3obSelectionName", objectsOnly=True) or []:
            rows.append((node,
                         _safe_get_attr(node, "a3obSelectionName", "") or "",
                         bool(_safe_get_attr(node, "a3obIsProxySelection", False)),
                         _safe_get_attr(node, "a3obFlagComponent", "") or "",
                         _set_member_count(node)))
        return (label, tuple(sorted(rows)))

    def showEvent(self, event):
        # Coming back on screen: the scene may have moved on while we were hidden.
        self._on_scene_changed(ALL_PANELS)
        super().showEvent(event)

    def hideEvent(self, event):
        # Drop any pending refresh so a stray tick never touches a torn-down scene.
        if getattr(self, "_refresh_timer", None) is not None:
            self._refresh_timer.stop()
        super().hideEvent(event)

    def teardown(self):
        """Remove the Maya callbacks. MUST run before the dock dies — a callback that
        outlives it fires into freed Python objects and crashes Maya."""
        if getattr(self, "_refresh_timer", None) is not None:
            self._refresh_timer.stop()
        watcher = getattr(self, "_watcher", None)
        if watcher is not None:
            watcher.stop()
            self._watcher = None

    def _on_scene_changed(self, hints):
        """Callback sink: remember what to rebuild and (re)arm the debounce."""
        self._dirty_panels.update(hints)
        timer = getattr(self, "_refresh_timer", None)
        if timer is not None:
            timer.start()

    def _refresh_dirty_panels(self):
        if qt_is_valid is not None and not qt_is_valid(self):
            return
        panels = self._dirty_panels
        self._dirty_panels = set()
        self._poll_lod = _selected_lod_transform()
        self._watcher_retarget(self._poll_lod)
        # Each panel is wrapped individually: one broken panel must not blank the rest.
        # Transient failures (undo/scene-open/teardown) warn exactly once per session so the
        # Script Editor stays quiet — _warn_panel_once deduplicates by panel name.
        if "LODs" in panels:
            try:
                self._poll_panel("LODs", self._lods_snapshot, self.refresh_lod_list)
            except Exception as exc:  # noqa: BLE001 - transient scene state; warn once
                _warn_panel_once("LODs", exc)
        if "Materials" in panels:
            try:
                self._poll_panel("Materials", self._materials_snapshot, self.refresh_material_metadata,
                                 defer=self._material_fields_focused())
            except Exception as exc:  # noqa: BLE001
                _warn_panel_once("Materials", exc)
        if "Selections" in panels:
            try:
                self._poll_panel("Selections", self._selections_snapshot, self.refresh_selection_manager)
            except Exception as exc:  # noqa: BLE001
                _warn_panel_once("Selections", exc)

    def _watcher_retarget(self, lod_name):
        watcher = getattr(self, "_watcher", None)
        if watcher is not None and lod_name != getattr(self, "_watched_lod", None):
            self._watched_lod = lod_name
            watcher.retarget(lod_name)

    def _build_quick_actions(self):
        group = qt_widgets.QGroupBox("Quick Actions")
        layout = qt_widgets.QGridLayout(group)
        layout.setContentsMargins(UI_MARGIN, UI_MARGIN, UI_MARGIN, UI_MARGIN)
        layout.setSpacing(UI_SPACING)
        actions = [
            ("Import P3D", import_p3d, "Open a P3D through Maya's native Arma P3D importer.", ":/fileOpen.png"),
            ("Export P3D", export_p3d, "Export the current scene through Maya's native Arma P3D exporter.", ":/fileSave.png"),
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
        # A plain QLineEdit (kept stable). Recent history is offered via a dropdown button
        # rather than a QComboBox, whose internal line edit Qt silently recreates — that
        # left a dangling reference and crashed the material refresh on selection change.
        field = qt_widgets.QLineEdit()
        browse = _icon_button(":/fileOpen.png", "...", caption)
        clear = _icon_button(":/deleteActive.png", "X", f"Clear {label}")
        browse.clicked.connect(lambda: self._browse_qt_path(field, caption, mode, file_filter, recent_key))
        clear.clicked.connect(field.clear)
        layout.addWidget(field, 1)
        if recent_key:
            recent = _icon_button(":/menuIconEdit.png", "R", "Pick a recently-used path")
            recent.clicked.connect(lambda: self._show_recent_paths_menu(field, recent_key, recent))
            layout.addWidget(recent)
        layout.addWidget(browse)
        layout.addWidget(clear)
        container._line_edit = field
        container._recent_key = recent_key
        return container


    def _show_recent_paths_menu(self, field, recent_key, anchor):
        menu = qt_widgets.QMenu(self)
        paths = recent_paths(recent_key)
        if not paths:
            action = menu.addAction("(no recent paths)")
            action.setEnabled(False)
        else:
            for path in paths:
                action = menu.addAction(path)
                action.triggered.connect(lambda checked=False, value=path: field.setText(value))
        menu.popup(anchor.mapToGlobal(anchor.rect().bottomLeft()))


    def _browse_qt_path(self, field, caption, mode, file_filter, recent_key=None):
        selected = cmds.fileDialog2(fileMode=mode, caption=caption, fileFilter=file_filter)
        if selected:
            path = _normalize_dayz_path(selected[0])
            field.setText(path)
            if recent_key:
                remember_path(recent_key, path)


__all__ = ["MayaObjectBuilderDock", "_dock_warned_panels", "_warn_panel_once"]
