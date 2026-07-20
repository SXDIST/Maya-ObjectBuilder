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

**The menu holds only what has no other home.** Every entry below is unreachable except
through it. This rule is why there is no File section: `Arma P3D` is a registered Maya
translator — `readSupport` and `writeSupport` both true, filter `*.p3d` — so
`File > Import` and `File > Export All` already offer P3D natively. A plugin entry would be
the *third* route to one dialog, after Maya's File menu and the dock's Quick Actions.

```
MayaObjectBuilder
  Open MayaObjectBuilder              [icon]
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

- **Auto LOD settings lose nothing by the File section going.** Maya's own
  `File > Export All` carries an option box, and it opens `mayaObjectBuilderP3DOptions` —
  the same dialog, including the Auto LOD frame. The one-click route survives as a native
  one.
- **Add Male Character is deliberate duplication**, and the one exception to the rule above:
  it also has a button in the Skinning panel. A Reference Assets group holding only
  Add Skeleton and a submenu reads as a stump, and the cost is one line. Stated rather than
  hidden.
- **Save Selection as** is a submenu because it holds the three destructive save actions
  the Skinning spec moves out of the panel. `female_body` is exposed here for the first
  time — it exists in `KINDS` and has never had any UI.
- **Preferences…** replaces Set Texture Root and holds the texture root and the
  alpha→transparency toggle, per the Materials spec.

## Dock

### Panels, in workflow order

Eleven become six:

| Panel | Contents after this work |
|-------|--------------------------|
| Quick Actions | Import P3D, Export P3D (+ its options button), Validate |
| LODs | list with inline type/resolution, plus the detail area holding Mass and Named Properties |
| Selections | selections, proxies and flags, each editable in place |
| Skinning | four buttons and the influence list |
| Memory Points | unchanged, still shown only for a Memory LOD |
| Validation | results list with click-to-select, and Scene / Selection buttons |

Order follows the work: bring a model in, structure its LODs, name parts of it, rig it, add
memory points, check it.

### Quick Actions

The row keeps its place **above the scroll area**, which is its entire justification: no
matter which panel is expanded or how far the dock is scrolled, export is one click away.
Every button in it is reachable elsewhere; being always visible is what it sells.

Its contents shrink from four to three. The **Auto LOD** button goes — generation now
happens at export. `Import P3D` and `Export P3D` remain, and `Export P3D` gains a small
adjacent **options** button opening the P3D export options, mirroring Maya's option-box
convention and giving the dock its own one-click route to the Auto LOD settings.

`Import P3D` is not merely a copy of `File > Import`: it pre-selects "Arma P3D" in the
dialog's type list, which Maya otherwise leaves on whatever was used last. That is the value
it adds, and it is the reason it stays in the dock while leaving the menu.

**Export P3D is now the most consequential control in the plugin** — it validates, may
generate LODs, and writes the file. It should read as the primary action of the row rather
than one of three equals.

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
- The menu contains no Import/Export P3D entry, and `File > Export All`'s option box still
  opens the P3D options with the Auto LOD frame.
- The Quick Actions options button opens the same dialog.
- `Import P3D` from Quick Actions pre-selects "Arma P3D" even when the last import used a
  different type.
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
