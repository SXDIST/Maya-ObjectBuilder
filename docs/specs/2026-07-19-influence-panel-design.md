# Influence Panel — Design

**Goal:** remove unwanted bones from a garment without leaving Paint Skin Weights and
without hunting for joints in the Outliner.

## Why

A DayZ garment is bound to the whole skeleton on purpose — guessing the subset a garment
needs is exactly what goes wrong — and `removeUnusedInfluence` then drops the bones that
ended up carrying nothing. What survives is the crumbs: a collar next to the neck picks up
`Face_Jawbone` and `Face_Chin` at a fraction of a percent, and a jacket ships carrying
facial bones.

Removing them natively costs a round trip per bone: leave the paint tool, find the joint in
the Outliner, add the mesh to the selection, `Skin > Edit Influences > Remove Influence`,
go back to painting. The information needed to make the decision is visible only inside the
paint tool, and the operation is only available outside it.

Worse, the obvious shortcut is wrong. Flooding an influence to zero does not delete weight —
weight cannot be deleted, only moved, because every vertex must sum to 1.0. Maya hands it to
the other influences, and by default it picks them by *distance to the bone*, ignoring what
the surrounding geometry uses. Measured on a sleeve whose neighbouring vertices are pure
`Elbow`: zeroing `Head` gave `Shoulder` 0.76 / `Elbow` 0.24 under **Distance**, and `Elbow`
1.0 under **Neighbors**. That default is how head weight lands on an arm, and why influences
appear to come back — the weight ping-pongs between two bones, so `Remove Unused Influences`
can never drop either.

## Scope

One selected mesh at a time, matching how Paint Skin Weights itself works.

Bones are judged **by name** (`Face_*`, `Eye*` — known-unwanted on clothing) and **by
location** (select a bone's vertices and look at where they are). Weight-share sorting is
deliberately out of scope; it was considered and not wanted.

## Components

### `scripts/a3ob/mayabridge/influences.py` — Maya-free

Name-mask matching and the decision of which influences may be removed. No Maya import, so
it runs under a plain interpreter like `skinweights.py` does.

- `match_names(names, pattern) -> [str]` — shell-style mask (`fnmatch`). An empty pattern
  matches nothing, not everything: an empty filter box must not arm a button that strips
  every bone.
- `removable(all_names, requested) -> ([str], str)` — the subset that may go, plus a reason
  when something is held back. A skinCluster must keep at least one influence; a mesh with
  none is undeformable, and a selection covering every bone is a slip, not an instruction.

### `scripts/a3ob/mayabridge/commands/influence.py` — `a3obInfluence`

One module per command, registered through the `COMMANDS` list, following the existing
layout. Three operations: list the influences of the selected mesh, remove the named ones,
select the vertices one bone drives.

Flag names are chosen conservatively. `set` and `fix` are reserved long names in this
plugin's history and `MSyntax.addFlag` does not fail gracefully — it kills the session at
first dispatch, losing unsaved work. `initializePlugin` already guards every command through
`_syntax_is_safe`, so a bad flag skips the command instead of killing the session. Every
mayapy test loads the plugin and therefore runs that guard over the new command; a flag name
Maya rejects shows up as the command being missing, not as a dead interpreter.

The command is **not** undoable. It works through `cmds`, so per the repo's rule it stays
non-undoable and wraps its body in `undo_chunk()` — one Ctrl+Z for the whole removal. Mixing
that with an `MDagModifier` is what leaves orphans behind.

### `scripts/a3ob/ui/panels/skinning.py` — the "Influences" section

A collapsible section holding a filter field, a multi-select list, and two buttons. The
filter is backed by an optionVar, so `Face_*` is typed once and stays.

The filter **narrows what the list shows**; it never removes anything by itself. Both
buttons act on the entries highlighted in the list. Typing a mask and pressing Remove is
therefore always two deliberate steps — filter, then select what you meant — rather than one
keystroke away from stripping a rig.

- **Select Vertices** — selects the vertices the highlighted bone drives above 1/254. Below
  that a weight encodes to a zero byte and never reaches the `.p3d`, so showing those
  vertices would misrepresent what is actually bound.
- **Remove** — removes the highlighted bones.

### `scripts/a3ob/ui/entry.py` — wrappers

`_list_influences()`, `_remove_influences(names)`, `_select_influence_vertices(name)`,
beside `_transfer_skin` and `_bake_skin_weights`, unwrapping `[value] -> value` the way the
existing wrappers do for `mayapy`.

## Data flow

The list is rebuilt from the selected mesh's skinCluster on the dock's existing debounced
refresh (`_refresh_context_ui` / `_schedule_context_refresh`, driven by `SelectionChanged`).
Rebuilding must stay free for ordinary component picking — `tests/mayapy/dock_refresh_cost.py`
guards that and must stay green.

Removal runs in this order, and the order is not cosmetic:

1. Remember the current tool context and leave the paint tool.
2. Set `weightDistribution` to `Neighbors` (1).
3. Remove the influences in a single call taking the whole list.
4. Restore the previous tool context.

Step 2 before step 3: redistribution happens *during* removal, so flipping the mode
afterwards is too late — the weight has already scattered by the old rule.

Step 1 exists because mutating a skinCluster's influence list while the Artisan tool holds
it is the leading suspect in a silent, log-less crash the user hit repeatedly. The panel
does the switching so the user never has to remember it.

## Error handling

| Case | Behaviour |
|------|-----------|
| Nothing selected, or the selection has no mesh | Empty list, buttons disabled, reason in the script editor |
| Mesh has no skinCluster | Empty list, stated plainly |
| The selection covers every influence | Refuse; keep at least one and say why |
| `weightDistribution` locked or connection-driven | `setAttr` raises; catch and carry on, as `finish_for_dayz` already does |
| Every remaining influence is locked (`lockInfluenceWeights`) | Report it — normalization has nowhere to put the weight |
| Tool context changed underneath us | Do not force the restore; leave the select tool |
| Running headless (`mayapy`) | Contexts do not exist — verified, `currentCtx()` returns `None`. Enter/exit degrade to no-ops |

## Testing

`tests/python/test_influences.py` — mask matching (empty mask, no match, `Face_*`, `Eye*`)
and the never-remove-the-last-influence rule. Plain interpreter.

`tests/mayapy/influence_panel.py` — a collar mesh on `Neck` / `Head` / `Face_Jawbone` /
`Face_Chin`, weighted onto the facial bones. Then: list the influences; remove by mask;
assert the facial bones are gone; assert the weight landed on `Head` and `Neck` (measured:
0.99 / 0.01); assert `weightDistribution == 1`; assert removing every influence is refused;
assert one undo restores the previous state.

`tests/mayapy/dock_refresh_cost.py` must stay green — the new section may not make component
picking cost a rebuild.

**Not covered by tests:** restoring the paint tool context. Contexts exist only in an
interactive session, so this is verified by hand in Maya, not in CI.
