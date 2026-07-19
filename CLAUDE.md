# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Maya 2027 plugin (`MayaObjectBuilder`) for DayZ/Object Builder P3D workflows, written in **pure Python** (Maya Python API 2.0, with a tiny API‑1.0 shell for the file translator). There is no compilation step — edit the Python and reload. The Blender add‑on under `Arma3ObjectBuilder-master/` is a format/compatibility reference only (gitignored, clone from https://github.com/MrClock8163/Arma3ObjectBuilder); do not edit it.

The plugin was ported 1:1 from a former C++ `.mll`. Command names, flags and the on‑scene `a3ob*` attribute schema are preserved, so existing scenes keep round‑tripping.

## Common commands

Run from the repository root.

```bash
# Register this repo as a Maya module (edit-in-place, no copy). Run inside Maya/mayapy:
#   import sys; sys.path.insert(0, r"<repo>/tools"); import dev_install; dev_install.install()
# or headless to just write the .mod:
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" -c "import maya.standalone as s; s.initialize(); import sys; sys.path.insert(0,'tools'); import dev_install; dev_install.install(load=False)"

# Pure-Python format tests (no Maya)
python tests/python/test_p3d_roundtrip.py
python tests/python/test_model_cfg.py
python tests/python/test_paa.py          # PAA decoder; skips cleanly if tests/paa/*.paa are absent
python tests/python/test_skinweights.py  # skin-weight outlier detection (pure math)
python tests/python/test_qem.py          # QEM decimation invariants (no orphan vertices)
python tests/python/test_influences.py   # influence name masks + never-strip-the-last rule

# Python syntax checks (compile every .py that exists on disk — robust to package renames)
python -m py_compile $(find scripts plug-ins tests -name '*.py')

# Maya workflow tests (load the plugin, exercise import/export + commands + UI)
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/p3d_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/model_cfg_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_weights_workflow.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/skin_transfer.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_survive_skeleton.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weight_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_undo.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/command_correctness.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_uses_live_mesh.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/scene_watch.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/plugin_teardown.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/influence_panel.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_refresh_cost.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/dock_panel_sync.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/lod_naming.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/material_faces.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/weights_restore.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/export_selection_scope.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/autolod_properties.py
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/mayapy/sharp_edges_follow_normals.py

# Package release archive (plain file copy + zip, no build)
powershell -ExecutionPolicy Bypass -File tools/package_release.ps1 -Version 0.1.0
```

Full validation after code changes: the `tests/python` tests → `py_compile` → the `tests/mayapy` workflows.

## High-level architecture

Two layers, split by whether they need Maya:

- **`scripts/a3ob/formats/`** — Maya-independent file format code, unit-testable with a plain
  system Python interpreter. `binary.py` (little-endian reader/writer), `p3d.py` (MLOD/LOD/TAGG,
  the `LodResolution` signature codec, coordinate + UV conventions), `model_cfg.py` (`model.cfg`
  parser/writer), `paa.py` (DayZ `.paa` texture decoder — DXT1/DXT5 + LZO1X, with numpy/`python-lzo`
  fast paths and pure-Python fallbacks), `rvmat.py` (`.rvmat` material-config parser).
- **`scripts/a3ob/mayabridge/`** — the Maya glue (`maya.api.OpenMaya` = API 2.0). `attributes.py`
  (the single `a3ob*` attribute schema + helpers); `import_/` and `export/` packages (Maya DAG ↔ MLOD
  conversion — `import_/{convert/,builders,importer}` where `convert/` is itself a package
  (`mesh`, `names`); `export/{parse,taggs/,exporter}` where `taggs/` is a package
  (`data`, `lodexport`, `memory`); `mesh_import.py`/`mesh_export.py` are kept as re-export facades);
  `commands/` package (one module per `a3ob*` `MPxCommand` + a shared `helpers/` package —
  `base`, `geometry`, `primitives`, `scene`, `sets`; `__init__` re-exports the classes and the
  `COMMANDS` list); `model_cfg_commands.py` (skeleton import/export); `translator.py` (import/export
  bodies + option parsing); `paatex/` package (resolve/decode/cache DayZ `.paa` textures and wire
  them onto Maya materials — `settings`, `resolve`, `decode`, `channels`, `materials`; `__init__`
  re-exports the public API).

- **`scripts/a3ob/ui/`** — the dock UI package (split from the former `objectBuilderMenu.py`
  monolith). `_qt.py` (guarded PySide6/shiboken/OpenMayaUI import layer), `widgets.py` (Qt helpers +
  `_CollapsibleSection`), `dock.py` (`MayaObjectBuilderDock` widget, assembled from the panel
  mixins), `panels/` package (one mixin per dock section — `lod`, `lod_list`, `metadata`,
  `named_properties`, `materials`, `selections`, `skinning`, `validation`), `actions/` package (action wrappers +
  scene business logic by domain — `files`, `lod`, `materials`, `memory`, `metadata`, `named`,
  `selections`, `_common`), `entry.py` (menu/dock lifecycle/install + singletons), `constants.py`
  (pure data tables), `recent.py` (recent-path history backing store), `scene/` package (Qt-free scene
  helpers by domain: attrs/lods/selections/materials/memory), `autolod/` package (auto-LOD
  generators). The `actions ↔ entry ↔ dock` cycle is broken by a lazy dock import inside
  `entry._build_qt_dock`; `objectBuilderMenu.py` is a thin facade re-exporting everything the plugin
  and the runpy-based mayapy tests reach.

- **`plug-ins/MayaObjectBuilder.py`** — the main scripted plugin (API 2.0). Registers the seventeen
  `a3ob*` commands (`_ALL_COMMANDS` = the fifteen in `commands/` plus the two in
  `model_cfg_commands.py`), sources the MEL option box, opens the Python dock UI, and
  loads/unloads the companion translator plugin.
- **`plug-ins/MayaObjectBuilderTranslator.py`** — companion plugin (API 1.0). Registers the
  `Arma P3D` `MPxFileTranslator` and delegates all work to `a3ob.mayabridge.translator`.
  `MPxFileTranslator` exists only in API 1.0, while the commands need API 2.0, so the two cannot
  register from a single plugin — hence the split. The main plugin auto-loads this one, so users
  deal with a single "MayaObjectBuilder" plugin.
- **`scripts/objectBuilderMenu.py`** — thin facade over the `a3ob.ui` package (see above), kept so
  the plugin and the runpy-based mayapy tests keep importing UI names from this path.
- **`scripts/objectBuilderAutoLOD.py`** — facade over `a3ob.ui.autolod` (auto-LOD generator).
- **`scripts/mayaObjectBuilderP3DOptions.mel`** — Maya File > Import/Export option box.
- **`tools/`** — developer-only tooling, deliberately OUTSIDE `scripts/` (which is on both
  `PYTHONPATH` and `MAYA_SCRIPT_PATH`, so anything there is importable in every Maya session).
  `tools/dev_install.py` writes `Documents/maya/modules/MayaObjectBuilder.mod` pointing at this repo
  (edit-in-place local install); `tools/launch_maya_debug.ps1` and `tools/package_release.ps1` are
  the debug-launch and release-packaging scripts. `install/` holds the drag-into-Maya end-user
  installer. Nothing in `tools/` ships in a release.
- `tests/python/` — pure-Python format tests. `tests/mayapy/` — Maya integration workflows.

## Installation model

- **Local dev:** `tools/dev_install.py` writes a `.mod` in `Documents/maya/modules/` whose module
  root is this repo, so Maya loads `plug-ins/` and `scripts/` from here with no copy. A committed
  `MayaObjectBuilder.mod` (root `.`) also makes the repo a drop-in module on `MAYA_MODULE_PATH`.
- **End users:** drag `install/mayaObjectBuilderInstall.py` into Maya. It copies `plug-ins/` +
  `scripts/` into `Documents/maya/MayaObjectBuilder/`, writes the `.mod`, and loads with autoload.

## Key task entry points

| Task | Primary files/functions |
|------|--------------------------|
| P3D export | `scripts/a3ob/mayabridge/export/` (`exporter.py` `_export_mesh_lod()`; `taggs/data.py` TAGG builders, `taggs/lodexport.py` per-LOD assembly, `taggs/memory.py` locators) |
| P3D import | `scripts/a3ob/mayabridge/import_/` (`importer.py` `MayaMeshImport`, `convert/mesh.py` `apply_uvs()`/`apply_normals()`, `convert/names.py` naming/serializers, `builders.py` object sets) |
| P3D binary format | `scripts/a3ob/formats/p3d.py`, especially `LOD.read/write`, the `*TaggData` classes, `LodResolution` |
| P3D translator | `scripts/a3ob/mayabridge/translator.py` (`do_read`/`do_write`) + `plug-ins/MayaObjectBuilderTranslator.py` |
| `a3ob*` commands | `scripts/a3ob/mayabridge/commands/` (one module per command; `ValidateCommand` in `validate.py`, `closed_face_islands()` in `helpers/geometry.py`); `__init__` exports `COMMANDS` |
| PAA texture decode | `scripts/a3ob/formats/paa.py` (`decode_largest_mip()`, `PAA_File`, DXT1/DXT5 + `lzo1x_decompress`) |
| `.rvmat` parsing | `scripts/a3ob/formats/rvmat.py` (`parse_rvmat_file()`) |
| Texture → material wiring | `scripts/a3ob/mayabridge/paatex/` (`materials.assign_paa_texture()`/`assign_pending_textures()`/`preferred_shader_type()`, `resolve.resolve_paa_path()`, `decode.decode_normal_png()`/`decode_smdi_png()`) |
| Texture root / alpha UI | `scripts/a3ob/ui/panels/materials.py`; menu entry via `scripts/a3ob/ui/entry.py` |
| `model.cfg` | `scripts/a3ob/formats/model_cfg.py` and `scripts/a3ob/mayabridge/model_cfg_commands.py` |
| Skin weights (rig) | `scripts/a3ob/mayabridge/skinweights.py` (Maya-free outlier math + bake format), `commands/skin.py` — **detection reports only**, repair is Maya's `Skin > Smooth Skin Weights` |
| Weight transfer from body | `scripts/a3ob/mayabridge/skintransfer.py` (`transfer_to_target()`, `check_alignment()`, `ensure_reference()`, rigid far shells), command `a3obTransferSkin`, dock panel `ui/panels/skinning.py` |
| Influence list / removal | `scripts/a3ob/mayabridge/influences.py` (Maya-free masks + removability), command `a3obInfluence` in `commands/influence.py` (`vertices_driven_by()`, `remove_influences()`, `set_paint_influence()`), dock section in `ui/panels/skinning.py` |
| Stored weights kept current | `scripts/a3ob/mayabridge/weightsync.py` (`sync_all_lods()` on `kBeforeSave`; `install()`/`uninstall()` from the plugin's `initializePlugin`/`uninitializePlugin`) |
| Pose testing / bind pose | `scripts/a3ob/mayabridge/posetest.py` (`find_spikes()`, `skeleton_is_posed()`), command `a3obTestPose`; bind-pose check runs inside `a3obValidate` |
| Reference assets (body/skeleton) | `scripts/a3ob/mayabridge/references.py` — saved as `.ma` under `Documents/maya/MayaObjectBuilder/references/`, paths in optionVars; command `a3obReference` |
| Import/export progress + cancel | `scripts/a3ob/mayabridge/progress.py` (`Progress`) — wraps API-1.0 `MComputation` |
| Dock scene notifications | `scripts/a3ob/ui/watch.py` (`SceneWatcher`) — Maya callbacks, NOT polling |
| Attribute schema | `scripts/a3ob/mayabridge/attributes.py` (long+short `a3ob*` names) |
| UI dock/menu | `scripts/a3ob/ui/dock.py` (`MayaObjectBuilderDock`), `entry.py` (`show_plugin_ui()`); `objectBuilderMenu.py` is a facade |
| Command registration | `plug-ins/MayaObjectBuilder.py`, `initializePlugin()` / `uninitializePlugin()` |
| Format reference | `Arma3ObjectBuilder-master/Arma3ObjectBuilder/io/{data_p3d,data_paa,compression}.py` (read-only) |

## Port-specific gotchas (Maya Python API differences vs the former C++)

- `MPxFileTranslator` is API‑1.0 only → the translator lives in the companion plugin (above).
- `MComputation` is **also API‑1.0 only** — `maya.api.OpenMaya` has no equivalent despite the
  devkit shipping the C++ header. `mayabridge/progress.py` imports it from `maya.OpenMaya` and
  degrades to a no-op when unavailable. devKit documents the C++ API; the 2.0 Python bindings
  do not cover all of it, so verify a class exists before designing around it.
- `MFnSet.getMembers()` returns an `MSelectionList`, which holds only ONE component type per
  DAG path: for a set containing both vertices and faces of the same mesh it returns the
  vertices and **silently drops every face** (measured: 1250 faces became 0). Selection
  membership is therefore listed with `cmds.sets(query=True)`; only the ownership test uses
  the API (`export/parse.py` `_read_set_components`).
- `MMeshIntersector.create(node, matrix)` does NOT accept world-space points alongside the
  matrix — points must be in the mesh's own object space. Passing world points returned 1.009
  where the true distance was 0.0186 (`skintransfer.shell_distances`).
- `om.MGlobal` is an immutable type: it cannot be monkey-patched in tests. Functions that warn
  should also RETURN what they found (`exporter._warn_about_missing_weights`).
- Undo: `_UndoableBase` (`commands/helpers/base.py`) routes changes through an `MDagModifier`.
  Once a command declares itself undoable, EVERY change it makes must go through that
  modifier — a `cmds.createNode` inside such a command survives Ctrl+Z, leaving orphans.
  Commands that build objectSets instead stay non-undoable and wrap their body in
  `undo_chunk()` so `cmds` records collapse into one user-visible step. `MFnSet.create()` never
  enters the undo queue at all — sets are created with `cmds.sets`.
- Weights live in the `skinCluster`, which Maya deletes together with the joints: deleting a
  skeleton destroys every weight. `a3obBakeSkin` copies them onto the LOD transform
  (`a3obBakedWeights`) and export falls back to them; the live skinCluster always wins.
  That copy is now also written by **import** (`import_/convert/mesh.py`
  `_store_weight_selections`, indices in MAYA space) and refreshed on every **scene save**
  (`weightsync.py`) — so a `.p3d` opened without its rig still exports its weights. Sync
  happens on save, never on export: export must not silently mutate the user's scene.
- The saved reference asset carries its **own skeleton**, so `skintransfer.ensure_reference()`
  imports it and *keeps* it. Importing it, transferring, and deleting it again was the obvious
  design and it is wrong: the garment binds to exactly those joints, so removing them takes the
  skinCluster and every transferred weight with it. Editing weights and `a3obTestPose` need the
  joints present anyway.
- A `@contextlib.contextmanager` must not `yield` inside a `try` that swallows the exception
  type its caller can raise: the caller's exception is thrown back in at the `yield`, and
  falling through to a second `yield` turns it into `RuntimeError: generator didn't stop after
  throw()`, masking the real error. This is why `ensure_reference` is a plain function.
- Export reads the DEFORMED mesh, so exporting a posed rig bakes the pose into the `.p3d`.
  `a3obValidate` warns via `posetest.skeleton_is_posed()`, which compares each joint against
  the skinCluster's `bindPreMatrix` (the joint's own `.bindPose` attribute does NOT work).
  `bindPreMatrix` is a **sparse multi** indexed by `.matrix[]` LOGICAL indices, which do NOT
  compact when an influence is removed — `enumerate(influences)` is the wrong index and made
  `skeleton_is_posed()` report joints on a rig nobody had moved. Measured: after removing two
  middle influences, `bindPreMatrix` kept `[0,1,2,3]` while `.matrix` held `[1,3]`. Use
  `cmds.getAttr(skin + ".matrix", multiIndices=True)`. Removing a TRAILING influence does not
  reproduce it, which is why a naive test passes.
- Removing a skin influence never deletes its weight — every vertex must sum to 1.0, so the
  weight moves to the influences still on that vertex, in the ratio they already carried.
  `weightDistribution` does NOT govern that: `removeInfluence` measured identical under both
  settings. It governs a subsequent PAINT stroke — flooding an influence to zero on a sleeve
  whose neighbours are pure `Elbow` gave `Shoulder 0.76 / Elbow 0.24` under **Distance** and
  `Elbow 1.0` under **Neighbors**. Transfers and removals set Neighbors for the rigger's later
  painting, not to change what removal itself does.
- `a3obProxy` / `a3obUpdateProxy` build objectSets, so they are NON-undoable + `undo_chunk()`
  like the other set-building commands. They were `_UndoableBase` and left an orphan
  `a3ob_proxy_*` set behind after Ctrl+Z — objectSets cannot go through an `MDagModifier`, so
  the undoable shape is simply the wrong one for them.
- `MSyntax.addFlag` accepts only ONE argument type per flag; the long flag name `set` is reserved.
  `a3obNamedProperty -set` therefore takes a single `"key=value"` string and its long alias is
  `-setproperty` (short `-s` unchanged). The long name `fix` is reserved the same way — `addFlag`
  raises "Unexpected Internal Failure" and the interpreter dies at command dispatch, so
  `a3obSkinWeights` uses `-repair` (short `-r`). Maya builds a command's syntax lazily, on
  its FIRST dispatch, from a C++ callback that cannot absorb a Python exception — so such a
  flag kills the session and loses unsaved work. `initializePlugin` therefore calls every
  `syntax()` up front (`_syntax_is_safe`) and skips the offending command instead.
- Selecting from API 2.0 is `MGlobal.setActiveSelectionList(list, MGlobal.kReplaceList)`;
  `MGlobal.select` does not exist there.
- `cmds.polyNormalPerVertex` **segfaults Maya** — no exception, the session dies and takes
  unsaved work with it — on a decimated mesh with nonmanifold topology or lamina faces.
  `polyCleanupArgList` does NOT reliably prevent it (it leaves nonmanifold vertices behind).
  `a3ob.ui.autolod` therefore skips the normal pass on meshes with locked normals and lets
  `polySoftEdge` do the work. Note also that `freezeNormal=False` is **not** an unfreeze —
  only `unFreezeNormal=True` clears locked normals (measured: 1560 locked before and after).
- The QEM decimator (`ui/autolod/qem.py`) must never emit a vertex that no surviving face
  references: such a point has no normal and is what triggers the segfault above. A vertex
  stays `alive_v` after its last face collapses into a degenerate one, so aliveness is not
  the same as being used — `tests/python/test_qem.py` guards the invariant.
- Debugging a Maya hard crash: reproduce it under `mayapy` (exit 139 = segfault), then
  bisect by wrapping the suspect helpers with flushed print markers. The process dies
  without a traceback, so the last flushed line IS the stack trace. Patch the names on the
  module that CALLS them (`lodgen`), not where they are defined — `helpers` is star-imported,
  which binds copies into the caller's namespace.
- The dock rebuilds every panel from the selected LOD, and that scans every objectSet in the
  scene. `SelectionChanged` fires per marquee-drag step, so `entry._schedule_context_refresh`
  debounces it and `_refresh_context_ui(force=False)` drops the work when the selected LOD is
  unchanged — component picking on a dense mesh must cost zero rebuilds
  (`tests/mayapy/dock_refresh_cost.py` guards this).
- **Smoothing lives in two places and NEITHER may be trusted alone** (`export/taggs/data.py`
  `_edge_splits_the_shading()`). Maya has the per-edge soft/hard flag AND locked custom
  per-face-vertex normals; each can be the only one holding the truth:
  * With **locked** normals the normals win. A DayZ jacket that came in through FBX had
    38131 edges, every one flagged hard and none soft, next to 40812 locked normals that
    were smooth. Trusting the flag wrote "smooth normals AND every edge sharp" into one LOD,
    and Object Builder — which recomputes normals from `#SharpEdges#` — showed it faceted.
  * With **unlocked** normals the flag is all there is. Hardening an edge by hand does NOT
    touch the stored normals: on a softened sphere with ten hand-hardened edges,
    `getNormals`/`getNormalIds` (what export writes) and `getFaceVertexNormal` both reported
    ZERO differing corners — measured under mayapy AND under interactive Maya. Deciding by
    normals alone silently dropped every hand-set crease.
  So: `MFnMesh.isNormalLocked(normalId)` picks which mechanism to believe, per edge. Border
  edges (<2 faces) split no shading and are never written; nonmanifold edges (>2) keep the
  flag. Note `getFaceVertexNormal()` returns the SHARED/averaged normal — it is not the
  per-corner value; use `getNormalIds()` into `getNormals()`, as the exporter itself does.
- The round-trip guard for this is a COUNT, not `> 0`. `export_uses_live_mesh.py` asserted
  only that some sharp edges survived, which hid a 19x inflation for a long time: the
  `sample_1_character.p3d` fixture carries 2004 sharp edges and export wrote 38871.
- A LOD **resolution signature is not a named property**. `1.000e+13` is the float in a
  Geometry LOD's resolution field that encodes its type; the Blender add-on mentions the
  string once, as a key in its signature → LOD type table (`io/data_p3d.py`). Auto LOD had
  ported that table entry into `_set_named_properties(node, (("lod", "1.000e+13"),))`, so
  every generated Geometry LOD showed a junk `lod` row in Object Builder's Named Properties
  — the same port artifact as the `autocenter=0` one removed before it. When something in
  `autolod/` looks like a magic Arma constant, check whether the reference treats it as data
  or as a *lookup key*.
- Export resolves a selected node to LODs **upward first, then downward**
  (`export/parse.py` `resolve_lod_paths()`). Upward only — the original — meant selecting the
  folder that holds a model's LODs resolved to nothing and failed with "selection does not
  contain an Object Builder LOD", so a folder per model, the obvious way to keep several
  models bound for separate `.p3d` files apart, was the one layout that could not be
  exported. A mesh still resolves to its own LOD, never its siblings.
- An **empty LOD exports fine** — `Add LOD` makes a marked transform with no mesh and that
  writes a valid (empty) LOD. What fails is a plain Maya group: no `a3obIsLOD`, so it is not
  a LOD at all. Note `_find_first_mesh_path()` only looks a child and a grandchild deep — a
  mesh nested deeper under a LOD is silently not exported.
- `a3obBakedWeights` is an **export fallback, and now also restorable**:
  `a3obBakeSkin -restore` writes it back onto the live skinCluster, matching bones by leaf
  name and renormalizing (a baked bone the rig lacks would otherwise leave rows summing to
  <1 for Maya to redistribute silently). It writes the whole array through
  `MFnSkinCluster.setWeights` — ~50k non-zero entries on a real garment, where per-vertex
  `skinPercent` takes minutes — so it does NOT enter the undo queue. Instead it stashes the
  weights it replaces in `a3obBakedWeightsPrevious`, which makes `-restore -previous` a swap.
- **Nothing may overwrite `a3obBakedWeights` without keeping the old copy**
  (`weightsync.store_bake()`). Sync-on-save refreshes from whatever skinCluster is live, and
  after a re-bind that is a fresh bind's defaults — which silently destroyed a good bake. A
  fresh bind is indistinguishable from any other rig, so there is no honest heuristic; the
  previous value is simply always kept. Note `store_bake` skips a write whose text it already
  holds, which is why the restore path writes the previous slot DIRECTLY — going through
  `store_bake` left the overwritten weights unreachable.
- The Selections panel keys on an **owner**, not strictly a LOD (`_owner_node_for_set()` /
  `_selected_selection_owner()`): a set made on a mesh nobody has marked yet belongs to that
  mesh. Requiring a LOD meant such a set existed in the scene and exported fine while
  appearing in no panel, which reads as "my selection was not created".
- Marking a mesh as a LOD must NOT rename it. `_mark_selection_as_lod()` passes `name` to
  `a3obCreateLOD`, which honours it only for a brand-new node, so an empty LOD is still
  "Resolution_1" while an existing mesh keeps the name its author gave it. Renaming the
  marked mesh to the LOD name was shipped and reverted: "helmet" became "Resolution_1", and
  marking a second mesh of the same type collided into a suffix
  (`tests/mayapy/lod_naming.py`). Note `autolod/helpers/meshops.py` has its own unrelated
  `_mark_lod(transform, lod_type, resolution)` — different signature, do not conflate them.
- A LOD's identity is its **node**, never `_lod_name_from_transform()`. That label is a type
  name and collides constantly: a measured scene had `|helmet`, `|group1|body|Resolution_2`
  and `|group1|body|Resolution_1` all reading "Resolution 1", so the Selections panel — which
  filtered by label — showed every one of them the other two's sets, and `lod_overview()`
  counted the same sets three times. Use `_lod_node_for_set()` / `selection_sets_for_lod()`.
- Panels are refreshed on every `SelectionChanged`, so anything they call must be a SILENT
  query. `a3obInfluence` warned "select a skinned mesh first" from the dock's own refresh,
  which turned clicking any unrelated prop into Script Editor spam. The gate is "no acting
  flag set" (`-sv`/`-ri`), NOT `isFlagSet("-li")`: measured, `-li` answered True under mayapy
  and False under interactive Maya for the identical `a3obInfluence(listInfluences=True)`
  call, so gating on it silences the tests and leaves the real session as noisy as before.
- **A registered `MPxCommand` does not pick up code changes on plugin reload.**
  `unloadPlugin` + purging every `a3ob*` module from `sys.modules` + `loadPlugin` genuinely
  refreshes the plain modules — dock panel behaviour changed live and the plugin re-imported
  all 86 modules — but the command classes kept executing the session's FIRST version:
  monkey-patching `InfluenceCommand.doIt` (which works under mayapy) never fired, and the old
  warning kept coming out of code that no longer exists on disk. Verify command changes under
  `mayapy`; a running Maya needs a restart before it will run them.
- Asserting that something stays SILENT needs a positive control in the same test, or it
  passes vacuously the moment the listener stops working. `MCommandMessage.addCommandOutputCallback`
  (API 1.0) does hear `MGlobal.displayWarning` under mayapy — `tests/mayapy/dock_panel_sync.py`
  proves that with an acting-flag call before it asserts the query says nothing.
- Weight cleanup belongs to Maya (`Skin > Smooth Skin Weights` / `Prune Small Weights`), not
  to this plugin: `a3obSkinWeights` finds and selects suspect vertices and writes nothing.
- Under `mayapy` standalone, `MPxCommand.setResult` values come back from `cmds` as a 1-element
  list (unlike the C++ scalar). Consumers (`objectBuilderMenu`, `objectBuilderAutoLOD`, the workflow
  tests) unwrap `[name] -> name`.
- `cmds.createNode(..., skipSelect=True)` is used where an active component selection must survive
  (the C++ used `MDagModifier`, which did not change selection).
- Material shaders and texture `file` nodes are made with `cmds.createNode(...)` (not `shadingNode`,
  which returns `None` during File > Import). The shader type is chosen by
  `paatex.preferred_shader_type()` — `aiStandardSurface` when Arnold (`mtoa`) is loaded, else `blinn`,
  else `lambert`.
- Node names are scrubbed to `[A-Za-z0-9_]` before creation (Maya raises on illegal names during
  File > Import); node names are not part of the P3D export contract.
- Maya can't read `.paa`; textures are decoded to cached PNGs (`a3ob.formats.paa`) and wired as
  `file` nodes. Because File > Import's DG context blocks inline file-node creation/connection,
  `translator.do_read` defers the texturing via
  `cmds.evalDeferred("import a3ob.mayabridge.paatex as _pt; _pt.assign_pending_textures()", lowestPriority=True)`.
- `numpy` and `python-lzo` are optional accelerators for the PAA decoder; both have pure-Python
  fallbacks (`paa.py` picks the fast path at import), so the `formats/` layer stays dependency-free
  for the `tests/python` interpreter.

## P3D format invariants

- P3D faces are triangles or quads only.
- Triangles write 16 bytes of zero padding after vertices; quads do not.
- N-gons are triangulated in `_export_mesh_lod()` through Maya triangle extraction.
- UVs are stored in both face data and the `#UVSet#` TAGG.
- UV V is inverted on write and read as `1 - v`.
- `#UVSet#` TAGG ids are 0-based; id `0` is the primary Object Builder UV set.
- Export reads Maya's active UV set through `MFnMesh.getUVs()` without a set name.
- Axis conversion (an inverse pair, round-trip tested): import P3D core point `(x, y, z)` → Maya
  `(x, z, -y)` (`convert/names.py` `core_to_maya_point`); export Maya `(x, y, z)` → P3D core
  `(x, -z, y)` (`export/parse.py` `maya_to_core_point`). Vectors/normals use the same swap and are
  normalized. Separately, `p3d.py` reads/writes each core vector's three floats in `x, z, y` file
  order (a Y/Z swap at the on-disk layer).
- TAGG structure is `active byte + null-terminated name + uint32 length + data`.

## PAA / texture invariants

- Decoded pixel rows are **bottom-to-top** (OpenGL/MImage convention); `paatex/decode.py`
  `_write_png()` flips them to top-to-bottom on write. A vertical-flip bug (PNGs were upside-down,
  so geometry sampled mirrored rows and the texture "smeared") was fixed by dropping an extra
  `np.flipud`; the cache dir is bumped to `a3ob_paa_cache_v3`. Verified byte-for-byte against the
  game's own `_co.png`.
- Alpha → transparency is **opt-in** (`MayaObjectBuilder_paa_alpha_transparency` optionVar, default
  off) and only applied to genuine bimodal cut-out masks (`_alpha_is_cutout`) — a DayZ `_ca` alpha is
  often a data channel, not a geometry cut-out, so wiring it would make solid armour see-through.
- DayZ `_smdi` channel layout: R unused (constant 1.0), **G = per-texel specular level**,
  **B = glossiness**; wired as G → `specularColor` and `1 - B` → `specularRoughness`. Feeding the raw
  RGB (R=1) blew the surface out with a red-tinted spec.
- `_nohq` is **DXT5nm**: normal.X in alpha, normal.Y in green, Z reconstructed; decoded to a
  tangent-space normal PNG and wired through `aiNormalMap` (Arnold only).
- Texture paths resolve against the texture-root optionVar (`MayaObjectBuilder_texture_root`), then
  `P:/`, then a bounded basename search; `.rvmat` stage textures (via `rvmat.py`) drive the exact
  colour/normal/spec channels, falling back to `_nohq`/`_smdi` siblings of the colour texture.
- DXT decode is numpy-vectorised with a byte-identical pure-Python fallback; LZO has an optional
  `python-lzo` C fast path. `assign_pending_textures()` prefetches every channel decode across a model
  in a `ThreadPoolExecutor` (path resolution + cache dir warmed on the main thread first).

## Maya metadata attributes

| Attribute | Node type | Purpose |
|-----------|-----------|---------|
| `a3obLodType`, `a3obResolution`, `a3obResolutionSignature` | transform | LOD type/resolution metadata |
| `a3obSourceVertices`, `a3obVertexSourceIndices` | transform | Source vertices preserved from import |
| `a3obUVSetTaggs`, `a3obUVSetTaggCount` | transform | Imported UVSet TAGG preservation |
| `a3obSharpEdges`, `a3obHasSharpEdges` | transform | Sharp edge TAGG preservation |
| `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, `a3obFlagValue` | objectSet | Object Builder selections, proxies, and flags |
| `a3obTechnicalSet`, `hiddenInOutliner` | objectSet | Technical set hiding/management |
| `a3obTexture`, `a3obMaterial` | shader | Texture (`.paa`) and `.rvmat` paths; drive the PAA pipeline — resolved against the texture-root optionVar and decoded on import, and the attrs `assign_pending_textures()` scans |
| `a3obSkeletonName` | joint | Skeleton root name (model.cfg) |

Full long+short name schema lives in `scripts/a3ob/mayabridge/attributes.py`. Note: the proxy flag
short name is unified to `a3px` on write; `a3pr` (the legacy import short name) is still read.

## Memory LOD locator workflow

Memory LOD (`a3obLodType = 9`) points are Maya **locators** parented under the Memory LOD transform.
Each locator transform's short name becomes the P3D named selection name.

- **Export** (`_collect_locators_from_memory_lod` in `export/taggs/memory.py`, surfaced through the
  `mesh_export.py` facade): when the Memory LOD has no mesh child but has locator-containing child
  transforms, each is exported as one vertex + one `SelectionTaggData` TAGG. Proxy transforms are
  skipped.
- **Import** (`create_locators_for_memory_lod` in `import_/builders.py`, invoked from
  `import_/importer.py`, surfaced through the `mesh_import.py` facade): single-vertex named selections
  in a face-less Memory LOD are reconstructed as locators; multi-vertex selections become a group.
- **UI**: `add_memory_point()` in `ui/actions/memory.py` (facade `objectBuilderMenu.py`) creates a
  locator under the selected Memory LOD.

## Do not touch without a specific task

- `Arma3ObjectBuilder-master/` — reference only (gitignored; clone if missing).
- `dist/`, `build/` — generated artifacts; installer sources live in `install/` and release
  packaging uses `tools/package_release.ps1`.
- Blender test workflows — require Blender and are not part of the normal validation checklist.
