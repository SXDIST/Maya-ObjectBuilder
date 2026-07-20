# Menu and dock presentation

**Date:** 2026-07-20
**Status:** approved, not implemented
**Depends on:** every other 2026-07-20 spec — this one arranges what they leave behind

## Why now

The menu is four flat items with no icons and no grouping, and it is about to grow: the
Reference Assets submenu arrives from the Skinning spec, and Preferences replaces "Set
Texture Root (.paa)…" from the Materials spec. Structuring it after that growth would mean
restructuring twice.

The dock, meanwhile, goes from eleven panels to six.

## The Bifrost look is native — verified

Every flag needed to reproduce the reference screenshot exists in Maya 2027 and was
exercised in a live session before being specified:

| Feature | Flag | Verified |
|---------|------|----------|
| Grey section header | `cmds.menuItem(divider=True, dividerLabel="…")` | returns `"File"`, `"Reference Assets"` on query |
| Icons | `cmds.menuItem(image="…")` | accepted |
| Submenu with arrow | `cmds.menuItem(subMenu=True)` | builds and nests |
| Option box | `cmds.menuItem(optionBox=True)` | creates the paired item |

No custom Qt, no stylesheet, no shipped images are required for the menu.

## Menu structure

```
MayaObjectBuilder
  Open MayaObjectBuilder              [icon]
  ── File ──────────────────
  Import P3D…                         [icon]
  Export P3D…                         [icon]  [□]
  ── Skeleton ──────────────
  Import model.cfg Skeleton
  Export model.cfg Skeleton
  ── Reference Assets ──────
  Add Male Character                  [icon]
  Add Skeleton                        [icon]
  Save Selection as            ▸      (Body / Skeleton / Female Body)
  ── Settings ──────────────
  Preferences…                        [icon]
```

Notes on specific entries:

- **The option box on Export P3D is load-bearing, not decoration.** Auto LOD now lives in
  the export options, so the box opens exactly the dialog a user wants before a generating
  export. This is the Maya convention for "the settings behind this action", and following
  it means the Auto LOD settings are reachable in one click from the menu bar.
- **Import/Export P3D appear in both the menu and the dock's Quick Actions.** That is
  deliberate: the menu works with the dock closed.
- **Save Selection as** is a submenu because it holds the three destructive save actions,
  which the Skinning spec moves out of the panel. `female_body` is exposed here for the
  first time — it exists in `KINDS` and has never had any UI.
- **Preferences…** replaces Set Texture Root and holds the texture root and the
  alpha→transparency toggle, per the Materials spec.

## Dock

### Panels, in workflow order

Eleven become six:

| Panel | Contents after this work |
|-------|--------------------------|
| Quick Actions | Import P3D, Export P3D, Validate — the Auto LOD button is gone |
| LODs | list with inline type/resolution, plus the detail area holding Mass and Named Properties |
| Selections | selections, proxies and flags, each editable in place |
| Skinning | four buttons and the influence list |
| Memory Points | unchanged, still shown only for a Memory LOD |
| Validation | results list with click-to-select, and Scene / Selection buttons |

Order follows the work: bring a model in, structure its LODs, name parts of it, rig it, add
memory points, check it.

### Visual language

- **Every button carries an icon**, drawn from Maya's own `:/` resources as the existing
  buttons already do. No shipped PNGs.
- **Section headers** use the existing `_CollapsibleSection`, given one consistent
  treatment rather than the current mix.
- **Spacing** stays on `UI_MARGIN` / `UI_SPACING`; no per-panel ad-hoc margins.
- **Explanatory prose is a last resort.** The Skinning spec removes four paragraphs; the
  same standard applies everywhere. A tooltip explains, a paragraph occupies.

### The constraint that matters most: no stylesheet

**Do not hand-roll QSS to make the dock look designed.** Maya's dock inherits the
application palette, and a stylesheet that looks right in one theme looks broken in
another — a custom background or text colour is the usual way a plugin ends up visibly
foreign inside Maya.

Presentation comes from Maya's own idioms: built-in icons, standard layouts, consistent
spacing, `dividerLabel` in menus. If something cannot be made to look right that way, the
answer is to simplify the layout, not to paint it.

## Testing

- The menu builds with every divider label, icon, submenu and the export option box, and
  `plugin_teardown.py` still removes it cleanly on unload with no leftover UI.
- Building the menu twice does not duplicate entries (the existing `menu(exists=True)`
  guard still holds).
- The export option box opens the P3D export options, including the Auto LOD frame.
- Every Save Selection entry is reachable, `female_body` included.
- The dock builds with exactly six sections, in the specified order.
- The dock still builds when Qt is unavailable (`QT_AVAILABLE` false path).
- No widget in `a3ob.ui` sets a **non-empty** stylesheet. Worth an explicit test — this is
  the rule most likely to be broken later by someone making one panel "look better".

  The test must allow `setStyleSheet("")`: `widgets.py:105` already calls it to strip an
  inherited stylesheet, which enforces this rule rather than breaking it. A test phrased as
  "no `setStyleSheet` anywhere" would fail on the one line that implements the policy.
- `dock_refresh_cost.py` and `dock_panel_sync.py` continue to pass.

## Not decided here

A Maya shelf was considered and set aside. It needs custom artwork to not look foreign —
Maya's built-in resources read as generic on a shelf — and the menu plus dock already cover
every action.
