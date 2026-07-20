# Proxies fold into Selections, and become editable

**Date:** 2026-07-20
**Status:** approved, not implemented
**Related:** `2026-07-20-ui-simplification-design.md`

## What the panel is today

`_build_proxies_section` (in `panels/metadata.py`) is a **create-only form**: a path picker,
an index spinbox, a "Create from selected components" checkbox, and a Create Proxy button.
It displays nothing. No existing proxy is visible in it, and none can be changed from it.

Three findings decide the design.

**Proxies are already listed elsewhere.** The Selections panel shows them as a distinct
kind — `_SELECTION_KIND_ICONS["Proxy"] = ":/out_reference.png"`, assigned by `_set_kind`
from `a3obIsProxySelection`. Select, Rename, Add, Remove and Delete all already operate on
them there. A separate Proxies tab means proxies live in two places, which is the exact
complaint this UI work exists to fix.

**`a3obUpdateProxy` has no UI at all.** The command is registered — it appears in the
seventeen commands listed by a running Maya — and nothing in the dock calls it. A proxy's
path or index therefore cannot be corrected after creation: the only repair is to delete
the proxy and build it again. This is the real gap, and the create-only panel hides it.

**Nothing about proxies is clothing work.** The measured scene has zero proxy sets, as
expected: proxies belong to weapons and vehicles. The capability must stay reachable, but
it does not deserve a permanently visible panel in a garment workflow.

## Design

The Proxies section is removed. Its capability moves into the Selections panel, which
already owns the list.

### Creating

The existing **Create** button becomes a small menu: *Selection from components* (what it
does today) and *Proxy…*. Choosing Proxy opens a modest dialog with the path picker — same
`_path_picker` with `recent_key="proxy"`, so the recent-paths dropdown is preserved — and
the index.

The **"Create from selected components" checkbox is dropped.** It selects between two modes
that the current selection already determines: with components selected, the proxy is built
from them; with none, a standalone placeholder is created. The dialog states which of the
two it will do, and updates as the selection changes, so the mode is visible without being
a control. `a3obProxy -fromSelection` keeps both behaviours for scripted callers.

Path validation stays exactly as it is — `_validate_proxy_path` already reports a missing
path against the texture root, and that message is good.

### Editing — the new part

When a row of kind **Proxy** is highlighted, the details area below the list shows its path
and index as editable fields plus an **Update** button, wired to `a3obUpdateProxy`. For
every other kind the area keeps showing what it shows now.

This is the only new capability in the spec, and it is the one that turns a wrong path from
"delete and rebuild the proxy" into "fix the path".

`a3obProxy` and `a3obUpdateProxy` are deliberately **non-undoable** and wrap their bodies in
an undo chunk: making them undoable is what previously left orphan `a3ob_proxy_*` sets
behind, because `MFnSet.create` never enters the undo queue. The edit path must follow the
same rule — it must not be made undoable to feel tidier.

## Testing

- A scene with a proxy set lists it once, in Selections, with the Proxy kind.
- Highlighting a Proxy row exposes path and index; highlighting a Selection, Vertex Flag or
  Face Flag row does not.
- Update writes a new path and index onto an existing proxy, and the export reflects them.
- Update leaves no orphan `a3ob_proxy_*` set, and Ctrl+Z after it does not resurrect one.
- Creating with components selected and creating with nothing selected both work, and the
  dialog names which one it is about to do.
- An invalid path still refuses with the existing texture-root message, and creates nothing.
- The panel stays a silent read on refresh (`dock_panel_sync.py`), positive control intact.

## Not decided here

Whether proxy placeholders should be visualised in the viewport (an axis marker at the
proxy's position, as Object Builder draws them) is a separate question. It is a real gap —
a proxy is currently invisible until export — but it is a viewport feature, not a panel
one.
