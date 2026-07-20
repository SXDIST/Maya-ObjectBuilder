# Menu and dock presentation

**Date:** 2026-07-20
**Status:** approved, not implemented
**Depends on:** every other 2026-07-20 spec — this one arranges what they leave behind

## Why now

The menu is four flat items with no icons and no grouping, and it is about to grow: the
Reference Assets submenu arrives from the Skinning spec, and Preferences replaces "Set
Texture Root (.paa)…" from the Materials spec. Structuring it after that growth would mean
restructuring twice.

The dock, meanwhile, goes from eleven panels to five, and loses its fixed Quick Actions
header entirely.

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
`File > Import`, `File > Export All` and `File > Export Selection` already offer P3D
natively. A plugin entry would be a second route to a dialog Maya already owns — and the
same reasoning removes the dock's Quick Actions below.

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

Eleven collapsible panels become five, and the fixed Quick Actions header is gone:

| Panel | Contents after this work |
|-------|--------------------------|
| LODs | list with inline type/resolution, plus the detail area holding Mass and Named Properties |
| Selections | selections, proxies and flags, each editable in place |
| Skinning | four buttons and the influence list |
| Memory Points | unchanged, still shown only for a Memory LOD |
| Validation | results list with click-to-select, and Scene / Selection buttons |

Order follows the work: bring a model in, structure its LODs, name parts of it, rig it, add
memory points, check it.

### Quick Actions is removed

The same rule that emptied the menu's File section applies here, and it applies harder: the
dock should not duplicate Maya's own file operations at all.

Every button has another home, so nothing becomes unreachable:

| Button | Where it lives instead |
|--------|------------------------|
| Import P3D | `File > Import` — `Arma P3D` is a registered translator |
| Export P3D | `File > Export All` / `File > Export Selection` |
| Auto LOD | already gone — generation moved into export |
| Validate | the Validation panel |

The Auto LOD settings keep their one-click route through Maya's own option boxes on
`File > Export All` and `File > Export Selection`, both of which open
`mayaObjectBuilderP3DOptions`.

**The loss, stated rather than glossed:** `import_p3d` and `export_p3d` pre-select
"Arma P3D" in the dialog's type list, and that convenience goes with them. Maya then
defaults to whatever type was used last, as it does for every other format.

Setting the `defaultFile*Type` optionVars at plugin load to compensate is **rejected**: it
would hijack `File > Import` for every other format the user works with. A plugin does not
get to decide what Maya's file dialogs default to.

With Quick Actions gone the dock has no fixed header, and the panel list is the whole dock.

**A bug to fix while here**, since it belongs to the export path either way.
`entry.export_p3d` sets only `defaultFileExportAllType`, so Export Selection is never
pre-set to "Arma P3D". The translator and the MEL already handle that path correctly —
`kExportActiveAccessMode` becomes `export_active`, which becomes `selected_only`, and
`mayaObjectBuilderP3DCurrentFileAction` already recognises `defaultFileExportActiveType`.
Only the optionVar was missed. Whatever survives of `export_p3d` must set both.

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

- The menu builds with every divider label, icon and submenu, and `plugin_teardown.py`
  still removes it cleanly on unload with no leftover UI.
- Building the menu twice does not duplicate entries (the existing `menu(exists=True)`
  guard still holds).
- The menu contains no Import/Export P3D entry, and `File > Export All`'s option box still
  opens the P3D options with the Auto LOD frame.
- The dock has no Quick Actions group and no Import/Export/Validate buttons outside the
  Validation panel.
- `File > Export Selection` writes only the selection, and its option box opens the P3D
  options with the Auto LOD frame.
- Any surviving export entry point sets **both** `defaultFileExportAllType` and
  `defaultFileExportActiveType` — the second is the one that regressed.
- Plugin load does not write any `defaultFile*Type` optionVar.
- Every Save Selection entry is reachable, `female_body` included.
- The dock builds with exactly five sections, in the specified order.
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
