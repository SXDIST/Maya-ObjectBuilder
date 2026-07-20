# UI simplification: LOD panel merge, Auto LOD at export, optional texture import

**Date:** 2026-07-20
**Status:** approved, not implemented

## Problem

The dock shows eleven collapsible panels and a four-button Quick Actions grid; the P3D
option box adds another thirty-two. A user opening it for the first time cannot
tell which controls matter. Three changes cut the surface without losing capability.

## Decisions

| Question | Decision |
|----------|----------|
| Auto LOD leaves LODs in the scene? | No — generated transiently, scene unchanged after export |
| What geometry does export generate from? | Exactly one selected mesh per export |
| Where do LOD type/resolution live? | Edited inline, in the LOD list row |
| Texture import default | On (preserves today's behaviour) |
| The 23 unwired option-box controls | Left in place — they are stubs for planned features |
| The LOD1 rename | Removed; the generator stops consuming its source |

## Section 1 — merge LODs and LOD Properties

`panels/lod.py` loses `_build_lod_properties_section`; `panels/lod_list.py` becomes the
only LOD panel. `LodPanelMixin` keeps `_build_memory_points_section` and the memory
visibility logic.

`QListWidget` becomes a four-column `QTreeWidget`:

| LOD | Type | Res | Stats |
|-----|------|-----|-------|
| `body_res1` | `[Resolution ▾]` | `[1 ▴▾]` | 4210 tris · 3 sel |
| `body_geo` | `[Geometry ▾]` | disabled | 812 tris |

Requirements:

1. Editors are per-row widgets via `setItemWidget`. They are **recreated only when the set
   of LOD nodes changes**; when the set is unchanged, existing rows are updated in place.
   Rebuilding widgets on every refresh would make marquee selection cost panel rebuilds and
   regress `dock_refresh_cost.py`.
2. An editor's signal writes to **the node of its own row**, resolved from the item's
   `UserRole` data. Today `_on_lod_controls_changed` stamps `_selected_lod_transform()`;
   reusing that under inline editing would write properties into the wrong LOD whenever the
   edited row is not the selected one.
3. `Res` is disabled for LOD types with `has_resolution == False`, and shows the type's
   `default_resolution`.
4. The `DayZ LOD` checkbox is replaced by a **Mark Selection as LOD** button in the button
   row and an **Unmark** entry in the row context menu. `assign_lod_to_selection` and
   `_remove_lod_from_selection` keep their current behaviour.
5. Marking a mesh must not rename it — `_mark_selection_as_lod` already documents why, and
   the inline editors must not reintroduce a rename.
6. Rows are keyed by node, never by label. A scene can hold three distinct nodes all
   reading "Resolution 1".

`_selected_lod_definition()` and `lod_resolution_value()` on the dock are consumed by
`actions/lod.py` for the Add-LOD path. They stay, backed by the row editors of the current
row, so `create_lod_type` and `assign_lod_to_selection` keep working unchanged.

## Section 2 — Auto LOD moves into export

The `Auto LOD` dock section and the `Auto LOD` Quick Actions button are removed.

### Option box

The export half of `mayaObjectBuilderP3DOptions.mel` gains a frame **Auto LOD (generated on
export)**, collapsed by default, holding the fields that `auto_lod_settings()` already
returns, plus a master checkbox:

| Key | Control | Default |
|-----|---------|---------|
| `autoLod` | master checkbox | `0` |
| `autoLodOutput` | Quads / Triangles | `quads` |
| `autoLodReduction` | Aggressive / Balanced / Light | `aggressive` |
| `autoLodFirst` | LOD1 / LOD0 | `LOD1` |
| `autoLodResolution` | checkbox | `1` |
| `autoLodGeometry` | checkbox | `1` |
| `autoLodMemory` | checkbox | `0` |
| `autoLodFire` | checkbox | `0` |
| `autoLodView` | checkbox | `0` |
| `autoLodGeometryType` | BOX / NONE | `BOX` |
| `autoLodFireQuality` | 1–10 | `2` |

Menu values need entries in `mayaObjectBuilderP3DMenuLabelToValue` and its inverse.

### Export path

**Auto LOD pairs with Export Selection.** Generating from one selected mesh and then writing
the *whole scene* is incoherent where several models share a scene — the measured one holds
six garments. Both access modes stay supported, since a single-model scene may reasonably
use Export All, but Export Selection is the coherent pairing and the dock offers it as a
first-class choice. See `2026-07-20-menu-and-dock-presentation-design.md`, which also fixes
the `defaultFileExportActiveType` optionVar that `entry.export_p3d` never set.

`translator.do_write`, when `autoLod=1`:

1. Resolve exactly one source mesh from the selection. Zero or more than one is an error
   with a plain message, and **no file is written**. This holds under both access modes —
   the source is the selection either way; only the written scope differs.
2. Suspend undo for the whole generate/export/cleanup span. Without it, Ctrl+Z after an
   export resurrects nodes that were deliberately removed.
3. Generate, export, then delete everything generated — in `finally`, so a cancel or an
   exception leaves the scene as it was and no partial file behind.

### The non-consuming refactor

`generate_auto_lods` **consumes its source**: `_generate_resolution_lods` does
`cmds.rename(source, name)` for index 0, so the user's mesh becomes LOD1, is marked as a
LOD, and is reparented under `visuals`. Transient generation is impossible while that
stands — the source is one of the nodes that would be deleted.

The rename is removed. Index 0 duplicates the source like every other index and calls
`_propagate_named_selections(source, duplicate, full_resolution=True)`. That path already
exists and carries both object-level and component-level sets; every a3ob set carries
`a3obSelectionName`, which is what the propagation filters on and what the dock's
`_selections_snapshot` relies on.

Rolling the scene back with `cmds.undo()` instead was considered and rejected:
`MFnSet.create` and `a3obFindComponents` never enter the undo queue, so the rollback would
leave orphan sets behind.

### Carrying the skin across — measured, not assumed

A duplicate of a skinned mesh **has no skinCluster**. Since a live skinCluster is what
export prefers, the duplicated LOD1 must be re-bound, and the re-bind must be exact.

Measured on `Own_Dreykrus.mb` (`jacket`: 6892 verts, 25 influences, 172300 weights):

| Method | Max abs deviation | Verts past the 1/254 encodable step |
|--------|-------------------|-------------------------------------|
| `cmds.copySkinWeights`, `closestPoint` / `oneToOne` | **0.1027** | 5 |
| `MFnSkinCluster.setWeights` with the raw source array | **0.0** | 0 |

`copySkinWeights` is not exact even on geometry duplicated from the source — coincident
points make `closestPoint` association pick arbitrarily. It must not be used here.

The required sequence is therefore: duplicate → `cmds.skinCluster(influences, dup,
toSelectedBones=True)` → read the source array with `MFnSkinCluster.getWeights` → write it
onto the duplicate with `setWeights` over a complete vertex component. A duplicate has
identical vertex order, so index *i* maps to index *i* and no association step is needed.

`duplicate(upstreamNodes=True)` is not an option — it would clone the skeleton.

### Layering

Undo suspension lives in `ui/_undo.py`, and `mayabridge` must not depend on `ui`. The
helper moves to `mayabridge/undoctl.py`; `ui/_undo.py` re-exports it so no caller changes.

## Section 3 — optional texture import

A checkbox **Import Textures (.paa decode)** joins the `Import: Data` frame, key
`importTextures`, default `1`. `translator.do_read` schedules
`evalDeferred(assign_pending_textures)` only when it is enabled; everything else about the
import is unaffected.

## Testing

Pure-Python (`tests/python/`, no Maya):

- `parse_options` / `option_enabled` over the new keys, including defaults when a key is
  absent: `autoLod` off, `importTextures` on.
- Unknown keys in an options string are still ignored, so option strings saved by an older
  version keep loading.

`mayapy`:

- Import with `importTextures=0` creates no `file` nodes; with `importTextures=1` it does.
- Export with `autoLod=1` writes the expected LOD count **and leaves the scene with the
  same transform count, the same node names, and the same objectSet membership as before
  the export**. This is the assertion that makes "scene unchanged" real rather than
  claimed.
- Export with `autoLod=1` and a selection of zero or two meshes writes no file.
- A cancel mid-decimation leaves the scene unchanged and writes no file.
- The non-consuming generator still produces the LOD stack the consuming one did:
  same LOD count, same types, same resolutions, same selections on LOD1.

Regression gates that must not move:

- `mayapy tests/golden.py verify` — the byte contract is untouched by this work.
- `dock_refresh_cost.py` — the `QTreeWidget` migration must not add rebuilds to component
  picking.
- `dock_panel_sync.py` — panel refresh must stay silent, with its positive control intact.

## Adjacent work, deliberately not addressed

### The unwired option keys

`translator.py` reads nine option keys. The option box offers thirty-two. These twenty-three
are stubs for features not yet built — the UI presents choices that change nothing:

`enclose`, `groupBy`, `absolutePaths`, `additionalData`, `customNormals`,
`flags`, `namedProperties`, `vertexMass`, `selections`, `uvSets`, `materials`, `sections`,
`translateSelections`, `cleanupSelections`, `proxyAction`, `relativePaths`, `sortSections`,
`collisions`, `warningsAreErrors`, `renumberComponents`, `forceLowercase`,
`exportTranslateSelections`, `preserveNormals`.

They stay. Until each is wired, no work may assume it has an effect, and the new Auto LOD
and texture keys must not be modelled on them — those two are wired from day one.

### Weight storage is its own design problem

Measured on `Own_Dreykrus.mb`, `a3obBakedWeights` holds 1 429 194 characters across six
garments — 24.3 characters per weight entry, storing full float precision for a value the
P3D encodes in **one byte** at a 1/254 step. The same data as `uint16` vertex + `uint8`
weight is roughly 180 KB. Two representations (live `skinCluster`, baked string) can also
silently disagree, which is why `a3obBakedWeightsPrevious` and the restore-swap exist.

Reworking that storage touches a hard contract and is not UI simplification. It gets its
own spec; nothing in this one changes the bake format. Note for that spec: the P3D
representation is name → list of `(vertex, weight)` — structurally identical to a Blender
vertex group. Maya lacks a native per-component-weighted set, which is the whole reason
the string attribute exists.
