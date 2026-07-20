# CLAUDE.md

Maya 2027 plugin (`MayaObjectBuilder`) for DayZ/Object Builder P3D workflows. **Pure Python**
(Maya API 2.0, plus a tiny API-1.0 shell for the translator) — no build step, edit and reload.
Ported 1:1 from a former C++ `.mll`, so command names, flags and the `a3ob*` schema are preserved
and existing scenes keep round-tripping.

## Commands

```bash
python tests/run_all.py                # pure-Python + py_compile + mayapy + byte gate
python tests/run_all.py --only python  # no Maya needed
mayapy tests/golden.py verify          # P3D byte contract alone
# Register this repo as a Maya module, from inside Maya:
#   import sys; sys.path.insert(0, r"<repo>/tools"); import dev_install; dev_install.install()
powershell -File tools/package_release.ps1 -Version 0.1.0
```

`mayapy` = `/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe` (override with `--mayapy`/`$MAYAPY`).
Each mayapy test runs in its own process — `maya.standalone` cannot be initialized twice.

## Hard contracts — never change these

1. **P3D bytes** — `formats/{p3d,binary}.py`, all of `mayabridge/export/`. Gate:
   `mayapy tests/golden.py verify`. **Never run `golden.py capture`**: it overwrites the baseline
   and makes the gate vacuous.
2. **The `a3ob*` schema** — long+short names in `mayabridge/attributes.py`. Gate:
   `tests/python/test_attr_schema.py` (33 pairs). A renamed attribute fails no other test; it
   silently stops resolving data in scenes users already have.
3. Registered command names, their flags, and the `Arma P3D` translator name.

Export is deterministic per scene state but **not across provenance**: the same scene exports to
the same byte COUNT but different bytes depending on whether it was freshly imported or
saved-and-reopened (measured 6145116 both ways) — a `.ma` round-trip reorders the DG and TAGG order
follows. `golden.py` therefore exports from the saved `.ma` on both sides.

## Architecture

Three layers, split by what they need. **`a3ob/formats/`** is Maya-free and testable under a plain
interpreter (`p3d`, `binary`, `model_cfg`, `paa`, `rvmat`, `serialize`). **`a3ob/mayabridge/`** is
the Maya layer (API 2.0): `attributes` (schema), `import_/` and `export/` (DAG ↔ MLOD, with
`export/pure.py` Maya-free), `commands/`, `translator`, `paatex/`, and the leaves `lodwalk`,
`skinquery`, `progress`. **`a3ob/ui/`** is the dock: `panels/`, `actions/`, `scene/` (Qt-free),
`autolod/`, `entry`, `_undo`.

`plug-ins/MayaObjectBuilder.py` registers the sixteen commands (API 2.0);
`MayaObjectBuilderTranslator.py` registers `Arma P3D` (API 1.0). `MPxFileTranslator` is 1.0-only
while commands need 2.0, so they cannot share a plugin — the main one auto-loads the other.

`scripts/objectBuilderMenu.py` and `objectBuilderAutoLOD.py` are EXTERNAL facades: the plugin loads
them by path and mayapy tests reach them via `runpy`. Keep them. `tools/` is dev-only and
deliberately outside `scripts/`, which is on `PYTHONPATH` *and* `MAYA_SCRIPT_PATH` — anything there
is importable in every Maya session.

`actions ↔ entry ↔ dock` is broken by a lazy dock import in `entry._build_qt_dock`. Every module in
`a3ob.ui.actions` does `from a3ob.ui.entry import *`, so `entry` must never import from that package
at module level — shared helpers go in leaves like `ui/_undo.py`.

`tools/dev_install.py` writes a `.mod` pointing here; the tracked `MayaObjectBuilder.mod` (root `.`)
makes a clone a drop-in module; `install/` is the end-user drag-in installer and must keep importing
only stdlib + `maya.cmds` (its `_module_text` duplication is load-bearing).

## Gotchas — the numbers are why these rules stand

### API 2.0 limits

- `MPxFileTranslator` and `MComputation` are API-1.0 only. The devkit documents the C++ API; the 2.0
  bindings do not cover all of it — verify a class exists before designing around it.
- `MFnSet.getMembers()` holds only ONE component type per DAG path: for a set with both vertices and
  faces of one mesh it returns the vertices and silently drops every face (1250 → 0). List
  membership with `cmds.sets(query=True)`.
- `MMeshIntersector.create(node, matrix)` needs points in the mesh's OWN object space; world points
  returned 1.009 where the true distance was 0.0186.
- `om.MGlobal` is immutable and cannot be monkey-patched in tests — functions that warn should also
  RETURN what they found. Selecting is `MGlobal.setActiveSelectionList(list, kReplaceList)`;
  `MGlobal.select` does not exist. Under mayapy `setResult` returns a 1-element list, not a scalar.
- `MSyntax.addFlag` takes ONE argument type per flag, and the long names `set` and `fix` are
  reserved — it raises "Unexpected Internal Failure" and the interpreter dies at dispatch. Maya
  builds syntax lazily on FIRST dispatch from a C++ callback that cannot absorb a Python exception,
  so such a flag kills the session with unsaved work. `initializePlugin` calls every `syntax()` up
  front (`_syntax_is_safe`) and skips the offender. Hence `-setproperty`, `-repair`.
- **A registered `MPxCommand` ignores code changes on plugin reload.** Unload + purge `sys.modules`
  + load refreshes plain modules, but command classes keep running the session's FIRST version —
  monkey-patching `doIt` never fires. Verify command changes under `mayapy`; Maya needs a restart.

### Undo

- `_UndoableBase` routes changes through an `MDagModifier`. Once a command is undoable, EVERY change
  must go through it — a `cmds.createNode` inside one survives Ctrl+Z and leaves orphans.
  `MFnSet.create()` never enters the undo queue at all, so sets use `cmds.sets` and set-building
  commands stay NON-undoable, wrapping their body in `undo_chunk()`. `a3obProxy`/`a3obUpdateProxy`
  were undoable and left orphan `a3ob_proxy_*` sets behind.
- Suspending undo is disable-then-restore (`ui/_undo.py`). The inverse shipped once and left Maya's
  undo queue dead for the whole session after one Validate click.
- `sets.py`'s cmds-based attr wrappers are NOT duplicates of the OpenMaya ones in `attributes.py` —
  collapsing them reintroduces that orphan-set bug.

### Skin weights and rigs

- Weights live in the `skinCluster` ALONE now — the branch that mirrored them into
  `a3obBakedWeights` on import and on every scene save (`weightsync.py`, `a3obBakeSkin -restore
  [-previous]`) was removed (`docs/specs/2026-07-20-weights-live-skincluster-design.md`). Deleting
  a skeleton destroys the weights with it, permanently; there is no second copy to fall back on.
  `a3obValidate` warns when a mesh has lost its rig while a sibling LOD of the same model is still
  skinned (`_model_has_skinned_sibling` in `commands/validate.py`) — it cannot recover the weights,
  only flag the loss before export does. Deleting the entire skeleton off a multi-LOD rigged model
  leaves no skinned sibling either, so that case slips through uncaught; there is no second source
  of truth left to catch it, which is exactly the point.
- `bindPreMatrix` is a **sparse multi indexed by `.matrix[]` LOGICAL indices** that do NOT compact
  when an influence is removed. `enumerate(influences)` is the wrong index and made
  `skeleton_is_posed()` report joints on a rig nobody moved: after removing two middle influences
  `bindPreMatrix` kept `[0,1,2,3]` while `.matrix` held `[1,3]`. Use
  `cmds.getAttr(skin + ".matrix", multiIndices=True)`. A TRAILING removal does not reproduce it,
  which is why a naive test passes. The joint's own `.bindPose` does not work at all.
- Removing an influence never deletes its weight — vertices sum to 1.0, so it redistributes in the
  ratio already present. `weightDistribution` does NOT govern that (measured identical both ways);
  it governs a later PAINT stroke: flooding to zero on a sleeve whose neighbours are pure `Elbow`
  gave `Shoulder 0.76 / Elbow 0.24` under **Distance** and `Elbow 1.0` under **Neighbors**.
- The reference asset carries its OWN skeleton and `ensure_reference()` KEEPS it. Importing,
  transferring, then deleting it was the obvious design and is wrong: the garment binds to exactly
  those joints, so removing them takes the skinCluster and every transferred weight with it.
  Weight cleanup belongs to Maya (`Smooth Skin Weights` / `Prune Small Weights`) —
  `a3obSkinWeights` selects suspect vertices and writes nothing.

### Export, smoothing, LODs

- **Smoothing lives in two places and NEITHER may be trusted alone** (`_edge_splits_the_shading`).
  With LOCKED normals the normals win: a DayZ jacket from FBX had 38131 edges all flagged hard and
  none soft, beside 40812 locked normals that were smooth — trusting the flag wrote "smooth normals
  AND every edge sharp" and Object Builder rendered it faceted. With UNLOCKED normals the flag is
  all there is: on a softened sphere with ten hand-hardened edges, `getNormalIds` and
  `getFaceVertexNormal` reported ZERO differing corners, so deciding by normals dropped every
  hand-set crease. `isNormalLocked(normalId)` picks which to believe, per edge. Border edges
  (<2 faces) split no shading and are never written; nonmanifold (>2) keep the flag.
  `getFaceVertexNormal()` returns the SHARED normal — use `getNormalIds()` into `getNormals()`.
- The round-trip guard for that must be a COUNT, not `> 0`: a `> 0` check hid a 19x inflation — the
  character fixture carries 2004 sharp edges and export wrote 38871.
- Export reads the DEFORMED mesh, so exporting a posed rig bakes the pose in; `a3obValidate` warns
  via `posetest.skeleton_is_posed()`.
- Export resolves a selection **upward first, then downward**. Upward-only meant selecting the
  folder holding a model's LODs resolved to nothing — the one layout that keeps several models apart
  was the one that could not be exported. A mesh still resolves to its own LOD, never siblings.
- An **empty LOD exports fine**; a plain Maya group does not (no `a3obIsLOD`). `_find_first_mesh_path`
  looks only a child and a grandchild deep — anything nested deeper is silently not exported.
- A LOD **resolution signature is not a named property**: `1.000e+13` encodes a Geometry LOD's type
  and the Blender reference lists it as a lookup KEY. Porting it as data gave every generated
  Geometry LOD a junk `lod` row. When something in `autolod/` looks like a magic Arma constant,
  check whether the reference treats it as data or as a key.
- LOD identity is its **node**, never its label. A measured scene had `|helmet`,
  `|group1|body|Resolution_2` and `|group1|body|Resolution_1` all reading "Resolution 1", so a
  label-filtered panel showed each the others' sets and counted them three times.
- Marking a mesh as a LOD must NOT rename it. Renaming shipped and was reverted: "helmet" became
  "Resolution_1" and a second mesh of the same type collided into a suffix. `meshops.py` has an
  unrelated `_mark_lod` — different signature, do not conflate.

### Auto LOD (crash zone)

- `cmds.polyNormalPerVertex` **segfaults Maya** — no exception, the session dies with unsaved work —
  on a decimated mesh with nonmanifold topology or lamina faces, and `polyCleanupArgList` does not
  reliably prevent it. `autolod` skips the normal pass on meshes with locked normals.
  `freezeNormal=False` is NOT an unfreeze; only `unFreezeNormal=True` clears them (1560 locked
  before and after).
- The QEM decimator must never emit a vertex no surviving face references: such a point has no
  normal and is what triggers that segfault. A vertex stays `alive_v` after its last face collapses
  into a degenerate one, so aliveness is not the same as being used — `test_qem.py` asserts the
  vertex and face sets agree in BOTH directions.
- Cancelling must leave the scene untouched: `decimate_chain` returns `None` rather than raising, so
  the generic `except Exception` fallback cannot swallow a cancel, and `core.py` removes the groups
  it created plus the hidden `__auto_lod_geometry_source` duplicate.
- Debugging a hard crash: reproduce under `mayapy` (exit 139 = segfault) and bisect with flushed
  print markers — the last flushed line IS the stack trace. Patch names on the module that CALLS
  them, not where they are defined: `helpers` is star-imported, which binds copies.

### Dock and panels

- Panels rebuild from the selected LOD and that scans every objectSet, while `SelectionChanged`
  fires per marquee-drag step. `_schedule_context_refresh` debounces and `_refresh_context_ui`
  drops the work when the LOD is unchanged; component picking must cost zero rebuilds
  (`dock_refresh_cost.py`).
- Anything a panel calls must be a SILENT query and must not WRITE. `a3obInfluence` warning from a
  refresh turned clicking any prop into Script Editor spam; `_selection_sets()` normalising on read
  dirtied the scene so Maya asked "Save changes?" after a read-only session. Hiding technical sets
  is the write path's job — all eight creation sites mark their own.
- Gate silence on "no acting flag set", NOT `isFlagSet("-li")`: measured, `-li` answered True under
  mayapy and False under interactive Maya for the identical call.
- Asserting silence needs a positive control in the same test, or it passes vacuously the moment the
  listener stops working (`dock_panel_sync.py`).
- The Selections panel keys on an **owner**, not strictly a LOD: a set made on an unmarked mesh
  belongs to that mesh. Requiring a LOD meant such a set exported fine while appearing in no panel.

### Misc

- A `@contextlib.contextmanager` must not `yield` inside a `try` that swallows the exception type its
  caller can raise — the exception is thrown back in at the `yield`, and a second `yield` turns it
  into `RuntimeError: generator didn't stop after throw()`, masking the real error.
- Shaders and texture `file` nodes use `cmds.createNode`, not `shadingNode` (which returns `None`
  during File > Import); type from `paatex.preferred_shader_type()` — `aiStandardSurface` with
  Arnold, else `blinn`, else `lambert`. Use `skipSelect=True` where a component selection must
  survive. Node names are scrubbed to `[A-Za-z0-9_]` and are not part of the P3D contract.
- Maya cannot read `.paa`, and File > Import's DG context blocks inline file-node creation, so
  `translator.do_read` defers texturing via `cmds.evalDeferred(..., lowestPriority=True)`.
- `numpy` and `python-lzo` are OPTIONAL and Maya ships neither, so the pure-Python fallbacks are the
  DEFAULT path for users — `test_no_numpy.py` blocks both and checks the DXT1 decoders agree
  exactly. In `meshops`, `getFloatPoints()` is NOT faster than `getPoints()` (31.6ms vs 16.4ms) and
  there is no precision trade-off: Maya stores points in single precision, so `getPoints()` only
  widens the same values (max difference 0.0).
- No `.gitattributes`, genuinely mixed line endings. Rewriting a file wholesale silently converts
  them and turns a 14-line change into a 1000-line diff — compare `git diff --shortstat` against
  `--ignore-cr-at-eol` before committing.

## P3D format invariants

- Faces are triangles or quads only; N-gons are triangulated on export. Triangles write 16 bytes of
  zero padding after their vertices; quads do not.
- UVs live in both the face data and the `#UVSet#` TAGG; V is inverted on write, read as `1 - v`.
  Ids are 0-based, id `0` is the primary set, and export reads Maya's ACTIVE set via
  `MFnMesh.getUVs()` with no set name.
- Axis conversion (an inverse pair, round-trip tested): import `(x, y, z)` → Maya `(x, z, -y)`;
  export Maya `(x, y, z)` → `(x, -z, y)`, vectors/normals the same swap and normalized. Separately
  `p3d.py` reads/writes each core vector's floats in `x, z, y` FILE order — a Y/Z swap on disk.
- TAGG structure: `active byte + null-terminated name + uint32 length + data`.

## PAA / texture invariants

- Decoded rows are **bottom-to-top** (OpenGL/MImage); `_write_png()` flips them. Cache dir
  `a3ob_paa_cache_v3`, verified byte-for-byte against the game's own `_co.png`.
- Alpha → transparency is **opt-in** (`MayaObjectBuilder_paa_alpha_transparency`, default off) and
  only for genuine bimodal cut-outs — a DayZ `_ca` alpha is often a data channel, and wiring it
  makes solid armour see-through.
- `_smdi`: R unused (1.0), **G = specular level**, **B = glossiness** → G to `specularColor`,
  `1 - B` to `specularRoughness`. Raw RGB blew the surface out with red spec.
- `_nohq` is **DXT5nm**: normal.X in alpha, normal.Y in green, Z reconstructed; wired through
  `aiNormalMap` (Arnold only).
- Paths resolve against `MayaObjectBuilder_texture_root`, then `P:/`, then a bounded basename
  search; `.rvmat` stage textures drive the exact channels, falling back to `_nohq`/`_smdi` siblings.

## Maya metadata attributes

| Attribute | Node | Purpose |
|-----------|------|---------|
| `a3obIsLOD`, `a3obLodType`, `a3obResolution`, `a3obResolutionSignature` | transform | LOD identity |
| `a3obSourceVertices`, `a3obVertexSourceIndices` | transform | Source vertices from import |
| `a3obUVSetTaggs`, `a3obSharpEdges` (+ their count/flag) | transform | TAGG preservation |
| `a3obSelectionName`, `a3obIsProxySelection`, `a3obFlagComponent`, `a3obFlagValue` | objectSet | Selections, proxies, flags |
| `a3obTechnicalSet`, `hiddenInOutliner` | objectSet | Outliner hiding |
| `a3obTexture`, `a3obMaterial` | shader | `.paa` / `.rvmat` paths driving the PAA pipeline |
| `a3obSkeletonName` | joint | Skeleton root (model.cfg) |

Source of truth: `mayabridge/attributes.py`, pinned by `test_attr_schema.py`. The proxy flag short
name is `a3px` on write; legacy `a3pr` is still read.

## Memory LOD locators

Memory LOD (`a3obLodType = 9`) points are Maya **locators** under the LOD transform, each locator's
short name becoming the P3D selection name. Export (`export/taggs/memory.py`) writes one vertex plus
one `SelectionTaggData` per locator when the LOD has no mesh child, skipping proxies; import
(`import_/builders.py`) rebuilds single-vertex selections as locators and multi-vertex ones as a
group; `ui/actions/memory.py` creates them.

## Do not touch without a specific task

- `Arma3ObjectBuilder-master/` — format reference only (gitignored; clone if missing).
- `dist/`, `build/` — generated; `build/golden/` holds the byte-gate baseline.
- Blender test workflows — need Blender, not part of normal validation.
