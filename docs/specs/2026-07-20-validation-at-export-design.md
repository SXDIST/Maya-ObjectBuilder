# Validation moves into export, with a severity tier that matches the actual danger

**Date:** 2026-07-20
**Status:** approved, not implemented
**Related:** `docs/specs/2026-07-20-ui-simplification-design.md`

## The premise, corrected

The Validate panel was questioned on the grounds that export already validates and Maya
reports problems in the Script Editor. Neither holds:

1. **Export does not validate by default.** The call is gated on `validateMeshes`,
   `exportValidateMeshes` and `validateLods` — all three default to `"0"` in
   `mayaObjectBuilderP3DOptions.mel`. A default export checks nothing.
2. **When it does validate, the result is discarded.** `translator.py:85` calls
   `om.MGlobal.executeCommand(command)` and ignores what comes back; line 87 exports
   regardless. Validation has never been able to stop a bad file being written.
3. **The Script Editor cannot select the offending node.** The panel can: clicking a row
   runs `cmds.select` on the node the issue belongs to. In a scene with seven LODs and
   thirty-five sets, "which one" is the entire question.

Run against `Own_Dreykrus.mb` as it stands: **0 errors, 21 warnings**, including two camo
selections that will not reach the P3D at all.

So the instinct — validation belongs at export — is right. It simply describes something
the code does not do yet.

## The severity tier is wrong, and that is the load-bearing part

Errors today are the unambiguously fatal: no LODs, negative or invalid mass, invalid proxy
placeholder, degenerate faces, invalid proxy selection name, invalid flag component, zero
flag value.

Everything else is a warning — including two things that silently change or lose what gets
exported:

| Issue | Consequence | Today |
|-------|-------------|-------|
| Rig is posed (`validate.py:101`) | The pose is baked into the exported mesh | warning |
| Set has no live members (`validate.py:187`) | That selection is absent from the P3D | warning |
| Duplicate LOD resolution signature (`validate.py:70`) | None, in a multi-model scene | warning |

On the measured scene, "errors block export" would never once fire, while both damaging
warnings would pass silently. A two-level scheme cannot express the difference between
"this file is malformed" and "this file will quietly not be what you think it is".

The posed-rig case is not hypothetical. Per
`2026-07-20-weights-live-skincluster-design.md` the skeleton now stays in the scene
specifically so weights can be posed and checked, which makes exporting from a posed rig a
routine near-miss rather than an exotic one.

## Design

### Three severities

`ValidationLog` gains a level between the two it has:

- **`error`** — the file would be malformed. Blocks the export; no file is written.
- **`damage`** — the file would be written, and would quietly differ from what the scene
  shows. Export presents the list and waits for confirmation. Posed rig and empty selection
  sets move here.
- **`warning`** — worth knowing, changes nothing. Listed, never blocking.

The severity string is already carried through the `"severity|node|message"` rows the panel
parses, so the transport does not change — only the vocabulary and the panel's icon map.

### Export always validates

The three gating options are removed from the option box and from `translator.do_write`,
which validates unconditionally. `do_write` reads the result instead of discarding it:

- any `error` → report and return `False`, writing nothing;
- any `damage` → present the issues, and abort unless confirmed;
- otherwise proceed.

`do_write` already returns `False` for handled failure, so refusing to export is expressible
without changing the translator's contract.

**Non-interactive callers must not hang on the confirmation.** When Maya is in batch mode
the `damage` prompt cannot be shown; it degrades to "report and proceed", so a scripted
export never blocks on a dialog that nobody can answer.

### The panel gets thinner

It keeps exactly what export cannot do: the issue list with click-to-select, plus **Scene**
and **Selection** buttons to check without exporting. It is also the place the export's own
results land, so an export that reported problems leaves them inspectable and clickable
rather than gone from a dialog.

Removed from it:

- **Select Skin Outliers** moves to the Skinning panel. It is a weight tool, writes a
  selection, and never belonged with a read-only validator.

### Two defects to fix while here

- **Rows duplicate, and the cause is a misplaced loop rather than a missing dedup.**
  `_validate_object_sets` runs once per mesh, and inside it walks *every* set in the scene
  with `MItDependencyNodes(om.MFn.kSet)`. The "no live members" check is scene-global, so
  each empty set is reported once per LOD — and every set is inspected once per LOD too:
  245 inspections instead of 35 on the measured scene.

  The fix is to hoist the scene-global checks out of the per-mesh pass and run them once.
  Deduplicating the output afterwards would hide the symptom and keep the repeated scan.
  Per-mesh checks (does *this* mesh's set have a valid flag component, a matching proxy
  placeholder) stay where they are.
- **`duplicate LOD resolution signature` is a false positive for multi-model scenes.** Six
  garments legitimately each carry `Resolution 1`. The check assumes one model per scene.
  It must compare signatures **within a model**, resolved the same way export resolves one
  — upward, then downward — not across the whole scene. Until that holds it produces noise
  on exactly the layout the export path was fixed to support.

## Testing

- `a3obValidate` reports a scene-global issue exactly once regardless of LOD count: an
  empty set in a scene with six LODs yields one row, not six. A count assertion, not
  `> 0` — the duplication this fixes was invisible to a `> 0` check.
- The number of set inspections does not scale with LOD count.
- Six sibling models each at `Resolution 1` produce **no** duplicate-signature warning; two
  LODs at `Resolution 1` within one model still do.
- Export with an `error` present writes no file and returns `False`.
- Export with a `damage` issue and no confirmation writes no file; with confirmation it
  writes.
- Export in batch mode with a `damage` issue writes the file and does not block.
- A posed rig and an empty selection set are both reported at `damage`, not `warning`.
- The panel stays a silent read (`dock_panel_sync.py`), with its positive control intact.

Unchanged gate: `mayapy tests/golden.py verify`. Validation gates whether a file is written;
it does not touch what the bytes are.

## Deliberately not decided here

Whether `damage` issues should be individually dismissible ("export anyway, ignore this one
in future") is left open. It is a preferences question, and the tier is worth living with
before adding an escape hatch to it.
