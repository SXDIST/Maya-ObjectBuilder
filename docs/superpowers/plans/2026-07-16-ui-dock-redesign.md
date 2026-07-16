# UI Dock Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переработать dock плагина MayaObjectBuilder в единый Qt-путь с аккордеон-панелями (стиль Blender N-panel), лёгким полишем без QSS и встроенными иконками Maya.

**Architecture:** Всё живёт в одном файле `scripts/objectBuilderMenu.py`. Класс `MayaObjectBuilderDock` (PySide6) уже самодостаточен и содержит всю UI-логику; параллельный legacy native-`cmds` путь (`_build_dock_contents` и его builder-функции) существует только как fallback и удаляется. `QTabWidget` заменяется вертикальным `QScrollArea` со стеком `_CollapsibleSection`. Бизнес-функции роутятся через `_active_qt_dock()`; их native-ветки под `exists=True` guard'ами становятся мёртвыми и вычищаются.

**Tech Stack:** Python 3 (Maya 2027), PySide6 (`QtWidgets`/`QtCore`/`QtGui`), shiboken6, Maya `cmds`. Тесты — `py_compile` + smoke через Maya MCP в живой сессии + существующие `tests/mayapy` workflows.

## Global Constraints

- Имена команд `a3ob*`, их флаги и схема атрибутов `a3ob*` — НЕ меняются.
- Логика import/export P3D и model.cfg — НЕ меняется.
- Сигнатуры точек входа `show_plugin_ui()`, `hide_plugin_ui()`, `open_dock()` — НЕ меняются.
- Никакого QSS (`setStyleSheet`). Фон/акценты — только через `QPalette` и `QFont`.
- Иконки — только встроенные Maya-ресурсы (`:/...`), с fallback на текст. Внешних ассетов не добавлять.
- Все изменения — в одном файле `scripts/objectBuilderMenu.py`. Каждый коммит стейджит точечно: `git add scripts/objectBuilderMenu.py` (рабочее дерево содержит несвязанный незакоммиченный рефактор — НЕ делать `git add -A`).
- Спецификация: `docs/superpowers/specs/2026-07-16-ui-dock-redesign-design.md`.

---

## File Structure

- Modify: `scripts/objectBuilderMenu.py` — единственный изменяемый файл.
  - Импорт-блок (строки 9–23): добавить `PySide6.QtGui` как `qt_gui`.
  - `_CollapsibleSection` (1864–1892): полиш без QSS + persist состояния в `optionVar`.
  - `_qt_button` (1856–1861): опциональная иконка.
  - `MayaObjectBuilderDock._build_ui` (1946–1957) и `_build_lod_tab`/`_build_metadata_tab` (1975–2164): аккордеон-раскладка + объединение Mass & Flags + отдельная панель Proxies.
  - `open_dock` (2759–2777): убрать native fallback-ветку.
  - Роутящие функции (`_refresh_lod_assignment_ui`, `_refresh_context_ui`, `_selected_lod_definition`, `_lod_resolution_value`, `apply_mass_from_ui`, `apply_flag_from_ui`, `generate_auto_lods_from_ui`, `create_proxy_from_ui`, module-level `_refresh_*`): убрать native-ветки.
  - Удалить: native builder/helper-функции и native control-name константы (полный список в Task 4).

---

## Task 1: UI-инфраструктура — импорт QtGui, иконки, полиш секций, persist

**Files:**
- Modify: `scripts/objectBuilderMenu.py` (импорт-блок 9–23; `_qt_button` 1856–1861; `_CollapsibleSection` 1864–1892)

**Interfaces:**
- Produces:
  - `qt_gui` — модуль `PySide6.QtGui` (или `None`, если Qt недоступен).
  - `UI_MARGIN = 8`, `UI_SPACING = 6` — константы отступов.
  - `_qt_icon(name)` → `QIcon` (пустой `QIcon`, если ресурс не найден или Qt нет).
  - `_qt_button(label, callback, tooltip="", icon="")` → `QPushButton` (иконка опциональна).
  - `_panel_optionvar_key(title)` → `str` — ключ optionVar для панели.
  - `_CollapsibleSection(title, collapsed=False, parent=None)` — с `.body_layout`; фон заголовка через `QPalette`, состояние раскрытости持istится в `optionVar`.

- [ ] **Step 1: Добавить `qt_gui` в импорт-блок**

В `try:`-блоке импортов (после строки 15 `qt_core = importlib.import_module("PySide6.QtCore")`) добавить:

```python
    qt_gui = importlib.import_module("PySide6.QtGui")
```

В `except ImportError:`-блоке (после строки 22 `qt_core = None`) добавить:

```python
    qt_gui = None
```

- [ ] **Step 2: Добавить константы отступов и helper иконок**

Сразу после импорт-блока (после строки 23, перед `SCRIPT_PATH`) добавить:

```python
UI_MARGIN = 8
UI_SPACING = 6


def _qt_icon(name):
    if not QT_AVAILABLE or qt_gui is None or not name:
        return qt_gui.QIcon() if qt_gui is not None else None
    icon = qt_gui.QIcon(name)
    return icon if not icon.isNull() else qt_gui.QIcon()
```

- [ ] **Step 3: Расширить `_qt_button` опциональной иконкой**

Заменить `_qt_button` (1856–1861) на:

```python
def _qt_button(label, callback, tooltip="", icon=""):
    button = qt_widgets.QPushButton(label)
    if icon:
        qicon = _qt_icon(icon)
        if qicon is not None and not qicon.isNull():
            button.setIcon(qicon)
    if tooltip:
        button.setToolTip(tooltip)
    button.clicked.connect(callback)
    return button
```

- [ ] **Step 4: Переписать `_CollapsibleSection` — полиш без QSS + persist**

Заменить весь класс `_CollapsibleSection` (1864–1892) на:

```python
def _panel_optionvar_key(title):
    slug = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
    return "MayaObjectBuilder_panel_%s_expanded" % slug


class _CollapsibleSection(qt_widgets.QWidget):
    def __init__(self, title, collapsed=False, parent=None):
        super(_CollapsibleSection, self).__init__(parent)
        self._title = title
        self._key = _panel_optionvar_key(title)
        if cmds.optionVar(exists=self._key):
            collapsed = not bool(cmds.optionVar(query=self._key))

        header = qt_widgets.QFrame()
        header.setAutoFillBackground(True)
        if qt_gui is not None:
            pal = header.palette()
            pal.setColor(qt_gui.QPalette.Window, pal.color(qt_gui.QPalette.Mid))
            header.setPalette(pal)
        header_layout = qt_widgets.QHBoxLayout(header)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(6)

        self._btn = qt_widgets.QPushButton(("▶ " if collapsed else "▼ ") + title)
        self._btn.setFlat(True)
        self._btn.setCheckable(True)
        self._btn.setChecked(not collapsed)
        self._btn.setCursor(qt_core.Qt.PointingHandCursor)
        font = self._btn.font()
        font.setBold(True)
        self._btn.setFont(font)
        self._btn.setStyleSheet("")  # ensure no inherited stylesheet
        self._btn.setSizePolicy(qt_widgets.QSizePolicy.Expanding, qt_widgets.QSizePolicy.Preferred)
        header_layout.addWidget(self._btn)

        self._body = qt_widgets.QFrame()
        self._body.setFrameShape(qt_widgets.QFrame.NoFrame)
        self._body.setVisible(not collapsed)
        self.body_layout = qt_widgets.QVBoxLayout(self._body)
        self.body_layout.setContentsMargins(12, 6, 4, 6)
        self.body_layout.setSpacing(UI_SPACING)

        outer = qt_widgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 4, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(header)
        outer.addWidget(self._body)
        self._btn.toggled.connect(self._on_toggle)

    def _on_toggle(self, checked):
        self._body.setVisible(checked)
        self._btn.setText(("▼ " if checked else "▶ ") + self._title)
        cmds.optionVar(intValue=(self._key, 1 if checked else 0))
```

Примечание: `self._btn.setStyleSheet("")` намеренно очищает любой stylesheet — единственный вызов `setStyleSheet`, и он пустой (не задаёт QSS-правил). Заголовок красится через `QPalette`.

- [ ] **Step 5: py_compile**

Run: `python -m py_compile scripts/objectBuilderMenu.py`
Expected: без ошибок (пустой вывод, код возврата 0).

- [ ] **Step 6: Smoke-тест в живой Maya-сессии (Maya MCP)**

Выполнить в сессии:

```python
import importlib, sys
sys.path.insert(0, r"C:\Users\targaryen\orca\Maya-ObjectBuilder\scripts")
import objectBuilderMenu as m
importlib.reload(m)
sec = m._CollapsibleSection("Test Panel", collapsed=False)
sec._on_toggle(False)  # свернуть
import maya.cmds as cmds
assert cmds.optionVar(query="MayaObjectBuilder_panel_Test_Panel_expanded") == 0
sec._on_toggle(True)   # раскрыть
assert cmds.optionVar(query="MayaObjectBuilder_panel_Test_Panel_expanded") == 1
cmds.optionVar(remove="MayaObjectBuilder_panel_Test_Panel_expanded")
print("Task1 OK")
```

Expected: печатает `Task1 OK` без исключений.

- [ ] **Step 7: Commit**

```bash
git add scripts/objectBuilderMenu.py
git commit -m "ui: add QtGui import, icon helper, palette-based collapsible section with persisted state"
```

---

## Task 2: Аккордеон-раскладка `_build_ui` + Quick Actions с иконками

**Files:**
- Modify: `scripts/objectBuilderMenu.py` (`MayaObjectBuilderDock._build_ui` 1946–1957; `_build_quick_actions` 1959–1973)

**Interfaces:**
- Consumes: `_CollapsibleSection`, `_qt_button(..., icon=...)`, `_qt_icon`, `UI_MARGIN`, `UI_SPACING` (Task 1); существующие методы-строители `_build_lod_properties_section`, `_build_auto_lod_section`, `_build_memory_points_section`, `_build_mass_flags_section`, `_build_proxies_section`, `_build_named_properties_tab`, `_build_materials_tab`, `_build_selections_tab`, `_build_skeleton_section`, `_build_validation_tab` (существующие или создаются в Task 3).
- Produces: `_build_ui` строит вертикальный аккордеон из панелей в фиксированном порядке; `_build_quick_actions` возвращает `QGroupBox` c 4 кнопками-иконками.

> ЗАВИСИМОСТЬ: панельные секции (`_build_lod_properties_section` и т.д.) выделяются в Task 3. Выполнять Task 3 ДО Task 2, либо в Task 2 временно оставить сборку через существующие `_build_lod_tab`/`_build_metadata_tab`. Порядок исполнения: Task 1 → Task 3 → Task 2 → Task 4. (Task 3 меняет тела методов, Task 2 меняет их компоновку.)

- [ ] **Step 1: Переписать `_build_quick_actions` с иконками (4 действия)**

Заменить `_build_quick_actions` (1959–1973) на:

```python
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
```

- [ ] **Step 2: Переписать `_build_ui` — аккордеон вместо табов**

Заменить `_build_ui` (1946–1957) на:

```python
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
```

Примечание: `self.memory_points_group` теперь ссылается на `_CollapsibleSection` панели Memory Points (её показывает/прячет `_update_memory_points_visibility`, вызывая `.setVisible(...)` — интерфейс `QWidget` сохранён).

- [ ] **Step 3: py_compile**

Run: `python -m py_compile scripts/objectBuilderMenu.py`
Expected: без ошибок (код возврата 0). Если `AttributeError`-подсказок нет — компилятор не проверяет наличие методов; фактические методы появятся после Task 3.

- [ ] **Step 4: Smoke-тест в Maya (после Task 3) — построение дока**

> Выполнять этот шаг ПОСЛЕ Task 3 (методы-секции должны существовать).

```python
import importlib, sys
sys.path.insert(0, r"C:\Users\targaryen\orca\Maya-ObjectBuilder\scripts")
import objectBuilderMenu as m
importlib.reload(m)
m.hide_plugin_ui()
ctrl = m.show_plugin_ui()
print("dock control:", ctrl)
dock = m._active_qt_dock()
assert dock is not None, "Qt dock not built"
print("Task2 OK")
```

Expected: печатает `dock control: ...` и `Task2 OK`; dock видим в Maya, панели раскрываются/сворачиваются, Quick Actions с иконками.

- [ ] **Step 5: Commit**

```bash
git add scripts/objectBuilderMenu.py
git commit -m "ui: replace tabbed layout with accordion panels and icon quick actions"
```

---

## Task 3: Выделить панельные секции (LOD/Auto LOD/Memory/Mass&Flags/Proxies/Skeleton)

**Files:**
- Modify: `scripts/objectBuilderMenu.py` (`_build_lod_tab` 1975–2066; `_build_files_tab` 2068–2086; `_build_metadata_tab` 2109–2164)

**Interfaces:**
- Consumes: `_CollapsibleSection`, `_qt_button`, `UI_*` (Task 1); существующие поля/методы класса (`self.lod_type_combo`, `self.auto_lod_*`, `self.mass_*`, `self.flag_*`, `self.proxy_*`, `self.model_cfg_*`, `self._path_picker`, `generate_auto_lods_from_ui`, `add_memory_point`, `add_point_to_selection`, `apply_mass_from_ui`, `clear_mass_from_ui`, `apply_flag_from_ui`, `create_proxy_from_ui`, `import_model_cfg_from_ui`, `export_model_cfg_from_ui`).
- Produces (все возвращают `QWidget`): `_build_lod_properties_section`, `_build_auto_lod_section`, `_build_memory_points_section`, `_build_mass_flags_section`, `_build_proxies_section`, `_build_skeleton_section`.

- [ ] **Step 1: Заменить `_build_lod_tab` тремя методами-секциями**

Удалить метод `_build_lod_tab` целиком (1975–2066) и вставить на его место:

```python
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
        memory_hint = qt_widgets.QLabel(
            "Add Memory Point — creates a new named locator (one vertex). "
            "Add Point to Selection — select an existing memory point and click this to add a second vertex; "
            "the first click auto-converts it to a named group with two point locators inside."
        )
        memory_hint.setWordWrap(True)
        layout.addWidget(memory_hint)
        mem_buttons = qt_widgets.QHBoxLayout()
        mem_buttons.addWidget(_qt_button("Add Memory Point", add_memory_point, "Create a new named locator under the selected Memory LOD."))
        mem_buttons.addWidget(_qt_button("Add Point to Selection", add_point_to_selection, "Add another locator to the same named selection as the selected memory point."))
        layout.addLayout(mem_buttons)
        return widget
```

- [ ] **Step 2: Заменить `_build_metadata_tab` двумя методами (Mass & Flags + Proxies)**

Удалить метод `_build_metadata_tab` целиком (2109–2164) и вставить на его место:

```python
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
```

- [ ] **Step 3: Заменить `_build_files_tab` на `_build_skeleton_section`**

Удалить метод `_build_files_tab` целиком (2068–2086) и вставить на его место:

```python
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
```

- [ ] **Step 4: Убрать внутренние отступы у переиспользуемых методов-панелей**

Методы `_build_named_properties_tab` (2166), `_build_materials_tab` (2202), `_build_selections_tab` (2233), `_build_validation_tab` (2283) остаются, но их внешний `layout.setContentsMargins(8, 8, 8, 8)` заменить на `layout.setContentsMargins(0, 0, 0, 0)` (в каждом — первый layout виджета), т.к. отступ теперь даёт `_CollapsibleSection.body_layout`. В каждом методе найти строку `layout.setContentsMargins(8, 8, 8, 8)` и заменить на `layout.setContentsMargins(0, 0, 0, 0)`.

- [ ] **Step 5: py_compile**

Run: `python -m py_compile scripts/objectBuilderMenu.py`
Expected: без ошибок (код возврата 0).

- [ ] **Step 6: Smoke-тест в Maya — построение всех панелей**

```python
import importlib, sys
sys.path.insert(0, r"C:\Users\targaryen\orca\Maya-ObjectBuilder\scripts")
import objectBuilderMenu as m
importlib.reload(m)
m.hide_plugin_ui()
ctrl = m.show_plugin_ui()
dock = m._active_qt_dock()
assert dock is not None
# все поля панелей проинициализированы
for attr in ("lod_type_combo","lod_resolution","auto_lod_preset","mass_value_field",
             "flag_component_combo","proxy_path_field","model_cfg_import",
             "named_list","material_list","selection_list"):
    assert getattr(dock, attr) is not None, attr
print("Task3 OK")
```

Expected: печатает `Task3 OK`; в доке видны все 10 панелей + Quick Actions.

- [ ] **Step 7: Commit**

```bash
git add scripts/objectBuilderMenu.py
git commit -m "ui: split tabs into standalone accordion panel builders, merge Mass & Flags"
```

---

## Task 4: Удалить legacy native-`cmds` путь и упростить роутинг

**Files:**
- Modify: `scripts/objectBuilderMenu.py` (native control-name константы 31–66; роутящие функции 366–412, 469–486, 524–566; `open_dock` 2759–2777; native builder-функции 1369–1853, 1604–1642, 1707–1772, 2694–2756)

**Interfaces:**
- Consumes: `_active_qt_dock()` (без изменений).
- Produces: единый Qt-путь; `open_dock` строит только `MayaObjectBuilderDock`; роутящие функции без native-веток.

- [ ] **Step 1: Упростить `open_dock` — убрать native fallback**

В `open_dock` (2759–2777) заменить блок (2771–2776):

```python
    if QT_AVAILABLE and _build_qt_dock(control):
        _install_context_refresh_job(control)
        return control
    cmds.setParent(control)
    _build_dock_contents()
    _install_context_refresh_job(control)
    return control
```

на:

```python
    if not (QT_AVAILABLE and _build_qt_dock(control)):
        cmds.warning("MayaObjectBuilder requires PySide6; UI could not be built.")
        return control
    _install_context_refresh_job(control)
    return control
```

- [ ] **Step 2: Упростить роутящие функции — убрать native-ветки**

Заменить `_refresh_context_ui` (1608–1623) на:

```python
def _refresh_context_ui():
    dock = _active_qt_dock()
    if dock is None:
        return
    dock.refresh_lod_assignment()
    dock.refresh_named_properties()
    dock.refresh_material_metadata()
    dock.refresh_selection_manager(True)
```

Заменить `_refresh_lod_assignment_ui` (395–412) на:

```python
def _refresh_lod_assignment_ui(*_):
    dock = _active_qt_dock()
    if dock is not None:
        dock.refresh_lod_assignment()
```

Заменить `_selected_lod_definition` (366–373) на:

```python
def _selected_lod_definition():
    dock = _active_qt_dock()
    if dock is not None:
        return dock.selected_lod_definition()
    return LOD_DEFINITIONS[0]
```

Заменить `_lod_resolution_value` (376–384) на:

```python
def _lod_resolution_value(definition):
    if not definition["has_resolution"]:
        return definition["default_resolution"]
    dock = _active_qt_dock()
    if dock is not None:
        return dock.lod_resolution_value()
    return definition["default_resolution"]
```

Заменить `generate_auto_lods_from_ui` (483–489) на:

```python
def generate_auto_lods_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    generated = _auto_lod_module().generate_auto_lods(dock.auto_lod_settings())
    if generated:
        _refresh_context_ui()
```

Заменить `apply_mass_from_ui` (524–537) на:

```python
def apply_mass_from_ui():
    load_plugin()
    dock = _active_qt_dock()
    if dock is None:
        return
    value = dock.mass_value()
    mode = dock.mass_mode()
    cmds.undoInfo(openChunk=True, chunkName="Set Mass")
    try:
        cmds.a3obSetMass(value=value, selectedComponents=(mode == "Selected vertices"))
    finally:
        cmds.undoInfo(closeChunk=True)
```

- [ ] **Step 3: Упростить `apply_flag_from_ui` и `create_proxy_from_ui`**

Прочитать текущие тела `apply_flag_from_ui` (549+) и `create_proxy_from_ui` (570+). Для каждой: заменить блок вида
`dock = _active_qt_dock(); if dock is not None: <dock-ветка> else: <native cmds ... exists=True>`
на dock-only:

```python
    dock = _active_qt_dock()
    if dock is None:
        return
    # ... использовать dock.flag_component()/dock.flag_value()/dock.flag_name()
    #     (или dock.proxy_path()/dock.proxy_index()/dock.proxy_from_selection())
```

сохранив вызовы `cmds.a3obSetFlag(...)` / `cmds.a3obProxy(...)` и `undoInfo`-обёртки без изменений. (Показать конкретный diff по факту чтения — тела короткие, паттерн идентичен `apply_mass_from_ui`.)

- [ ] **Step 4: Удалить native builder-функции и helpers**

Удалить целиком следующие определения (все — native `cmds`-UI, недостижимы после Steps 1–3):

- `_refresh_named_properties`, `_refresh_material_metadata`, `_refresh_selection_manager`, `_refresh_named_property_lods`, `_refresh_lod_filter`, `_select_named_property` (native-версии, если дублируют методы класса) — **проверить grep'ом** (см. Step 5) перед удалением.
- `_build_named_properties_ui` (1369), `_build_material_metadata_ui` (1566), `_build_selection_manager_ui` (1579), `selection_manager` (1604 — это просто `open_dock()`, оставить как тонкую обёртку ИЛИ удалить, если нет внешних вызовов — проверить grep'ом).
- `_action_button` (1638), `_icon_action` (1645), `_button_stack` (1654), `_compact_button_stack` (1663), `_action_row` (1672), `_quick_action_bar` (1684), `_button_pair` (1695), `_two_column_buttons` (1699), `_full_width_button` (1703).
- `_browse_path` (1707), `_clear_text_field` (1716), `_path_row` (1721).
- `_card` (1735), `_end_card` (1739), `_labeled_row` (1743), `_section` (1751), `_end_section` (1758), `_start_tab` (1763), `_end_tab` (1769).
- `_build_lod_assignment_ui` (1774), `_build_metadata_tools_ui` (1816), `_build_validation_ui` (1847).
- `_auto_lod_settings_from_legacy_ui` (469).
- `_build_dock_contents` (2694).

- [ ] **Step 5: Удалить осиротевшие native control-name константы**

Удалить строковые константы имён native-контролов, ставшие неиспользуемыми (31–66): `LOD_TYPE_MENU`, `LOD_RESOLUTION_FIELD`, `LOD_PREVIEW_TEXT`, `LOD_CONTEXT_TEXT`, `AUTO_LOD_*`, `SELECTION_MANAGER_*`, `NAMED_PROPERTIES_*`, `MATERIAL_METADATA_*`, `MASS_VALUE_FIELD`, `MASS_MODE_MENU`, `FLAG_*`, `PROXY_*_FIELD`, `PROXY_FROM_SELECTION_CHECK`, `MODEL_CFG_IMPORT_FIELD`, `MODEL_CFG_EXPORT_FIELD`.

Перед удалением КАЖДОГО имени — проверить grep'ом, что живых ссылок не осталось:

Run: `git grep -n "LOD_TYPE_MENU\|SELECTION_MANAGER_LIST\|MASS_VALUE_FIELD\|NAMED_PROPERTIES_LIST\|MATERIAL_METADATA_LIST\|PROXY_PATH_FIELD\|MODEL_CFG_IMPORT_FIELD" -- scripts/objectBuilderMenu.py`
Expected: после удаления соответствующих функций — совпадений нет (пустой вывод). Если совпадение осталось — это живой потребитель; не удалять константу, разобраться.

> Сохранить константы, которые всё ещё используются (`MENU_NAME`, `PLUGIN_NAME`, `TRANSLATOR_NAME`, `DOCK_NAME` — они не native-UI-контролы).

- [ ] **Step 6: py_compile**

Run: `python -m py_compile scripts/objectBuilderMenu.py`
Expected: без ошибок (код возврата 0). `NameError` на этапе компиляции не ловится — проверка живых ссылок в Step 7.

- [ ] **Step 7: Проверить отсутствие мёртвых ссылок**

Run: `git grep -n "_build_dock_contents\|_quick_action_bar\|_action_row\|_card(\|_path_row\|_build_lod_assignment_ui\|_auto_lod_settings_from_legacy_ui\|_start_tab" -- scripts/objectBuilderMenu.py`
Expected: пустой вывод (все определения и вызовы удалены).

- [ ] **Step 8: Smoke-тест в Maya — полный цикл load/reload/unload**

```python
import importlib, sys
sys.path.insert(0, r"C:\Users\targaryen\orca\Maya-ObjectBuilder\scripts")
import objectBuilderMenu as m
importlib.reload(m)
m.hide_plugin_ui()
m.show_plugin_ui()
dock = m._active_qt_dock()
assert dock is not None
m._refresh_context_ui()          # роутинг без native-веток
m.hide_plugin_ui()
assert m._active_qt_dock() is None
print("Task4 OK")
```

Expected: печатает `Task4 OK` без исключений.

- [ ] **Step 9: Commit**

```bash
git add scripts/objectBuilderMenu.py
git commit -m "ui: remove legacy native-cmds dock path and dead control constants"
```

---

## Task 5: Полная регрессия и визуальная приёмка

**Files:**
- Test: `tests/mayapy/p3d_workflow.py`, `tests/mayapy/model_cfg_workflow.py` (запуск, без изменений)

**Interfaces:**
- Consumes: финальный `scripts/objectBuilderMenu.py`.

- [ ] **Step 1: py_compile по чек-листу CLAUDE.md**

Run:
```bash
python -m py_compile plug-ins/*.py scripts/objectBuilderMenu.py scripts/objectBuilderAutoLOD.py scripts/dev_install.py $(git ls-files 'scripts/a3ob/*.py') tests/mayapy/*.py tests/python/*.py
```
Expected: без ошибок (код возврата 0).

- [ ] **Step 2: Pure-Python формат-тесты (страховка — UI их не касается)**

Run:
```bash
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
```
Expected: `PASS`-строки, ненулевых ошибок нет.

- [ ] **Step 3: Оба mayapy workflow (регрессия команд/атрибутов)**

Run:
```bash
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
```
Expected: `p3d_workflow` — 14 OK-проверок без ошибок; `model_cfg_workflow` — `OK model.cfg joints=18 root=Hip`.

- [ ] **Step 4: Визуальная приёмка в живой Maya (пользователь)**

В сессии: `hide_plugin_ui()` → reload → `show_plugin_ui()`. Проверить глазами:
- Quick Actions с иконками (Import/Export P3D, Auto LOD, Validate).
- 10 аккордеон-панелей в заданном порядке; заголовки с фоном-подложкой и жирным текстом.
- Сворачивание/раскрытие работает; после reload состояние панелей восстанавливается (persist).
- Панель Mass & Flags содержит обе группы; Proxies — отдельно.
- Смена выделения меша обновляет LOD Properties/Selections; Memory Points панель показывается только для Memory LOD.
- Импорт тестовой фикстуры P3D → правка LOD/mass/selection → экспорт без ошибок.

- [ ] **Step 5: Финальный commit (при необходимости — только если Step 4 потребовал правок)**

```bash
git add scripts/objectBuilderMenu.py
git commit -m "ui: polish accordion dock after visual review"
```

---

## Self-Review

- **Spec coverage:** ✔ единый Qt-путь (Task 4), аккордеон-панели (Task 2/3), объединение Mass & Flags (Task 3), иконки Maya (Task 1/2), без QSS через QPalette (Task 1), persist optionVar (Task 1), dock-контейнер и точки входа без изменений (Task 4), тестирование (Task 5).
- **Placeholder scan:** Task 4 Step 3 намеренно процедурный (тела `apply_flag_from_ui`/`create_proxy_from_ui` читаются на месте — паттерн идентичен показанному `apply_mass_from_ui`); Task 4 Step 4 список удаления с grep-верификацией — это стандартная безопасная процедура dead-code removal, не заглушка.
- **Type consistency:** имена методов-секций в `_build_ui` (Task 2) совпадают с определениями в Task 3 (`_build_lod_properties_section`, `_build_auto_lod_section`, `_build_memory_points_section`, `_build_mass_flags_section`, `_build_proxies_section`, `_build_skeleton_section`) и с переиспользуемыми (`_build_named_properties_tab`, `_build_materials_tab`, `_build_selections_tab`, `_build_validation_tab`). Порядок исполнения зафиксирован: Task 1 → Task 3 → Task 2 → Task 4 → Task 5.
