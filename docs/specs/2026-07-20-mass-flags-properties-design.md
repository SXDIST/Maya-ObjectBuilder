# Mass, Flags and Named Properties go where the thing they describe lives

**Date:** 2026-07-20
**Status:** approved, not implemented
**Related:** `2026-07-20-ui-simplification-design.md`,
`2026-07-20-proxies-into-selections-design.md`

## The two panels

"Mass & Flags" carries seven mass controls (value, mode, apply, clear, density, distribute
evenly, from volume) and four flag controls (component, value, set name, apply). "Named
Properties" carries a list, a name combo, a value combo, an apply-to-all checkbox, and
add/remove buttons.

Both are permanently visible. Measured on `Own_Dreykrus.mb`:

| Data | Present in the scene |
|------|----------------------|
| `a3obMassValues` | on no LOD at all |
| Flag sets (`a3obFlagComponent`) | none |
| `a3obProperties` | `lodnoshadow=1`, on five of six garments |

Eleven controls for mass and flags, neither of which the scene uses, and a list that is
empty except for one property.

## The organising principle

These are not a category. They are three different kinds of data that were grouped by being
leftovers:

- **Mass** is per-LOD data (`a3obMassValues` on the LOD transform).
- **Named properties** are per-LOD data (`a3obProperties` on the LOD transform, exported as
  that LOD's TAGGs).
- **Flags** are per-component sets — the same shape as proxies.

So each moves to where its subject already lives:

| What | Where | Why |
|------|-------|-----|
| Mass | LOD detail area of the merged LODs panel | It belongs to one LOD |
| Named Properties | the same detail area | It belongs to one LOD |
| Flags | Selections panel | `_set_kind` already lists them as "Vertex Flag" / "Face Flag" |

Flags repeat the Proxies situation exactly: a separate creation form for objects the
Selections panel already lists and already operates on. They follow proxies into that panel,
with the same treatment — highlighting a flag row exposes its component type and value for
editing, instead of forcing delete-and-recreate.

Both "Mass & Flags" and "Named Properties" disappear as top-level panels.

## Relevance drives prominence, never availability

This is the governing constraint, and it must survive implementation.

Mass matters on Geometry LODs; named properties vary wildly by model type — the
`KNOWN_NAMED_PROPS` vocabulary is Arma-wide, running from `lodnoshadow` to `church`,
`treehard` and `lighthouse`, of which a garment author uses two or three. It is tempting to
gate these by LOD type.

**Do not gate them.** Every one of these parameters is used situationally: sometimes needed,
sometimes not, and the tool cannot know which. Export writes a mass TAGG wherever
`a3obMassValues` exists and does not restrict it by LOD type, so hiding the controls would
make the UI narrower than the format.

The rule is therefore:

- The Mass section is **always present** in the LOD detail area. When the selected LOD's
  type is not one where mass is usual, it starts **collapsed** — de-emphasised, one click
  away, never absent.
- The named-property name combo **suggests** first what suits the selected LOD's type, and
  stays **editable**, so any property in the vocabulary — or outside it — can still be
  typed.
- Nothing is removed from `KNOWN_NAMED_PROPS`.

## A divergence the current panel cannot show

Five of six garments carry `lodnoshadow=1`; `gloves` carries no `a3obProperties` at all.
Whether that is deliberate is the author's call — but the current panel shows one LOD's
properties at a time, so a disagreement between six sibling models is structurally
invisible in it.

The merged LODs panel lists every LOD, so multi-selecting rows and using the existing
**Apply to all selected LODs** checkbox becomes the natural fix. That checkbox keeps its
behaviour and moves with the rest.

No automatic "these LODs disagree" warning is specified. A validator that guesses intent
across sibling models would produce false positives on exactly the multi-model layouts this
work exists to support.

## Testing

- A scene with no mass and no flags shows no mass or flag data, and the Mass section is
  collapsed rather than missing.
- Setting mass on a Resolution LOD still works and still exports, proving the collapse is
  cosmetic.
- Highlighting a Vertex Flag or Face Flag row in Selections exposes its component and value;
  editing writes through and leaves no orphan set.
- Named properties apply to one LOD, and to several when rows are multi-selected with
  Apply to all selected LODs.
- A property outside `KNOWN_NAMED_PROPS` can still be typed and is stored.
- `dock.py` has no "Mass & Flags" and no "Named Properties" panel; the Named Properties
  branch of `_refresh_dirty_panels` and `_named_snapshot` follow the panel, and
  `_named_fields_focused` goes with them.

Unchanged: `a3obMassValues`, `a3obProperties`, `a3obFlagComponent`, `a3obFlagValue` and
their short names. Only where they are edited changes.
