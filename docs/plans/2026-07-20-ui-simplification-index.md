# UI simplification — implementation index

**Date:** 2026-07-20
**Branch:** `claude/ui-simplification-improvements-b45ece`
**Specs:** the eleven `docs/specs/2026-07-20-*.md` documents

This is the sequencing document for the PR. Each phase is a separate plan with its own
tests and commits, and each leaves the plugin working. Phases are ordered by dependency,
not by size.

## Headline

| | Before | After |
|---|--------|-------|
| Dock panels | 11 + a fixed Quick Actions header | 5, no header |
| P3D option-box controls | 32, of which 9 are wired | 32 + Auto LOD + textures; the 23 stubs stay |
| Weight storage | `skinCluster` + 2.73 MB of duplicated text | `skinCluster` alone |
| Validation at export | never by default; result discarded | always; errors block, damage asks |
| `a3obUpdateProxy` | registered, reachable from nothing | editable in the Selections panel |

## Phase 0 — dev module points at this worktree

**Status: done by the author.** Recorded because it is invisible and because it must be
undone.

Maya loads whatever `Documents/maya/modules/MayaObjectBuilder.mod` names, and it named the
**main** repo. `tools/dev_install.py` run from *this worktree* rewrites it to point here.
A Maya restart is required: `PYTHONPATH` and `MAYA_SCRIPT_PATH` are read at startup, and a
registered `MPxCommand` keeps the session's first version of its class regardless of plugin
reloads.

**Verify before starting Phase 1** — a half-switch (mod rewritten, Maya not restarted) means
editing here while executing `main`:

```python
import maya.cmds as cmds, a3ob, os
print(cmds.pluginInfo("MayaObjectBuilder.py", query=True, path=True))
print(os.path.dirname(a3ob.__file__))
```

Both must contain `.claude/worktrees/ui-simplification-improvements-b45ece`. Verified on a
restarted session: plugin path, `a3ob` module path and the `.mod` all point here.

**Also check that the main repo is not still on `sys.path`.** In the verified session it
was, inherited from whatever launched Maya — not from the `.mod` (only one exists, pointing
here), not from `Maya.env` (empty), not from `HKCU`/`HKLM` (unset):

```python
import sys
print([p for p in sys.path if "Maya-ObjectBuilder" in p])
```

The worktree sorts first, so imports resolve here and normal work is unaffected. The hazard
is specific to **Phase 1, which deletes code**: a module removed from the worktree keeps
importing from the main copy, so the deletion looks successful without being it. Either
launch Maya without that inherited environment, or drop the entry for the session:

```python
import sys
sys.path[:] = [p for p in sys.path
               if not (p.rstrip("\\/").endswith("Maya-ObjectBuilder\\scripts")
                       or p.rstrip("/").endswith("Maya-ObjectBuilder/scripts"))]
```

**Phase 6 undoes this.** Removing the worktree while the `.mod` still points at it leaves
Maya silently without the plugin.

## Phase 1 — Weights: the skinCluster is the only source of truth

**Spec:** `2026-07-20-weights-live-skincluster-design.md`

**Why first.** It deletes `a3obBakedWeights`, and that changes what Phase 2 must do: with no
bake to fall back on, re-binding a duplicated LOD1 stops being an optimisation and becomes
required. Building Auto LOD first would build against a fallback that is about to vanish.

**Touches:** `mayabridge/weightsync.py`, `commands/skin.py`, `export/taggs/skin.py`,
`import_/convert/mesh.py`, `attributes.py`, `skinquery.py`, `ui/panels/skinning.py`
(the storage block only), `ui/entry.py`,
`tests/mayapy/{weight_sync,weights_restore,weights_survive_skeleton,weights_panel_state}.py`,
`tests/python/test_attr_schema.py` (35 pairs → 33).

**Re-check before deleting anything:** every mesh carrying a bake must have a live
skinCluster. Verified once on `Own_Dreykrus.mb`; the scene has changed since, so verify
again. If any mesh has a bake and no cluster, the spec's "no migration" section is void.

**Gate:** `mayapy tests/golden.py verify` must not move — a mesh with a live skinCluster
already exports through `_add_skin_weight_taggs`, untouched here.

## Phase 2 — The export pipeline

**Specs:** `2026-07-20-ui-simplification-design.md` (Auto LOD, texture import),
`2026-07-20-validation-at-export-design.md`

**Why together.** All of it edits `translator.py`'s `do_read`/`do_write` and
`mayaObjectBuilderP3DOptions.mel`. Split across phases, that is three sequential conflicting
edits to the same two files.

Ordered within the phase:

1. **Non-consuming generator.** Remove the `cmds.rename(source, name)` in
   `_generate_resolution_lods`; duplicate instead, `_propagate_named_selections(...,
   full_resolution=True)`, then re-bind and copy weights with `MFnSkinCluster.setWeights`.
   **Not `cmds.copySkinWeights`** — measured at 0.1027 deviation on geometry duplicated from
   the source, against 0.0 for the array write.
2. **Undo helper moves** to `mayabridge/undoctl.py`, re-exported by `ui/_undo.py`, so
   `mayabridge` need not import `ui`.
3. **Auto LOD at export:** the option-box frame and keys, then transient
   generate → export → cleanup in `finally`, undo suspended across the span.
4. **`importTextures`** gating the deferred texture assignment in `do_read`.
5. **Validation always on:** three severities, the gating flags removed, the result read
   instead of discarded, and the scene-global set checks hoisted out of the per-mesh pass.

**Gate:** `mayapy tests/golden.py verify`. Validation decides *whether* a file is written,
never what its bytes are.

## Phase 3 — Panels

**Specs:** `ui-simplification` (LOD merge), `mass-flags-properties`,
`proxies-into-selections`, `skinning-panel` (panel half), `materials-into-attribute-editor`

Ordered by dependency:

1. **LODs + LOD Properties merge** — `QTreeWidget` with inline type/resolution editors, and
   the detail area the next step fills.
2. **Mass and Named Properties** into that detail area; **Flags** into Selections.
3. **Proxies** into Selections, plus the `a3obUpdateProxy` editing path.
4. **Skinning panel** down to four buttons and the influence list.
5. **Materials** to an `AEshadingEngineTemplate`; the two global preferences to a
   Preferences window.

**Gates:** `dock_refresh_cost.py` (component picking must still cost zero rebuilds — the
inline editors are the risk) and `dock_panel_sync.py` (panels stay silent reads, positive
control intact).

## Phase 4 — Reference assets ship

**Spec:** `2026-07-20-skinning-panel-design.md` (reference half)

`assets/references/` with its own ADPL-SA `LICENSE` and attribution, a root `README` note,
and `install/install_maya.py` copying them into `default_directory()` and setting the
optionVars — never overwriting a reference the user has already saved.

**Blocked on the author** supplying the prepared `.ma` files. Everything else in the phase
can be built and tested against an empty directory, which must also be a passing case.

**Constraint:** `install_maya.py` still imports only stdlib and `maya.cmds`.

## Phase 5 — Menu and dock presentation

**Spec:** `2026-07-20-menu-and-dock-presentation-design.md`

Last, because it arranges what every other phase leaves behind. Menu restructured with
`dividerLabel` sections, icons and the Save Selection submenu; Quick Actions removed;
`entry.export_p3d` fixed to set `defaultFileExportActiveType` as well as
`defaultFileExportAllType`.

**Test worth writing carefully:** no widget sets a *non-empty* stylesheet. `widgets.py:105`
calls `setStyleSheet("")` to strip inherited styling — it enforces the rule, so a blanket
ban fails on the one line implementing the policy.

## Phase 6 — Close-out

1. Full run: `python tests/run_all.py`.
2. `mayapy tests/golden.py verify` — never `capture`, which overwrites the baseline and
   makes the gate vacuous.
3. **Point the dev module back at the main repo** and restart Maya.
4. `git diff --shortstat` against `--ignore-cr-at-eol`: the repo has genuinely mixed line
   endings and no `.gitattributes`, so a wholesale rewrite turns a small change into a
   thousand-line diff.
5. Open the PR, one section per phase.

## Carried debt, deliberate

- The 23 unwired option keys stay — they are stubs for planned features, not dead code.
- Proxy placeholders remain invisible in the viewport until export.
- Whether the PAA cache deserves controls in the Preferences window is unanswered.
- Whether import should rebuild a live rig from P3D bone selections is unanswered.
