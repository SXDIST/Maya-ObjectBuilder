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
| The 23 inert option-box controls | Out of scope this round — see Known debt |

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

`translator.do_write`, when `autoLod=1`:

1. Resolve exactly one source mesh from the selection. Zero or more than one is an error
   with a plain message, and **no file is written**.
2. Suspend undo for the whole generate/export/cleanup span. Without it, Ctrl+Z after an
   export resurrects nodes that were deliberately removed.
3. Generate, export, then delete everything generated — in `finally`, so a cancel or an
   exception leaves the scene as it was and no partial file behind.

### The blocking refactor

`generate_auto_lods` **consumes its source**: `_generate_resolution_lods` does
`cmds.rename(source, name)` for index 0, so the user's mesh becomes LOD1, is marked as a
LOD, and is reparented under `visuals`. Transient generation is therefore impossible
without changing this — the source is one of the nodes that would be deleted.

The generator must become non-consuming: index 0 duplicates the source like every other
index and calls `_propagate_named_selections(source, duplicate, full_resolution=True)`.
That path already exists and already carries both object-level and component-level sets;
every a3ob set carries `a3obSelectionName`, which is what the propagation filters on and
what the dock's `_selections_snapshot` relies on.

**Open risk, must be measured before implementing.** Today LOD1 *is* the source, so it
carries the live `skinCluster`. A duplicate does not. Per the export contract a live
skinCluster always wins and export otherwise falls back to `a3obBakedWeights` — a transform
attribute, which duplication does copy. So a duplicated LOD1 exports from the bake, and on
an unbaked garment the weights differ from today's output. Clothing is the stated primary
use case, so this is not hypothetical.

The implementation plan must open with a `mayapy` measurement on a skinned garment:
export byte counts and weight TAGGs from the consuming path versus the duplicating path.
If they diverge, the duplicate must carry weights across (`copySkinWeights` onto a fresh
bind, not `duplicate(upstreamNodes=True)`, which would clone the skeleton) before the rest
of Section 2 proceeds.

Rolling the scene back with `cmds.undo()` instead was considered and rejected:
`MFnSet.create` and `a3obFindComponents` never enter the undo queue, so the rollback would
leave orphan sets behind.

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

## Known debt, deliberately not addressed

`translator.py` reads nine option keys. The option box offers thirty-two. These twenty-three
are inert — the UI presents choices that change nothing:

`enclose`, `groupBy`, `absolutePaths`, `additionalData`, `customNormals`,
`flags`, `namedProperties`, `vertexMass`, `selections`, `uvSets`, `materials`, `sections`,
`translateSelections`, `cleanupSelections`, `proxyAction`, `relativePaths`, `sortSections`,
`collisions`, `warningsAreErrors`, `renumberComponents`, `forceLowercase`,
`exportTranslateSelections`, `preserveNormals`.

Removing them is the single largest simplification available and is left for a follow-up.
Until then, no new work should assume any of them has an effect.
