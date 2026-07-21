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
| 3d — Materials → Attribute Editor; Preferences window | specced, **not planned** |
| 4 — reference assets ship with the plugin | specced, not planned |
| 5 — menu and dock presentation | specced, not planned |
| 6 — close-out | see below |

Suite **58/58**. Dock is **6 panels**, down from 11. The byte gate has not moved once across
the whole branch: `5e66ed46ac09f396` / 6145116 and `0ba984eb4fdb5d5e` / 60229.

Eleven specs in `docs/specs/2026-07-20-*.md`. Sequencing:
`docs/plans/2026-07-20-ui-simplification-index.md`. Completed plans:
`2026-07-20-phase1-weights.md`, `2026-07-20-phase2-export-pipeline.md`,
`2026-07-20-phase3a-lod-panel.md`, `2026-07-20-phase3b-selections.md`.

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
   - The **six-panel dock** as a whole, since Phase 3b removed two panels and moved their
     controls.
   - The **Reference Assets submenu** added in Phase 3c: that six items and two dividers render,
     and that `Set Texture Root` is not swallowed into the submenu. No test can reach it.
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
