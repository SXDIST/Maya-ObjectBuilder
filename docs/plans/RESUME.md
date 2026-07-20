# Resume here

State of the UI-simplification work, written so a fresh session can pick it up without the
conversation that produced it.

**Branch:** `claude/ui-simplification-improvements-b45ece` · **PR:** #2 (draft, do not merge
per phase — one merge at the end, by the author's decision)

## Where things stand

| Phase | State |
|-------|-------|
| 0 — dev module points at this worktree | done |
| 1 — weights: the `skinCluster` is the only store | **done**, 10 tasks, all reviewed, merged into the branch |
| 2 — export pipeline | **planned**, not started — `docs/plans/2026-07-20-phase2-export-pipeline.md` |
| 3 — panels (11 → 5) | specced, not planned |
| 4 — reference assets ship | specced, not planned |
| 5 — menu and dock presentation | specced, not planned |
| 6 — close-out | see below |

Eleven specs in `docs/specs/2026-07-20-*.md`. The sequencing document is
`docs/plans/2026-07-20-ui-simplification-index.md`.

Suite is 41/41. The byte gate has not moved once: `5e66ed46ac09f396` / 6145116 and
`0ba984eb4fdb5d5e` / 60229.

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

**Maya must be loading this worktree, not the main repo.**

```python
import maya.cmds as cmds, a3ob, os
print(cmds.pluginInfo("MayaObjectBuilder.py", query=True, path=True))
print(os.path.dirname(a3ob.__file__))
```
Both must contain `.claude/worktrees/ui-simplification-improvements-b45ece`. If not, run
`tools/dev_install.py` **from this worktree** and restart Maya — the `.mod` is read at
startup, and a registered `MPxCommand` keeps the session's first version of its class
regardless of plugin reloads.

Also check the main repo is not still on `sys.path` (it was, inherited from whatever
launched Maya). Harmless normally; it matters whenever a task deletes a module, because the
deleted module keeps importing from the main copy and the deletion looks like it worked.

## Operational lessons, paid for

- **Implementer agents must run everything in the FOREGROUND.** Two stalled in Phase 1 by
  launching the mayapy suite in the background and waiting for a notification. The suite
  takes several minutes; that is normal. Say so in every dispatch.
- **Push after every completed task**, in the same step as the ledger entry. A PR tracks the
  branch — there is no separate push target — so an unpushed commit is invisible to the
  reviewer. Three finished, reviewed tasks once sat unpushed.
- **Reviews earn their cost.** Eleven reviews in Phase 1 found eight real defects and no
  false positives. Five were tests that passed vacuously — one reported `PASS` through the
  suite runner while checking nothing. Two were gaps in the plan rather than the code.
- **Grep before deleting, across the whole repo.** The plan's file list missed
  `export/exporter.py`, which read `A.BAKED_WEIGHTS` and would have raised `AttributeError`
  on every export of a scene containing a joint. Phase 2's Task 1 and Phase 1's Task 9 both
  now open with a sweep for this reason.
- **A test whose failure you have not witnessed is not evidence.** Ask implementers to break
  the thing deliberately and show the red.

## Decisions already made — do not relitigate

- **The skeleton always stays in the scene.** This is the premise the whole weights design
  rests on. If it ever changes, the storage decision must be revisited, not patched.
- **The lost-rig warning fires only when a sibling LOD of the same model is still skinned.**
  Deleting an entire skeleton is therefore not caught; that is accepted and recorded in
  `docs/specs/2026-07-20-weights-live-skincluster-design.md`.
- **The second warning trigger the spec originally called for was dropped**, because import
  turns every Selection TAGG into a plain objectSet — `Pelvis` and `camo_jacket` are
  indistinguishable once the joints are gone.
- **The 23 unwired option-box keys stay.** They are stubs for planned features, not dead code.
- **`autolod` moves to `mayabridge` in Phase 2 Task 1**, because export must not import from
  `a3ob.ui`.

## Carried findings for a later review

- `_model_has_skinned_sibling` assumes one folder holds a model's LODs; hand-built scenes
  with per-resolution subfolders may group differently.
- Five tests call bare `main()` instead of `sys.exit(_harness.run(main))`, losing the
  `FAIL <test>: <error>` attribution line.
- `import_writes_no_bake.py` prints SKIP and exits 0 when the reference clone is absent, and
  the runner reports that as PASS.
- The spec's headline 2.73 MB is **not** reclaimed yet: existing scenes keep the attributes
  and re-saving preserves them. The cleanup action needs Phase 3's Preferences window.

## Phase 6, when everything is done

Point the dev module back at the main repo and restart Maya **before** removing this
worktree. A `.mod` left pointing at a deleted worktree leaves Maya silently without the
plugin.

## The local ledger

`.superpowers/sdd/progress.md` holds the per-task detail — commit ranges, review outcomes,
fix rounds. It is gitignored working scratch and will not survive `git clean -fdx`. Nothing
above depends on it; it is a convenience, and `git log` is the real record.
