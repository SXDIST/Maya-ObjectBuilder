# Resume here

State of the UI-simplification work, written so a fresh session can pick it up without the
conversation that produced it.

**Branch:** `claude/ui-simplification-improvements-b45ece` · **PR:** #2 (draft)
**Do not merge per phase** — one merge at the end, by the author's decision.

## Where things stand

| Phase | State |
|-------|-------|
| 0 — dev module points at this worktree | done |
| 1 — weights: the `skinCluster` is the only store | **done**, 10 tasks, all reviewed |
| 2 — export pipeline: Auto LOD, textures, validation | **done**, 10 tasks, all reviewed |
| 3a — one LOD panel | **done**, 4 tasks, all reviewed |
| 3b — Selections absorbs Proxies and Flags | **done**, 7 tasks, all reviewed |
| 3c — Skinning slims to four buttons | **done**, 4 tasks, all reviewed |
| 3d — Materials → Attribute Editor; Preferences window | **done**, 5 tasks + a 2-task rebuild after live check |
| 4 — reference assets ship with the plugin | **done**, 3 tasks, all reviewed |
| 5 — menu and dock presentation | specced, not planned |
| 6 — close-out | see below |

Suite **66/66**. Dock is **5 panels**, down from 11. The byte gate has not moved once across the
whole branch: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.

Phase 4 fixed **two release-breaking defects that predate this branch**, neither in its own spec.
`_copy_runtime_package` opened with `shutil.rmtree(target)` where `target` is
`<userAppDir>/MayaObjectBuilder` — the same directory holding `references.default_directory()` and
the author's `backups/`, which contained a crash folder and an 899 KB weights backup written by no
code in this repo. Every re-install deleted them. Separately, `6d824ea` moved `autolod` and left
the file lists in `install_maya.py` and `package_release.ps1` stale in three different ways;
`REQUIRED_PACKAGE_FILES` is what `_validate_package` refuses to install without, so **every release
built from this branch would have hard-failed installation for every user.**
`tests/mayapy/release_manifest_matches_repo.py` now pins both lists to the repo and to each other.

Eleven specs in `docs/specs/2026-07-20-*.md`. Sequencing:
`docs/plans/2026-07-20-ui-simplification-index.md`. Completed plans:
`2026-07-20-phase1-weights.md`, `2026-07-20-phase2-export-pipeline.md`,
`2026-07-20-phase3a-lod-panel.md`, `2026-07-20-phase3b-selections.md`,
`2026-07-20-phase3c-skinning.md`, `2026-07-20-phase3d-materials.md`,
`2026-07-21-phase4-references.md`, `2026-07-21-phase3d-fix-ae-section.md`.

Phase 3b fixed **two proxy-command defects that predate this branch**, both from the same root
cause: `proxy_selection_name` is `"proxy:%s.%d" % (path, index)` and encodes **no LOD identity**,
so the same proxy in Resolution 1 and Resolution 2 keys on the identical string. `a3obUpdateProxy`
updated only whichever half of the pair was selected, and `a3obProxy` gated set creation
scene-wide and so silently skipped the second LOD's set. Both lookups are now LOD-scoped. If you
touch proxy code, assume that key is ambiguous until you have scoped it.

## Before running anything

**The byte gate is vacuous in this worktree unless two junctions exist.**
`Arma3ObjectBuilder-master/` (the `.p3d` fixtures) and `build/golden/` (the baseline) are
gitignored, so `git worktree add` did not bring them. Without them `golden.py verify` prints
`SKIP` and every byte assertion proves nothing — and the skip message advises
`golden.py capture`, which would rewrite the baseline from current behaviour and leave the
gate approving anything. **Never run `capture`.**

```bash
cmd //c mklink //J "Arma3ObjectBuilder-master" "C:\Users\targaryen\orca\Maya-ObjectBuilder\Arma3ObjectBuilder-master"
cmd //c mklink //J "build\golden" "C:\Users\targaryen\orca\Maya-ObjectBuilder\build\golden"
"/c/Program Files/Autodesk/Maya2027/bin/mayapy.exe" tests/golden.py verify
```
Expected: real per-fixture lines, not `SKIP`.

**Maya must be loading this worktree, not the main repo.** Run `tools/dev_install.py` from
*this worktree* and restart Maya if not — the `.mod` is read at startup, and a registered
`MPxCommand` keeps the session's first version of its class regardless of plugin reloads.
Also check the main repo is not still on `sys.path` (it was once, inherited from whatever
launched Maya); it matters whenever a task deletes a module.

## Operational lessons, paid for

- **Implementer agents must run everything in the FOREGROUND, and must never be asked to run
  `python tests/run_all.py`.** That full-suite run stalled three agents; the controller runs
  it instead. Removing it from dispatches stopped the stalling completely.
- **Push after every completed task.** A PR tracks the branch — there is no separate push
  target — so an unpushed commit is invisible. Three finished, reviewed tasks once sat
  unpushed.
- **Reviews earn their cost, repeatedly.** Across ~24 reviews they found real defects and
  no false positives. Seven were tests that passed vacuously; several were gaps in the plan
  rather than the code; one was a Critical the implementer had misdiagnosed.
- **Grep the whole repo before deleting.** A plan's file list missed `export/exporter.py`,
  which read a schema constant and would have raised `AttributeError` on every export of a
  scene containing a joint.
- **A test whose failure you have not witnessed is not evidence.** Ask implementers to break
  the thing deliberately and show the red. This caught more than anything else.
- **A real `QWidget` under mayapy segfaults** unless a `QApplication` is created **before**
  `maya.standalone.initialize()`. Use `_built_active_dock()` / `_release_active_dock()` from
  `tests/mayapy/_harness.py` — they build a dock registered so `_active_qt_dock()` finds it and
  release it through `teardown()`. Their guard is `isinstance(app, QtWidgets.QApplication)`, not
  `app is None`: Maya's own bring-up leaves a bare `QGuiApplication`, so a `None` check passes
  and *then* segfaults with no traceback.
- **A mayapy test that calls an `a3ob*` command needs `_harness.load_plugin()`.** Without it the
  command does not exist and the test fails with `AttributeError` unconditionally. Three test
  files in Phase 3b shipped from a plan that forgot it.
- **`cmds.select(some_set)` selects the set's MEMBERS, not the set node.** Pass `noExpand=True`.
  This bit twice in Phase 3b, once in production code.
- **A test that exercises a "use the default location" path writes into the user's real Maya
  folder unless something stops it.** `reference_overwrite_guard.py` created a junk
  `dayz_skeleton.ma` in `Documents/maya/MayaObjectBuilder/references` and repointed the
  optionVar at it. Stub `references.default_directory` to a `mkdtemp`, and restore every
  optionVar in a `finally` — `skin_transfer.py` has the idiom.
- **The Attribute Editor CAN be reached headlessly, through the callback hook.** Maya 2027 ships
  `AEshadingEngineTemplate.mel`, so writing our own would shadow it — but the chain
  `AEshadingEngineTemplate → AEentityTemplate → AEdependNodeTemplate` fires
  `callbacks -executeCallbacks -hook "AETemplateCustomContent" $nodeName`, and all of that works
  under mayapy in batch. Measured: `cmds.callbacks(addCallback=…)` and `listCallbacks` work;
  the Python `callbacks` command has **no flag for the node name** (`nodeName=` raises "Invalid
  flag"), so drive it with `mel.eval('callbacks -executeCallbacks -hook "…" "<node>";')` exactly
  as Maya does; and `cmds.editorTemplate(…)` no-ops rather than raising.
- **"Only *rendering* is untestable" was written here, and it was WRONG — it cost the whole of
  Phase 3d.** Because `editorTemplate` no-ops in batch, what is untestable is not the section's
  appearance but **whether it exists at all**. The shipped section rendered an empty frame on
  every shading engine and every test was green. Measured in a live session:
  `editorTemplate -callCustom` **never invokes its procs from inside the
  `AETemplateCustomContent` hook**, while `beginLayout`/`endLayout` do take effect — hence a
  frame with nothing in it. `-addControl` works, takes a `-label` override, and its change
  command fires with the NODE name; Maya then re-points those native controls itself. When a
  headless test can only observe that your code *ran*, and not what Maya *did with it*, treat
  the feature as unverified until a live session says otherwise.
- **The Attribute Editor builds a node type's template ONCE per tab**, then only re-points it.
  Any experiment that changes template code and re-selects the same node type measures nothing —
  a probe recorded ZERO hook calls across a whole round of "comparisons" that were duly written
  down as findings. The AE's **Copy Tab** button forces a genuine rebuild and is what made the
  diagnosis repeatable. Do not delete `workspaceControl("AttributeEditor")` to force one: it
  takes `AEmenuBarLayout` with it and Maya cannot recreate the panel — that costs a restart.
- **The menu is invisible to every headless test.** `entry.show_plugin_ui` returns immediately
  under `cmds.about(batch=True)`, so menu callbacks must stay one-line wrappers over functions
  that *are* testable. `cmds.confirmDialog` returns `None` under mayapy rather than blocking,
  so a dialog cannot hang a headless run — but it also cannot be exercised by one.

## Decisions already made — do not relitigate

- **The skeleton always stays in the scene.** The whole weights design rests on it.
- The lost-rig warning fires only when a sibling LOD of the same model is still skinned;
  whole-skeleton deletion is knowingly uncaught, recorded in the weights spec.
- **`damage` severity means "the scene shows one thing and the file silently contains
  another".** Exactly two situations qualify today: a posed rig, and an Object Builder set
  with no live members. The lost-skinCluster report deliberately stays a `warning`.
- **Relevance drives prominence, never availability.** Mass collapses where unusual, never
  hides or disables; the property combo suggests but accepts anything.
- The 23 unwired option-box keys stay — stubs for planned features, not dead code.
- `autolod` lives in `mayabridge`, not `ui`: export must not import from `a3ob.ui`.

## Open items the author must handle

1. **Three things need ONE live Maya session between them.** Headless mayapy creates no UI at
   all — `cmds.about(batch=True)` is true and every UI command returns `False`.
   - The **P3D option box** has never been opened. It now has an Auto LOD frame, an Import
     Textures checkbox, and three fewer validation checkboxes.
   - The **proxy and flag dialogs** (`ui/dialogs.py`) have no automated coverage and cannot get
     any: mayapy cannot drive a modal `exec()`. Removing their `scriptJob` rests on an
     inspection claim — `QDialog.exec()` is application-modal, so `SelectionChanged` cannot fire
     while one is open. If a later task ever makes a dialog modeless, its mode label silently
     regains the ability to lie.
   - The **five-panel dock** as a whole, since Phase 3b removed two panels and Phase 3d Task 5
     retired a third (Materials, moved to the Attribute Editor and Preferences window).
   - The **Reference Assets submenu** added in Phase 3c: that six items and two dividers render,
     and that `Set Texture Root` is not swallowed into the submenu. No test can reach it.
   - The **DayZ Material section in the Attribute Editor** added in Phase 3d. This one has the
     longest list, because the AE caches a template per node TYPE and the headless suite can
     drive the state layer but never the rendering:
     **This list was rewritten after the first live check found the section did not work at
     all.** It rendered an empty frame on every shading engine, because
     `editorTemplate -callCustom` never fires from inside the `AETemplateCustomContent` hook
     — `beginLayout` does. The section was rebuilt on `-addControl`
     (`docs/plans/2026-07-21-phase3d-fix-ae-section.md`), which deleted `_SECTIONS`,
     `_resolve_section`, `_manage_layout` and the proc pair. Do not look for those.
     1. The section appears for a marked shading engine, and the stock **Shading Group
        Attributes** is still intact — Maya 2027 ships its own `AEshadingEngineTemplate.mel`
        and ours would shadow it, so this is the check that we did not.
     2. Both fields render, populated from the node, labelled **Texture** and **Material** —
        not Maya's auto-prettified "A 3ob Texture". That is the `-label` override.
     3. A plain shading engine shows **no DayZ Material section at all** — not an empty
        frame, which is what the broken version did.
     4. **Re-pointing.** Select a different marked shading engine in the same AE tab; the
        fields must follow it. This is the highest-value item: Maya owning re-pointing is the
        entire reason the per-tab bookkeeping could be deleted, and no headless test reaches it.
     5. Editing a field writes it, normalised to the backslash form, and re-textures. Type
        `P:/data/x.paa` and confirm it comes back as `data\x.paa`.
     6. Nothing writes `a3obTexture`/`a3obMaterial` onto a node the plugin never marked.
        Check `initialShadingGroup` specifically: the pre-fix version reached three nodes
        from one keystroke.
     7. A shading engine carrying only ONE of the two attributes — does the missing one show
        as an empty field, or does the section break? `should_show_section` returns true on
        either, and both controls are declared unconditionally. Untestable headlessly.
     8. **Select Faces by Material** in the menu selects the right faces, both with a shading
        engine selected and with just the material selected.
     9. The Script Editor stays silent while clicking around a busy scene with the AE open.
   - The **Preferences window** added in Phase 3d, reached from the menu where
     `Set Texture Root (.paa)…` used to be:
     1. The window renders, with three sections — Texture root, Alpha → transparency, and
        **Active texture sources** — and no free-text path checker (that was cut).
     2. It opens with the **dock closed**. It is reached from the menu, which exists
        independently of the dock, and no headless test can cover that.
     3. Active texture sources shows a real message immediately on open, no typing.
        Reproduce the motivating bug by hand — a configured root that EXISTS but is not what
        resolves the textures — and confirm the message never claims `configured`. A root
        existing on disk is not evidence it is in use; that was the whole point.
     4. An untextured scene says so plainly rather than implying a verdict, and a scene over
        500 materials still opens promptly and admits it sampled.
     5. Changing the root re-textures already-imported materials; toggling alpha changes
        viewport transparency on materials already in the scene. Both act on what is already
        there, not only on the next import — that is what makes them feel real.
     6. Phase 3d Task 5 retired the Materials panel's own alpha checkbox and texture-root
        field entirely, so the Preferences window is now the only door to either setting —
        the two-doors-must-stay-in-sync concern this bullet used to name no longer applies.
   - The **installer**, after Phase 4. It cannot be exercised end to end headlessly — `install()`
     unloads and reloads the plugin and writes a `.mod` — so only its pure helpers are tested.
     1. Drag `install/install_maya.py` in with the assets present; the console names the seeded
        files.
     2. `references/` and `backups/` in `<userAppDir>/MayaObjectBuilder` **survive the install**.
        This is the data-loss fix; before Phase 4 they were deleted every time.
     3. *Add Male Character* works with no prior manual save — the point of the whole phase.
     4. Hand-edit the seeded `dayz_male_body.ma`, or repoint its optionVar elsewhere, re-run the
        installer, and confirm it is untouched.
     5. The plugin still loads and autoloads after the install.
2. **Whole-scene validation ignores `visibleOnly`** while the exporter honours it, so a
   hidden invalid LOD can block an `Export All` that would have succeeded and never
   contained that node. A reviewer called it a fast-follow, not a merge blocker.
3. **"Apply to all selected LODs" is exercised by no test**, before or after this work.
4. `translator.do_read` still checks the removed `validateMeshes` key — a dead gate, one-line
   cleanup.
5. Two of the LOD panel's buttons refresh twice per click, because `_active_qt_dock()` does
   not register a test-built dock. Cheap, but it is production paying for testability.

## Phase 6, when everything is done

Point the dev module back at the main repo and restart Maya **before** removing this
worktree. A `.mod` left pointing at a deleted worktree leaves Maya silently without the
plugin.

## The local ledger

`.superpowers/sdd/progress.md` holds per-task detail — commit ranges, review outcomes, fix
rounds, and the reasoning behind each judgment call. It is gitignored scratch and will not
survive `git clean -fdx`. Nothing above depends on it; `git log` is the real record.
