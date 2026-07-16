# Разбиение крупных файлов на модули

Дата: 2026-07-16
Статус: одобрено к планированию

## Цель

Разгрузить крупные исходные файлы, разбив их на директории/поддиректории с файлами
~100–250 строк, чтобы было проще разрабатывать (редактировать 2–3 небольших файла вместо
одного на 1000–1700 строк). Поведение, публичные имена команд `a3ob*`, схема атрибутов и
результаты тестов не меняются — это перемещение кода, а не переписывание.

## Объём

Дробим (файлы > ~300 строк с чёткими швами):

| Строк | Файл | Целевой пакет |
|------:|------|---------------|
| 1700 | `scripts/objectBuilderMenu.py` | `a3ob/ui/` (widgets, panels/, dock, actions, entry) |
| 1080 | `scripts/a3ob/mayabridge/commands.py` | `a3ob/mayabridge/commands/` (по команде + base) |
| 604 | `scripts/a3ob/mayabridge/mesh_export.py` | `a3ob/mayabridge/export/` |
| 525 | `scripts/a3ob/mayabridge/mesh_import.py` | `a3ob/mayabridge/import_/` |
| 447 | `scripts/objectBuilderAutoLOD.py` | `a3ob/ui/autolod/` |
| 321 | `scripts/a3ob/ui/scene_ops.py` | `a3ob/ui/scene/` (по доменам) |

НЕ трогаем: `formats/p3d.py` (627) и `formats/model_cfg.py` (398) — высоко-когезивный формат-код,
покрытый unit-тестами; дробление даёт риск без выигрыша. Прочие файлы уже < 200 строк.

## Несущий контракт (что нельзя сломать)

1. **`tests/mayapy/p3d_workflow.py` через `runpy.run_path(scripts/objectBuilderMenu.py)`** тянет
   приватные имена (`_selection_sets`, `_live_set_members`, `_normalize_dayz_path`,
   `_canonical_selection_components`, `_clear_all_object_builder_sets`, `_active_qt_dock`,
   `_refresh_context_ui`, `_panel_optionvar_key`, `MayaObjectBuilderDock`, `_qt_button`, `_qt_icon`,
   `_CollapsibleSection`, `import_p3d`/`export_p3d`, `import_model_cfg_from_ui`/`export_...`,
   `generate_auto_lods_from_ui`, `open_dock`/`show_plugin_ui`/`hide_plugin_ui` и др.) прямо из
   namespace модуля. `objectBuilderMenu.py` остаётся **фасадом** с явными re-export этих имён.
2. **`plug-ins/MayaObjectBuilder.py`** регистрирует 9 `a3ob*` `MPxCommand`-классов по ссылке и
   `import objectBuilderMenu` для `show_plugin_ui`/`hide_plugin_ui`. Классы команд остаются
   импортируемыми из `a3ob.mayabridge.commands` (пакет с тем же именем — `__init__.py` реэкспортит).
3. **`plug-ins/MayaObjectBuilderTranslator.py`** и `a3ob.mayabridge.translator` импортируют
   `MayaMeshImport`/`MayaMeshExport` — эти имена остаются доступны из
   `a3ob.mayabridge.mesh_import`/`mesh_export` (модуль-фасад или переименование с фасадом).
4. **`scripts/objectBuilderAutoLOD.py`** загружается тестами и UI через
   `importlib.import_module("objectBuilderAutoLOD")` и `runpy.run_path` — остаётся тонким фасадом,
   реэкспортящим `generate_auto_lods` из `a3ob/ui/autolod/`.
5. **Установщик/упаковка** копируют деревья `plug-ins/` и `scripts/` целиком, поэтому новые
   поддиректории доставляются автоматически; в gate-списки (`install/install_maya.py`,
   `scripts/package_release.ps1`) добавляем по одному якорному файлу на новый пакет.

## Целевая раскладка

### `objectBuilderMenu.py` (1700) → `a3ob/ui/`

Класс `MayaObjectBuilderDock` (~800 строк) держит общее состояние (виджеты — атрибуты `self.*`),
поэтому разбиваем его на **mixin-классы** по панели; `dock.py` наследует все mixin'ы.

```
a3ob/ui/
  widgets.py            # _qt_icon, _qt_button, _icon_button, _hint, _picker_field,
                        # _panel_optionvar_key, _CollapsibleSection, _SELECTION_KIND_ICONS,
                        # UI_MARGIN/UI_SPACING re-import
  panels/
    __init__.py
    lod.py              # LodPanelMixin: LOD Properties + Auto LOD + Memory Points build + logic
    metadata.py         # MetadataPanelMixin: Mass & Flags + Proxies
    named_properties.py # NamedPropertiesPanelMixin
    materials.py        # MaterialsPanelMixin
    selections.py       # SelectionsPanelMixin
    skeleton.py         # SkeletonPanelMixin (model.cfg)
    validation.py       # ValidationPanelMixin
  dock.py               # MayaObjectBuilderDock(*PanelMixins): __init__, _build_ui,
                        # _build_quick_actions, refresh_lod_assignment, dock lifecycle helpers
  actions.py            # module-level *_from_ui wrappers + assign_lod_to_selection,
                        # create_empty_lod, add_memory_point, selection/named/material CRUD wrappers,
                        # _undo_chunk, routing (_refresh_*), _selected_* facade helpers
  entry.py              # load_plugin, import_p3d/export_p3d, import/export_model_cfg,
                        # show/hide_plugin_ui, open_dock, menu build, install/uninstall,
                        # _plugin_path, _ensure_script_path, _auto_lod_module,
                        # _qt_workspace_parent, _build_qt_dock, _delete_qt_dock, _active_qt_dock,
                        # _install_context_refresh_job, the _qt_dock_widget/_ui_script_jobs singletons
  scene_ops.py          # (existing)
  constants.py          # (existing)
scripts/objectBuilderMenu.py  # FACADE: sys.path bootstrap + `from a3ob.ui.* import ...` re-exports
```

Панель-mixin владеет своими `_build_*_section` методами, refresh/getter-методами и обращается к
`self.*`-виджетам — то же, что сейчас, только по файлам. Синглтоны `_qt_dock_widget`/`_ui_script_jobs`
и `_active_qt_dock` живут в одном месте (`entry.py`); модули, которым нужен активный dock, импортируют
`_active_qt_dock` лениво внутри функций во избежание циклов.

### `commands.py` (1080) → `a3ob/mayabridge/commands/`

```
a3ob/mayabridge/commands/
  __init__.py           # re-export: ValidateCommand, SetMassCommand, ... UpdateProxyCommand
                        # (so `from a3ob.mayabridge.commands import <Cls>` keeps working)
  base.py               # shared helpers: closed_face_islands, selected_components,
                        # create_material_nodes, component/undo helpers used by 2+ commands
  validate.py           # ValidateCommand
  mass.py               # SetMassCommand
  material.py           # SetMaterialCommand
  flag.py               # SetFlagCommand
  components.py         # FindComponentsCommand
  lod.py                # CreateLODCommand
  proxy.py              # ProxyCommand
  named_property.py     # NamedPropertyCommand
  update_proxy.py       # UpdateProxyCommand
```

`commands.py` (single module) becomes the package directory `commands/`; `plug-ins/MayaObjectBuilder.py`
already does `from a3ob.mayabridge.commands import ...` (or attribute access), preserved by `__init__`.

### `mesh_export.py` (604) → `a3ob/mayabridge/export/`

```
a3ob/mayabridge/export/
  __init__.py           # re-export MayaMeshExport
  exporter.py           # MayaMeshExport + _export_mesh_lod (core two-pass streaming)
  taggs.py              # _add_uvset_taggs, sharp edges, property/mass taggs
  locators.py           # _collect_locators_from_memory_lod + memory-LOD helpers
```
`mesh_export.py` stays as a 2-line facade `from a3ob.mayabridge.export import MayaMeshExport`, or the
package replaces it and `translator`/tests import from `a3ob.mayabridge.export`.

### `mesh_import.py` (525) → `a3ob/mayabridge/import_/`

(`import` is a keyword — package named `import_`.)
```
a3ob/mayabridge/import_/
  __init__.py           # re-export MayaMeshImport + create_* helpers used by tests
  importer.py           # MayaMeshImport + _import_lod
  materials.py          # material/shading-group creation + assignment
  locators.py           # create_locators_for_memory_lod, _create_single_locator, sanitized_name
  attributes.py         # set_lod_metadata + uv/normal application
```

### `objectBuilderAutoLOD.py` (447) → `a3ob/ui/autolod/`

```
a3ob/ui/autolod/
  __init__.py           # re-export generate_auto_lods
  core.py               # generate_auto_lods orchestration
  generators.py         # per-LOD generators (resolution/geometry/memory/fire/view)
scripts/objectBuilderAutoLOD.py  # facade: from a3ob.ui.autolod import generate_auto_lods
```

### `scene_ops.py` (321) → `a3ob/ui/scene/`

```
a3ob/ui/scene/
  __init__.py           # re-export every name objectBuilderMenu facade needs
  attrs.py              # _node_exists/_attr_exists/_safe_get_attr/_valid_nodes/_ensure_string_attr, path
  lods.py               # _is_lod_transform/_lod_transforms/_selected_lod_transform/_lod_* helpers
  selections.py         # _selection_sets and selection-set read helpers
  materials.py          # _material_nodes_for_selection, _material_metadata_label, ...
  memory.py             # memory-LOD helpers
```
Keep `scene_ops.py` as a facade re-exporting from `a3ob/ui/scene/` (tests reach these via the
objectBuilderMenu facade, which already re-exports scene_ops names).

## Стратегия и порядок (риск-ориентированный)

Делаем по одному пакету за раз, каждый — самостоятельный коммит с полной валидацией (py_compile +
оба mayapy workflow + smoke в Maya). Порядок от низкого риска к высокому:

1. `commands/` — команды независимы, чистое перемещение классов, низкий риск.
2. `scene_ops.py` → `scene/` — чистые функции, уже без dock-зависимостей.
3. `autoLOD` → `autolod/` — обособлен, грузится по фасаду.
4. `mesh_import.py` → `import_/`, `mesh_export.py` → `export/` — helpers + фасад.
5. `objectBuilderMenu.py` → `ui/` (widgets → panels → dock → actions → entry → фасад) — самый крупный
   и рискованный, делаем последним, подшагами с валидацией после каждого выделенного модуля.

Каждый пакет получает якорный файл в install/package gate-списках.

## Риски

- **runpy/private-name coupling** — фасад `objectBuilderMenu.py` должен реэкспортить каждое приватное
  имя, которое дёргают тесты; пропуск ломается только на этапе теста. Митигация: после каждого этапа
  прогонять оба mayapy workflow (они и есть проверка контракта).
- **Циклические импорты** — dock ↔ actions ↔ scene. Правило: низкоуровневые модули (scene, widgets,
  constants) не импортируют dock/actions на уровне модуля; где нужен активный dock — ленивый импорт
  внутри функции.
- **Mixin-разбиение класса** — метод-панель обращается к `self.*`, определённым в других mixin'ах;
  порядок наследования и отсутствие коллизий имён методов проверяются smoke-тестом (построение дока).
- **Регистрация команд** — `plug-ins/MayaObjectBuilder.py` регистрирует классы по ссылке; `commands/__init__`
  обязан реэкспортить все 9 классов под прежними именами. Проверка: `plugin-smoke`/оба workflow.
- **Объём** — большой. Митигация: пакет-за-пакетом, коммит и зелёная валидация перед следующим;
  механические выделения можно делегировать субагенту с обязательной верификацией смоук-тестом в Maya.

## Проверка (после каждого этапа и в конце)

1. `python -m py_compile` по чек-листу CLAUDE.md (glob подхватывает новые `scripts/a3ob/**`).
2. `python tests/python/test_p3d_roundtrip.py` и `test_model_cfg.py` (формат не тронут — страховка).
3. Оба `tests/mayapy` workflow (контракт команд/атрибутов/UI).
4. Smoke в живой Maya: load → build dock → все панели → hide (для UI-этапов).
