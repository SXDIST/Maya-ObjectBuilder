# CLAUDE.md

Maya 2027 plugin (`MayaObjectBuilder.mll`) for DayZ/Object Builder P3D workflows.  
Blender add-on at `Arma3ObjectBuilder-master/` — **format reference only**, не трогаем.

---

## Сборка и тесты (запускать из корня репо)

```bash
# Сборка Debug (единственный генератор который работает)
cmake --build build --config Debug

# C++ тесты формата
build/Debug/p3d_roundtrip.exe Arma3ObjectBuilder-master/tests/inputs/p3d build/p3d-roundtrip
build/Debug/model_cfg_test.exe Arma3ObjectBuilder-master/tests/inputs/model.cfg build/model-cfg-output.cfg

# Maya workflow тесты (полная верификация)
python -m py_compile scripts/objectBuilderMenu.py tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
```

Полный чеклист после любых изменений: сборка → p3d_roundtrip → py_compile → mayapy p3d_workflow.

---

## Навигация по задачам

| Задача | Куда идти | Конкретные функции |
|--------|-----------|--------------------|
| **Экспорт P3D** | `src/maya/MayaMeshExport.cpp` | `exportMeshLOD()` — главный цикл граней; `addUVSetTaggs()` — UVSet TAGG |
| **Импорт P3D** | `src/maya/MayaMeshImport.cpp` | `applyUVs()`, `applyNormals()`, `assignMaterials()` |
| **UV (экспорт)** | `MayaMeshExport.cpp` строки ~700–770 | Цикл граней: `getUVIndex()` → `face.uvs`; `addUVSetTaggs()` |
| **UV (импорт)** | `MayaMeshImport.cpp:applyUVs()` | `setUVs()` + `assignUVs()` |
| **P3D бинарный формат** | `src/formats/P3D.cpp` | `LOD::read()`, `LOD::write()`, все `*TaggData::read/write` |
| **Формат-референс** | `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/data_p3d.py` | Канонический Python-референс P3D MLOD |
| **Команды a3ob\*** | `src/commands/StubCommands.cpp` | `a3obValidate`, `a3obCreateLOD`, `a3obSetMass`, `a3obSetFlag`, `a3obProxy` и др. |
| **Валидация** | `StubCommands.cpp` ~строка 1000 | `MItMeshPolygon` цикл внутри `a3obValidate` |
| **UI (dock)** | `scripts/objectBuilderMenu.py` | `show_plugin_ui()`, `MayaObjectBuilderDock` |
| **Selections/flags** | `MayaMeshExport.cpp:addSelectionAndFlagData()` | Maya `objectSet` → P3D selection TAGG |
| **model.cfg** | `src/formats/ModelCfg.*`, `src/commands/ModelCfgCommands.*` | — |
| **Регистрация команд** | `src/PluginMain.cpp` | `initializePlugin()` |

---

## Критические факты P3D формата

**Грани:**
- Только треугольники (3 вершины) и квады (4 вершины)
- Треугольник → после вершин 16 байт нулевого padding; квад → без padding
- N-гоны (5+ вершин) → **автоматически треангулируются** в `exportMeshLOD()` через `polygonIt.getTriangle()`

**UV:**
- Хранятся дважды: в данных грани и в `#UVSet#` TAGG
- V-координата инвертируется: при записи `1 - v`, при чтении `1 - v`
- `#UVSet#` TAGG id **обязательно 0-based** (id=0 — первичный UV для Object Builder, id=1 = lightmap и т.п.)
- Плагин читает UV из **текущего активного** UV-сета (`meshFn.getUVs()` без имени сета)

**Оси:**
- Maya Y-up → P3D: позиция пишется `(x, z, y)`, нормали `-x, -z, -y`
- Масштаб: сантиметры, конвертация не нужна

**TAGG структура:** `active (1 byte) + name\0 (variable) + length uint32 + data`

---

## Ключевые атрибуты Maya-нодов

| Атрибут | Где живёт | Назначение |
|---------|-----------|------------|
| `a3obLodType`, `a3obResolution`, `a3obResolutionSignature` | transform | Тип и разрешение LOD |
| `a3obSourceVertices`, `a3obVertexSourceIndices` | transform | Сохранённые вершины от предыдущего импорта |
| `a3obUVSetTaggs`, `a3obUVSetTaggCount` | transform | Сохранённые UVSet TAGG от импорта |
| `a3obSharpEdges`, `a3obHasSharpEdges` | transform | Sharp edges TAGG |
| `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, `a3obFlagValue` | objectSet | Object Builder selections/flags |
| `a3obTechnicalSet`, `hiddenInOutliner` | objectSet | Скрывает сеты из Outliner |
| `a3obTexture`, `a3obMaterial` | shader | Пути к текстуре и .rvmat |

---

## Что НЕ трогать без необходимости

- `Arma3ObjectBuilder-master/` — только для справки по формату, не редактировать
- `CMakeLists.txt` / `cmake/` — сборка работает, не менять генератор
- `install/`, `scripts/package_release.ps1` — упаковка релиза, отдельная задача
- Blender тесты (`blender -b ...`) — требуют Blender, не часть обычного цикла
