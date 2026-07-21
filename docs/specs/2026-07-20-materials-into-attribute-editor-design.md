# Materials move to the Attribute Editor; preferences get their own window

**Date:** 2026-07-20
**Status:** implemented, with the AE-hosted parts of the design revised after live-Maya
measurement — see "Per-material editing → AE template" below
**Related:** `2026-07-20-ui-simplification-design.md`

## What the panel holds

`panels/materials.py` mixes three unrelated things:

1. **Two global preferences** — the texture root and the alpha→transparency toggle. Neither
   is a property of any material; they sit here only because there was nowhere else.
2. **A per-material editor** — texture and rvmat paths for whatever the selection uses.
3. **Select Faces** — a scene operation.

## Findings

**The material data is already native.** `a3obTexture` and `a3obMaterial` are *dynamic*
attributes: `listAttr(userDefined=True)` on a shading engine in the measured scene returns
exactly `["a3obTexture", "a3obMaterial"]`. Maya therefore already shows them in the
Attribute Editor under **Extra Attributes**, with no plugin code involved. The panel
duplicates a view Maya provides for free, adding browse buttons, recent paths,
`_normalize_dayz_path`, and immediate re-texturing on change.

That makes an **AE template** the natural home: a "DayZ Material" section with real path
pickers, reachable exactly where a Maya user looks for material attributes — select the
material in Hypershade, edit it in the Attribute Editor.

**The texture root is currently a lie.** The measured scene has it set to
`…\Maya-ObjectBuilder\tests\paa` — the repository's test fixtures — and that directory
**does not exist**. Textures nonetheless display, because the resolution chain falls through
to `P:/` and the real file is at `P:/DeadCityGameplay/…/Own_Dreykrus_Helmet_co.paa`. The
field states one source while another is doing the work, and nothing says so.

**The scene carries 48 shading engines with a3ob data**, all with relative paths. The panel
only ever shows those belonging to the current selection.

## Design

### Per-material editing → AE template

**Superseded by measurement.** This section as originally designed (path pickers with browse
buttons, and a Select Faces button, both built as custom UI inside the AE) does not work:
measured in a live Maya 2027 session, `editorTemplate -callCustom` never invokes its procs
from inside the `AETemplateCustomContent` hook — the section rendered as an empty frame on
every shading engine. `-addControl` does work, so what shipped is an `AEshadingEngineTemplate`
adding a **DayZ Material** section containing only:

- **Texture** — a native attribute field (`-addControl`), no browse button, no recent-paths
  dropdown — `-addControl` renders an attribute field and nothing else.
- **Material** — the same.

Both accept typing and paste, and `write_material_metadata` still records every path in the
recent-path history for the pickers that remain elsewhere (the texture root lives in the
Preferences window). Editing writes through the same path as today: normalise, store on the
shading engine, re-resolve the texture. Edits stay instant — there is no Apply button now and
none is added.

**Select Faces moved to the menu.** It cannot live in the AE section at all: raw UI built into
the `AETemplateCustomContent` hook cannot re-point when the AE switches nodes (the hook fires
once per node type per tab), which is the same defect that ruled out `-callCustom` in the
first place — a button wired to a stored node would act on the wrong material the moment the
user selected a different one. `select_faces_for_shading_group` survives unchanged in
`a3ob/ui/actions/materials.py`; `select_faces_for_selected_material` (same module) resolves
its target from the **current selection at call time** instead — a selected `shadingEngine`,
or the one a selected material feeds — and a **Select Faces by Material** entry in the
MayaObjectBuilder menu calls it. A resolver that re-reads the selection has nothing to go
stale, which is what makes this safe where the in-AE button was not. Hypershade can select
objects by material but not faces, so this capability still has no native equivalent and
still must survive.

**The discoverability wrinkle, stated plainly.** The attributes live on the
**`shadingEngine`**, not on the material node (`blinn` / `aiStandardSurface`). In Hypershade
one usually clicks the material, so the section appears only after selecting the shading
group. This is a real cost of the move and it is accepted rather than hidden.

Mirroring the attributes onto the material node would fix discoverability and is
**rejected**: it creates two places holding the same value, which is precisely the failure
mode removed from weight storage in
`2026-07-20-weights-live-skincluster-design.md`. If the wrinkle proves painful in use, the
follow-up is a template on the material node types that *reads through* to the connected
shading engine — one source, two views — not a second copy.

### Global preferences → a Preferences window

A **Preferences** entry in the MayaObjectBuilder menu opens a small window holding:

- **Texture root**, with validation. A configured path that does not exist is reported as
  such, and the window states which source actually resolved textures — configured root,
  `P:/`, or the basename search. The current situation, where a stale root silently does
  nothing, must not be expressible without a warning.
- **Alpha → transparency**, unchanged in behaviour and still off by default: a DayZ `_ca`
  alpha is often a data channel, and wiring it makes solid armour see-through.

Both remain optionVars. Only where they are edited changes, and the window is the place
future preferences land instead of being wedged into whichever panel is nearest.

### The panel is removed

With editing in the AE and preferences in their own window, nothing is left.

This also removes the Materials branch from the dock's live-refresh machinery:
`_materials_snapshot` (which builds a tuple over every material node of the selection on
each scene change), `_material_fields_focused` (which defers refreshes while a path field
has focus), and the `"Materials"` case in `_refresh_dirty_panels`. One of the four polled
panels disappears, and with it the deferral hack that existed only because a refresh could
overwrite what the user was typing.

## Testing

- The AE shows a DayZ Material section for a shading engine carrying `a3obTexture` /
  `a3obMaterial`, and does not show it for a shading engine without them.
- Editing a path in the AE writes the normalised value onto the shading engine and
  re-resolves the texture, with no Apply step.
- Recent-path history is shared with what the panel used, so existing history survives.
- **Select Faces by Material**, from the MayaObjectBuilder menu, selects the same faces the
  panel selected — with a shading engine selected, and with just the material selected
  (`tests/mayapy/select_faces_from_selection.py`).
- Preferences reports a configured texture root that does not exist, and names the source
  that actually resolved a texture.
- Alpha → transparency still defaults to off, and toggling it still applies to existing
  materials.
- `dock.py` has no Materials panel, no `_materials_snapshot` and no `_material_fields_focused`;
  a scene change no longer walks the selection's material nodes
  (`dock_refresh_cost.py`).

Unchanged: the `a3obTexture` / `a3obMaterial` schema entries and their short names. Nothing
about where the data lives changes — only where it is edited.

## Not decided here

Whether the PAA decode cache and its directory (`a3ob_paa_cache_v3`) deserve controls in the
Preferences window — a cache size readout and a clear button — is left open. It is a real
question but it is about the cache, not about materials.
