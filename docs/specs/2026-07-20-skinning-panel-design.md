# Skinning panel: what is left once the storage model goes

**Date:** 2026-07-20
**Status:** approved, not implemented
**Depends on:** `2026-07-20-weights-live-skincluster-design.md`,
`2026-07-20-validation-at-export-design.md`

## Starting point

`panels/skinning.py` is 349 lines and shows, top to bottom: four reference-asset buttons, a
transfer row with a distance field, Test Pose, a weights-storage block of three buttons and
a state line, and an influence list with two buttons — separated by four paragraphs of
explanatory prose.

## What the other specs already remove

The weights-storage block goes with `a3obBakedWeights`: the explanatory paragraph, the
state line, **Restore Weights**, **Use the Older Copy**, **Bake Now**, plus `_weights_state`,
`_weights_state_text`, `_why_nothing_restored`, `run_bake_skin`, `run_restore_skin`,
`_show_restore_previous` and `refresh_weights_state` — roughly 141 of 349 lines, 40% of the
panel.

That also removes the panel's only `on_expand` callback (`dock.py` registers
`refresh_weights_state` for "Skinning"). The panel becomes static: expanding it stops
costing a scene scan.

The panel's own warning text — *"WARNING: the older copy is one save from being
overwritten"* — disappears with the model that made it necessary. A panel that has to warn
the user about its own storage was evidence the storage was wrong.

**Select Skin Outliers** arrives here from the Validation panel. It is a weight tool that
writes a selection, and never belonged in a read-only validator.

## Decisions

### Removed from the panel

- **Add Skeleton.** The reference body carries its own skeleton and `ensure_reference`
  keeps it, so adding a bare skeleton is the rare case. Moves to the menu.
- **The `Detached over` field.** `DEFAULT_FAR_DISTANCE = 0.06` is not a guess: it was
  measured on a real DayZ character — boots 0.009, trousers 0.019, jacket 0.024, helmet
  0.025, against a backpack at 0.102 — and 0.03, the first guess, wrongly classified parts
  of the jacket as detached. The field only ever overrode an already-correct value. The
  `a3obTransferSkin -distance` flag stays as the escape hatch.
- **The four explanatory paragraphs.** With the panel down to four buttons and a list, the
  prose outweighs the interface. The detail is already written in the tooltips, which is
  where it stays.

### Renamed

- **Add Male Body → Add Male Character.** It imports the body *with its materials and its
  skeleton*; "Body" undersells what lands in the scene.

### Reference assets now ship with the plugin

`references.py` states the assets are Bohemia's and therefore not stored in the repository.
That premise was wrong: Bohemia publish the character rig and body themselves, in
`BohemiaInteractive/DayZ-Misc` under *Rig and Animations*.

The constraint is licensing, not availability. `DayZ-Misc` is under the **Arma and DayZ
Public License Share Alike (ADPL-SA)**: attribution required, non-commercial, Arma/DayZ
only, and share-alike — derivatives must carry the same license. GitHub does not even
detect it as a license (`gh api` reports `license: null`). A prepared `.ma` with materials
and `a3obTexture`/`a3obMaterial` paths set up *is* an adaptation of their mesh, so it falls
under that share-alike clause. The plugin's own code is MIT and is not a derivative of the
mesh, so the two must not be mixed in one undifferentiated tree.

Therefore:

- `assets/references/` holds the prepared `.ma` files and **its own `LICENSE`** naming
  ADPL-SA, with attribution to Bohemia Interactive.
- The root `README` states plainly that code is MIT and that this directory is ADPL-SA,
  with what that implies (non-commercial, Arma/DayZ only, share-alike).
- The installer copies whatever it finds there into `default_directory()` and points the
  optionVars at the results, skipping silently when the directory is absent.
  `install_maya.py` must keep importing only stdlib and `maya.cmds`; `shutil` satisfies
  this.
- Never overwrite a reference the user has already saved. Someone who customised their body
  must not lose it to an upgrade.

The result is that **Add Male Character works immediately after installation**, which is
what deleting the save buttons was reaching for.

*This records what the licenses say, not legal advice; the compatibility call is the
author's.*

### Moved to the menu, not deleted

**Save Selection as Body** and **Save Selection as Skeleton** were proposed for deletion.
Shipping the assets removes the argument that they are the only way to obtain a reference,
but not the reason to keep them: they are how a reference gets *changed* — a DayZ update
alters the rig, texture or material paths need fixing, or a different base character is
wanted. Without them a shipped reference is frozen.

They belong in the menu rather than the panel because `save_reference` exports the current
selection with `force=True` and **no confirmation**: a wrong selection plus one click
silently replaces the reference asset. A destructive, once-in-a-while action should not sit
beside buttons pressed daily.

Therefore a **Reference Assets** submenu holds: Add Male Character, Add Skeleton, Save
Selection as Body, Save Selection as Skeleton. `KINDS` also defines `female_body`, which has
never had any UI at all; the submenu exposes it for free and removes that inconsistency.

**Added safety:** saving over an existing reference asks first, naming the file it would
replace. Overwriting a working reference with a mis-selection currently has no way back.

### Added

The transfer result must report **how many shells were rigidified**.
`transfer_to_target` already returns the count and the panel discards it, saying only
"Transferred onto N mesh(es)". Removing the distance field removes the user's ability to
correct a misclassification, so the misclassification must at least become visible — the
margin between fitted cloth at 0.06 and a backpack at 0.102 is only 1.7×, and a bulky vest
with pouches could fall in it.

## Resulting panel

```
[ Add Male Character ]
[ Transfer Skin from Body ]
[ Test Pose ]
[ Select Skin Outliers ]

Filter [____________]
┌────────────────────┐
│ bone list          │
└────────────────────┘
[ Select Vertices ] [ Remove ]

<summary line>
```

Four buttons, a filtered list, two list actions, one result line. No prose, no state to
track, no storage model to understand.

## Testing

- The panel builds with no reference to `a3obBakedWeights` or its helpers.
- `dock.py` registers no `on_expand` for Skinning; expanding it triggers no scene scan
  (`dock_refresh_cost.py`).
- Transfer reports the rigidified-shell count, and reports zero distinctly from "none
  needed".
- Transfer uses `DEFAULT_FAR_DISTANCE` when the command is called without `-distance`, and
  still honours `-distance` when given.
- Saving over an existing reference prompts; declining leaves the file untouched.
- Saving with nothing selected still raises the existing clear error rather than writing an
  empty asset.
- The installer populates `default_directory()` and the optionVars from
  `assets/references/`, and running it a second time does **not** overwrite a reference the
  user has since saved themselves.
- The installer completes normally when `assets/references/` is absent.
- `install_maya.py` still imports only stdlib and `maya.cmds`.
- The panel stays a silent read (`dock_panel_sync.py`), positive control intact.
