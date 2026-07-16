# Переработка UI dock'а MayaObjectBuilder

Дата: 2026-07-16
Статус: одобрено к реализации

## Цель

Убрать три проблемы текущего UI дока плагина (`scripts/objectBuilderMenu.py`):

1. **Дублирование кодовых путей** — параллельно живут современный Qt-dock
   (`MayaObjectBuilderDock`) и legacy native-`cmds` путь (`_build_dock_contents` и
   компания), который существует только как fallback на случай отсутствия PySide6.
2. **Раскладка/навигация** — функции разбросаны по вкладкам `QTabWidget`
   (LOD/Files/Metadata/Validation), связь между ними не очевидна.
3. **Внешний вид** — сыровато: неровные отступы, группировки, нет единой сетки.

Итог: один чистый Qt-путь, навигация аккордеон-панелями в стиле Blender N-panel,
лёгкий полиш без QSS.

## Не-цели (контракт сохраняется)

- Имена команд `a3ob*`, их флаги и схема атрибутов `a3ob*` — без изменений.
- Логика import/export P3D и model.cfg — без изменений.
- Сигнатуры точек входа `show_plugin_ui()` / `hide_plugin_ui()` / `open_dock()` —
  без изменений (меняется только их внутренняя реализация).
- Меню «MayaObjectBuilder» в главном окне Maya — остаётся.
- Никакого QSS / кастомных тем: опираемся на нативную тему Maya.

## Архитектура: один Qt-путь

В Maya 2027 PySide6 (`QT_AVAILABLE`) присутствует всегда, поэтому native-`cmds`
fallback — фактически мёртвый дубль. Удаляем его целиком:

- `_build_dock_contents`, `_start_tab`/`_end_tab`
- `_card`/`_end_card`, `_action_row`, `_quick_action_bar`, `_button_stack`,
  `_compact_button_stack`, `_button_pair`, `_two_column_buttons`, `_full_width_button`,
  `_action_button`, `_icon_action`, `_path_row`, `_browse_path`, `_clear_text_field`
- native-построители `_build_lod_assignment_ui`, `_build_validation_ui`,
  `_build_metadata_tools_ui`, `_build_material_metadata_ui`,
  `_build_selection_manager_ui`, `_build_named_properties_ui`, `_refresh_lod_assignment_ui`,
  `_refresh_context_ui` (native-часть)

`open_dock()` строит **только** `MayaObjectBuilderDock`. В batch-режиме UI не
открывается (guard `cmds.about(batch=True)` уже есть).

**Бизнес-логику НЕ трогаем** — она общая и не дублируется: `import_p3d`,
`export_p3d`, `import_model_cfg`, `export_model_cfg`, `set_mass`/`apply_mass_from_ui`,
`apply_flag_from_ui`, `create_proxy_from_ui`, `generate_auto_lods_from_ui`, все
`_refresh_*` источники данных из сцены, менеджеры selection/named-property/material.

**Распутывание helper'ов:** функции, которые сейчас читают/пишут через native-имена
контролов (`SELECTION_MANAGER_LIST`, `NAMED_PROPERTIES_LIST`, `MATERIAL_METADATA_LIST`,
`MODEL_CFG_IMPORT_FIELD` и т.п.), переводятся на методы класса `MayaObjectBuilderDock`
и Qt-виджеты. Module-level константы имён native-контролов удаляются вместе с их
единственными потребителями. Данные-справочники (`COMMON_NAMED_PROPERTIES`,
`KNOWN_NAMED_PROPS`, `LOD_DEFINITIONS` и пр.) остаются.

## Навигация: аккордеон-панели (N-panel)

Вместо `QTabWidget` — вертикальный `QScrollArea` со стеком сворачиваемых секций
(`_CollapsibleSection`, класс уже существует). Сверху — неубираемая полоса
Quick Actions. Порядок сверху вниз по типичному воркфлоу:

| Панель | Содержимое | Состояние по умолчанию |
|--------|-----------|------------------------|
| Quick Actions (фикс.) | Import P3D · Export P3D · Auto LOD · Validate | всегда видно |
| LOD Properties | DayZ LOD toggle, тип LOD, resolution, контекст-подпись | раскрыта |
| Auto LOD | пресеты генерации LOD | свёрнута |
| Mass & Flags | масса (value/mode) + флаги (component/value/name) — **объединены** | свёрнута |
| Named Properties | TAGG-свойства активного LOD | свёрнута |
| Materials | texture/rvmat выбранного материала | свёрнута |
| Selections | менеджер сетов, фильтры, Find Components | свёрнута |
| Proxies | proxy path/index/create + Update Proxy | свёрнута |
| Memory Points | локаторы Memory LOD | свёрнута |
| Skeleton (model.cfg) | import/export cfg | свёрнута |
| Validation | validate scene/selection + вывод результата | свёрнута |

Состояние раскрытости каждой панели сохраняется в `optionVar`
(ключ вида `MayaObjectBuilder_panel_<name>_expanded`), чтобы при переоткрытии дока
раскладка восстанавливалась.

## Вид: лёгкий полиш без QSS

- Единые отступы/спейсинг вынесены в константы модуля (`UI_MARGIN = 8`,
  `UI_SPACING = 6`) и применяются во всех layout'ах.
- Заголовки секций — жирный шрифт через `QFont`/`setBold(True)` (не QSS).
- Формы через `QFormLayout` с выровненными метками и одинаковой шириной полей.
- Кнопки одной высоты, сгруппированы в ровные ряды (`QHBoxLayout`/`QGridLayout`).
- **Иконки** на Quick Actions — встроенные Maya-ресурсы через `QIcon(":/<name>.png")`
  с fallback (если ресурс не найден — кнопка остаётся текстовой). Внешних
  ассетов не добавляем. Кандидаты ресурсов: `:/fileOpen.png`, `:/fileSave.png`,
  `:/polyReduce.png`/`:/LOD.png`, `:/confirm.png` (точные имена проверяются в сессии).
- Тултипы на всех действиях (частично уже есть — дополняем).

Визуальные приёмы вдохновлены сторонним STALKER 2 Toolkit (плавающее окно с
аккордеон-секциями): крупные читаемые заголовки секций и крупные кнопки действий.
Статичную preview-картинку не делаем — у P3D нет готового статичного превью, а
3D-рендер в панель избыточен.

## Контейнер: dock (не плавающее окно)

Подтверждено: используем dock (`workspaceControl`), а не отдельное плавающее окно.
Причина — плагин рассчитан на постоянную работу с выделением по ходу моделирования
(LOD, selection, mass, метаданные), где прилипающая панель, реагирующая на смену
выделения, удобнее разового окна-мастера. При желании dock штатно отрывается в
плавающее окно средствами Maya.

## Точки входа (сигнатуры без изменений)

- `show_plugin_ui()` — создаёт меню в главном окне + `open_dock()`.
- `open_dock()` — `workspaceControl` + `MayaObjectBuilderDock` (только Qt-ветка).
- `hide_plugin_ui()` — снимает scriptJob'ы, удаляет dock и меню.

## Тестирование

1. `python -m py_compile scripts/objectBuilderMenu.py` (+ остальной чек-лист из
   CLAUDE.md, чтобы ничего не задеть).
2. Smoke-тест в живой Maya-сессии через Maya MCP: `hide_plugin_ui()` → reload модуля →
   `show_plugin_ui()`; проверяем, что dock и все панели строятся без исключений,
   сигналы подключаются, `optionVar` восстановления работают.
3. Регрессия: оба `tests/mayapy` workflow остаются зелёными (UI их не касается, но
   прогоняем как страховку от случайных правок в общих helper'ах).
4. Визуальная приёмка пользователем в Maya.

## Риски

- **Переплетение helper'ов**: часть module-level функций selection/named-property
  используется и Qt-классом, и native-путём. При удалении native-пути нужно
  аккуратно сохранить те, что зовёт Qt-класс, и удалить только native-only. Митигация:
  перед удалением каждой функции — grep по её имени, убедиться, что нет живых
  вызовов из Qt-ветки.
- **Имена Maya-иконок** (`:/...`) могут отличаться между версиями. Митигация: fallback
  на текстовую кнопку + проверка доступных ресурсов в сессии перед фиксацией имён.
- **`_CollapsibleSection`** должен корректно работать внутри `QScrollArea` при
  сворачивании (пересчёт размера). Проверяем в smoke-тесте.
