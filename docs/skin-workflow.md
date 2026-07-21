# DayZ skin weights — working order

The short version: **weights live only in the skinCluster.** Maya deletes it together with the
joints, and there is no second copy — deleting a skeleton loses every weight on every mesh bound
to it, for good. Keep the reference skeleton in the scene until you are done exporting.
`a3obValidate` warns when a mesh has lost its rig while a sibling LOD of the same model is still
skinned, but it cannot bring the weights back — it can only tell you before export does.

## 1. Prepare the scene

Dock → **Skinning**:

- **Add Male Character** — brings in the reference body, its materials, and its skeleton.

For a bare skeleton with no body, or the female body, use the **Reference Assets** submenu in
the MayaObjectBuilder menu instead — that submenu is also where a wrong selection can overwrite
a saved reference asset, which is why it asks for confirmation before replacing one.

The body must be present and *fitted*: the garment has to sit on it in world space. The
transfer refuses to run if the two are in different units or do not overlap, because copying
by closest point would silently produce nonsense.

## 2. Fit the garment

Your job, not the plugin's. The closer the garment follows the body, the better the transfer.
Measured on a real DayZ character, fitted garments sit 0.01–0.03 from the body surface; a
backpack sits at 0.10.

## 3. Transfer the weights

Select the garment → **Transfer Skin from Body**.

What happens: it binds to every joint of the body, copies the weights by closest point, makes
detached shells rigid, then enforces the DayZ rules (≤4 influences, normalized, nothing below
1/254) and drops joints that ended up unused.

A shell more than `0.06` units from the body surface is treated as a separate rigid object
rather than smeared across three bones — see the measurements above for where fitted garments
and a backpack fall relative to that line. The summary line names which happened — "N shell(s)
made rigid" or "none detached" — so a misclassified bulky garment is still visible even without
a field to correct it. Script callers can override the threshold with `a3obTransferSkin
-distance`.

## 4. Test in pose — do not skip this

**Test Pose** bends knees, elbows, shoulders and hips, reports vertices that move unlike their
neighbours, selects them, and puts the skeleton back.

This matters because **bad weights are invisible in bind pose**. A vertex bound to the wrong
limb looks perfectly fine until something rotates. That is exactly how a stray weight survives
all the way into the game.

If spikes are reported, they are already selected — apply `Skin → Smooth Skin Weights`, then
run Test Pose again.

## 5. Check before exporting

**Skinning → Select Skin Outliers** finds vertices whose weights disagree with their
surroundings, by a different measure than Test Pose (distribution rather than motion). Fix the
same way: Smooth Skin Weights.

## 6. Export

`File → Export All`, type **Arma P3D**. You choose the path in the dialog.

Open the result in Object Builder and check the selection list on the right: every bone should
be there alongside `camo`. If you only see `camo`, the model went out without weights.

---

## Three ways to lose weights

**Deleting the skeleton.** Maya deletes the skinCluster with the joints, and the weights go
with it — permanently, with nothing to fall back on.
→ Not recoverable after the fact: keep the skeleton in the scene until export, and if it does
get deleted, re-run **Transfer Skin from Body** rather than trying to get the old weights back.
`a3obValidate` warns when a mesh has no skinCluster while a sibling LOD of the same model still
does — the signal that this LOD specifically lost its rig, not that the model was never rigged.

**Exporting while posed.** Export reads the *deformed* mesh, so a rotated skeleton is baked
into the .p3d as if that were the model's shape.
→ Return to bind pose first (`Skin → Go to Bind Pose`, or Ctrl+Z after Test Pose — Test Pose
restores it by itself).

**Re-running the transfer.** It replaces the existing skinCluster, because the joint set may
differ. Any manual weight painting done since is gone.
→ Do the transfer first, hand-refine after. One Ctrl+Z undoes the whole transfer.

## Rules the format enforces

- at most **4 bones** per vertex;
- weights **normalized** to 1.0;
- nothing below **1/254** — such a weight encodes to a zero byte but still lists the vertex in
  that bone's selection, which Object Builder paints as a stray member far from the bone.

The transfer applies all three. If you paint by hand afterwards, they are yours to maintain —
Maya's `Prune Small Weights` (threshold ~0.004) and `maxInfluences=4` cover it.
